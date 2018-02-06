import datetime
import sqlite3
import threading
import time

import requests
import telebot

import config
import instagram
import cherrypy


WEBHOOK_HOST = '130.255.14.138'
WEBHOOK_PORT = 443  # 443, 80, 88 или 8443 (порт должен быть открыт!)
WEBHOOK_LISTEN = '0.0.0.0'  # На некоторых серверах придется указывать такой же IP, что и выше

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Путь к сертификату
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Путь к приватному ключу

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)


insta_smile = u"\U0001F464"
like_smile = u"\U00002764"
comment_smile = u"\U0001F4AD"
list_smile = u"\U0001F4CB"
help_smile = u"\U00002753"
pay_smile = u"\U0001F4B3"

bot = telebot.TeleBot(config.token)
#bot.remove_webhook()
agent = instagram.AgentAccount('sgforever.bot', '145236888')
agent.update()

class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            # Эта функция обеспечивает проверку входящего сообщения
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)


def write_to_log(message):
    print(message)


@bot.message_handler(commands=["start"])
def start_chat(message):
    write_to_log(str("Подключился " + message.from_user.first_name + ", id:" + str(message.from_user.id)))
    if dbcon.check_user_from_db(message.from_user.id):
        bot.send_message(message.chat.id, config.start_tx_return.format(message.from_user.first_name))
    else:
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
        user_markup.row(help_smile + ' помощь', list_smile + ' список задач', pay_smile + ' оплата')
        dbcon.add_new_telegram_user(message.from_user.id, message.from_user.first_name)
        bot.send_message(message.chat.id, config.start_tx.format(message.from_user.first_name),
                         reply_markup=user_markup)
        dbcon.change_input_status(message.from_user.id, True, "invite")


@bot.message_handler(commands=["about"])
def about_message(message):
    write_to_log(str("about " + message.from_user.first_name))
    dbcon.check_user_from_db(message.chat.id)
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
    bot.send_message(message.chat.id, message.from_user.first_name + config.about_tx, reply_markup=user_markup)


@bot.message_handler(commands=["help"])
def help_message(message):
    write_to_log(str("help " + message.from_user.first_name))
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
    bot.send_message(message.chat.id, config.help_tx, reply_markup=user_markup)


@bot.message_handler(commands=["pay"])
def pay_message(message):
    write_to_log(str("Подключился " + message.from_user.first_name))
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
    bot.send_message(message.chat.id, dbcon.get_pay_status(message.from_user.id), reply_markup=user_markup)


@bot.message_handler(commands=["invite"])
def invite_user(message):
    write_to_log(str("invite " + message.from_user.first_name))
    bot.send_message(message.from_user.id, config.go_invite)
    dbcon.change_input_status(message.from_user.id, True, "invite")


@bot.message_handler(commands=["like"])
def like_post(message):
    write_to_log(str("like " + message.from_user.first_name))
    if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
        bot.send_message(message.from_user.id, config.go_like)
        dbcon.change_input_status(message.from_user.id, True, "like")
    else:
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        user_markup.row(pay_smile + ' оплата', help_smile + ' помощь', insta_smile + ' инстаграм')
        bot.send_message(message.chat.id, config.no_pay, reply_markup=user_markup)


@bot.message_handler(commands=["com"])
def com_post(message):
    if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
        bot.send_message(message.from_user.id, config.go_like)
        dbcon.change_input_status(message.from_user.id, True, "com")
    else:
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        user_markup.row(pay_smile + ' оплата', help_smile + ' помощь', insta_smile + ' инстаграм')
        bot.send_message(message.chat.id, config.no_pay, reply_markup=user_markup)


@bot.message_handler(commands=["list"])
def list(message):
    write_to_log(str("list " + message.from_user.first_name))
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
    if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
        bot.send_message(message.chat.id, dbcon.get_list_for_work(message.from_user.id), reply_markup=user_markup)
    else:
        bot.send_message(message.chat.id, str(config.no_pay + config.pay_tx), reply_markup=user_markup)


@bot.message_handler(content_types=["text"])
def echo_message(message):
    write_to_log(str("Прислал сообщение: " + message.from_user.first_name + ", text:" + message.text))
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+', like_smile + ' лайк+')
    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
    input_status = dbcon.get_input_status(message.from_user.id)
    if input_status == "input":
        s = message.text.split(" ")
        if dbcon.get_input_type(message.from_user.id) == "invite":
            dbcon.add_insta_ac(message.from_user.id, message.text)
            bot.send_message(message.chat.id, config.invite_tnx_tx, reply_markup=user_markup)
            dbcon.change_input_status(message.from_user.id, False, "")
        else:
            if dbcon.get_input_type(message.from_user.id) == "like":
                dbcon.change_input_status(message.from_user.id, False, "")
                if len(s) == 1:
                    ss = check_media(s[0], message.from_user.id)
                    if ss == "ok":
                        i = dbcon.add_post(message.from_user.id, s[0], "like",
                                           dbcon.get_insta_user(message.from_user.id))
                        bot.send_message(message.chat.id, config.like_ok.format(i), reply_markup=user_markup)
                        send_all(message.chat.id, config.new_event_like.format(i, s[0]))
                        print("пришло задание на лайк")
                    else:
                        bot.send_message(message.chat.id, ss, reply_markup=user_markup)
                else:
                    if len(s) > 1:
                        bot.send_message(message.chat.id, config.like_no, reply_markup=user_markup)
            else:
                if dbcon.get_input_type(message.from_user.id) == "com":
                    dbcon.change_input_status(message.from_user.id, False, "")
                    if len(s) == 1:
                        ss = check_media(s[0], message.from_user.id)
                        if ss == "ok":
                            i = dbcon.add_post(message.from_user.id, s[0], "com",
                                               dbcon.get_insta_user(message.from_user.id))
                            bot.send_message(message.chat.id, config.like_ok.format(i), reply_markup=user_markup)
                            send_all(message.chat.id, config.new_event_com.format(i, s[0]))
                            print("пришло задание на комментарий")
                        else:
                            bot.send_message(message.chat.id, ss, reply_markup=user_markup)
                        # bot.send_message(message.chat.id, config.com_intro)
                    else:
                        if len(s) > 1:
                            bot.send_message(message.chat.id, config.like_no, reply_markup=user_markup)
    else:
        if input_status == "noinput":
            if message.text == insta_smile + ' инстаграм':
                write_to_log(str("invite " + message.from_user.first_name))
                bot.send_message(message.from_user.id, config.go_invite)
                dbcon.change_input_status(message.from_user.id, True, "invite")
            else:
                if message.text == comment_smile + ' комент+':
                    if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
                        bot.send_message(message.from_user.id, config.go_like)
                        dbcon.change_input_status(message.from_user.id, True, "com")
                    else:
                        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                        user_markup.row(pay_smile + ' оплата', help_smile + ' помощь', insta_smile + ' инстаграм')
                        bot.send_message(message.chat.id, config.no_pay, reply_markup=user_markup)
                else:
                    if message.text == like_smile + ' лайк+':
                        if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
                            bot.send_message(message.from_user.id, config.go_like)
                            dbcon.change_input_status(message.from_user.id, True, "like")
                        else:
                            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                            user_markup.row(pay_smile + ' оплата', help_smile + ' помощь', insta_smile + ' инстаграм')
                            bot.send_message(message.chat.id, config.no_pay, reply_markup=user_markup)
                    else:
                        if message.text == help_smile + ' помощь':
                            write_to_log(str("help " + message.from_user.first_name))
                            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                            user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+',
                                            like_smile + ' лайк+')
                            user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
                            bot.send_message(message.chat.id, config.help_tx, reply_markup=user_markup)
                        else:
                            if message.text == list_smile + ' список задач':
                                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                                user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+',
                                                like_smile + ' лайк+')
                                user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
                                if dbcon.get_pay_status(message.from_user.id) == config.yes_pay:
                                    bot.send_message(message.chat.id, dbcon.get_list_for_work(message.from_user.id),
                                                     reply_markup=user_markup)
                                else:
                                    bot.send_message(message.chat.id, str(config.no_pay + config.pay_tx),
                                                     reply_markup=user_markup)
                            else:
                                if message.text == pay_smile + ' оплата':
                                    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                                    user_markup.row(insta_smile + ' инстаграм', comment_smile + ' комент+',
                                                    like_smile + ' лайк+')
                                    user_markup.row(help_smile + ' помощь', list_smile + ' список задач')
                                    bot.send_message(message.chat.id, dbcon.get_pay_status(message.from_user.id),
                                                     reply_markup=user_markup)
                                else:
                                    print(message)
        else:
            bot.send_message(message.chat.id, input_status)


def check_media(url, author):
    try:
        req = requests.get('https://api.instagram.com/oembed/?url={}'.format(url))
        a = req.json()
        print(a["provider_name"])
    except ValueError:
        print("Ошибка джейсона")
        return config.no_insta
    if a["provider_name"] == "Instagram":
        if a["author_name"] == dbcon.get_insta_user(author):
            return "ok"
        else:
            return config.no_author
    else:
        return config.no_insta
    return config.common_error


def add_event():
    now = datetime.datetime.timestamp(datetime.datetime.now())
    s = "1517250653.189727"
    time_delta = now - float(s)
    print(now, s, time_delta)
    print("Время в секундах:" + str(int(time_delta)))
    print("Время в минутах:" + str(int(time_delta / 60)))
    print("Время в часах:" + str(int(time_delta / 3600)))


def get_media_id(url):
    try:
        req = requests.get('https://api.instagram.com/oembed/?url={}'.format(url))
        a = req.json()
        print(a)
    except ValueError:
        print("Ошибка джейсона")
        return config.no_insta
    if a["provider_name"] == "Instagram":
        return a["media_id"].split("_")[0]
    else:
        return config.no_insta
    return config.common_error


def send_all(user_id, message):
    list = dbcon.get_send_list(user_id)
    for i in list:
        bot.send_message(i, message)
        print(i, message)


def get_likes_list_from_instagram(insta_account, media_id):
    print(insta_account, media_id)
    account = instagram.Account(insta_account)
    agent.update(account)
    j = 0
    while j < config.max_account_iterations:
        media = agent.getMedia(account, count=j + 1)
        if media[j].id == media_id:
            break
        else:
            if j == config.max_account_iterations:
                print("Запись не найдена")
                return []
            j = j + 1
    print(agent.getLikes(media[j], 5000))
    return agent.getLikes(media[j], 5000)


def get_comments_list_from_instagram(insta_account, media_id):
    print(insta_account, media_id)
    account = instagram.Account(insta_account)
    agent.update(account)
    j = 0
    while j < config.max_account_iterations:
        media = agent.getMedia(account, count=j + 1)
        if media[j].id == media_id:
            break
        else:
            if j == config.max_account_iterations:
                print("Запись не найдена")
                return []
            j = j + 1
    print(agent.getComments(media[j], 5000))
    comentators_list=[]
    for i in agent.getComments(media[j], 1000):
        b = i.owner
        comentators_list.append(b)
    return comentators_list


class CommonStorage():
    def __init__(self):
        print("Common storage start...")
        self.lost_post_numb = 0

    def common_data(self, types, data, new_data=0):
        if types == "get":
            if data == "lost_post_numb":
                return self.lost_post_numb
        else:
            if types == "set":
                if data == "lost_post_numb":
                    self.lost_post_numb = new_data
        return 0


class DBConnector():
    def __init__(self):
        print("DBConnecter add...")

    def get_send_list(self, user_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id !=  :userid", {"userid": user_id})
        result = c.fetchall()
        user_id_list = []
        for row in result:
            user_id_list.append(row[1])
        c.close()
        conn.close()
        return user_id_list

    def change_input_status(self, user_chat_id, on_off_input, input_type):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("UPDATE bot_user2 SET input_mode=:ofi WHERE user_telegram_id=:uti",
                  {"uti": user_chat_id, "ofi": on_off_input})
        conn.commit()
        c.close()
        conn.close()
        conn2 = sqlite3.Connection(config.db_name)
        c2 = conn2.cursor()
        c2.execute("UPDATE bot_user2 SET input_mode_type=:ofi WHERE user_telegram_id=:uti",
                   {"uti": user_chat_id, "ofi": input_type})
        conn2.commit()
        c2.close()
        conn2.close()

    def get_input_status(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        row = c.fetchone()
        if row == None:
            c.close()
            conn.close()
            return config.common_error
        else:
            if row[8] == True:
                c.close()
                conn.close()
                return "input"
            else:
                c.close()
                conn.close()
                return "noinput"

    def get_input_type(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        row = c.fetchone()
        if row == None:
            c.close()
            conn.close()
            return config.common_error
        else:
            c.close()
            conn.close()
            return row[9]

    def remove_post(self, post_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("DELETE FROM list WHERE id=:pi", {"pi": post_id})
        conn.commit()
        c.close()
        conn.close()

    def add_post(self, user_chat_id, link, event_type, insta_author):
        media_id = get_media_id(link)
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute(
            "INSERT INTO list (author_id,author_name,event_type,link,media_id,add_time_math) VALUES (:ai,:an,:et,:li,:mi,:tm)",
            {"ai": user_chat_id, "an": insta_author, "et": event_type, "li": link, "mi": media_id,
             "tm": datetime.datetime.timestamp(datetime.datetime.now())})
        conn.commit()
        c.execute("SELECT * FROM list WHERE event_type=:et AND link=:li", {"et": event_type, "li": link})
        post_id = c.fetchone()[0]
        c.close()
        conn.close()
        i = storage.common_data("set", "lost_post_numb", post_id)
        new_post_thread = ClockThread(config.life_time, config.warning_time, post_id, user_chat_id, link, media_id,
                                      event_type, insta_author)
        new_post_thread.daemon = True
        new_post_thread.start()
        print(threading.enumerate())
        print("Пост в БД №" + str(storage.common_data("get", "lost_post_numb")))
        return post_id

    def get_list_for_work(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        row = c.fetchone()
        if row == None:
            c.close()
            conn.close()
            return config.common_error
        else:
            st_post_for_user = row[10]
        row = None

        c.execute("SELECT * FROM list WHERE id>:st", {"st": st_post_for_user})
        row = c.fetchone()
        if row == None:
            c.close()
            conn.close()
            return config.list_empty
        else:
            answer = config.list_start
            c.execute("SELECT * FROM list WHERE id>:st", {"st": st_post_for_user})
            result = c.fetchall()
            for row in result:
                if row[1] != user_chat_id:
                    if row[6] == "like":
                        a = config.list_like
                    else:
                        a = config.list_com
                    answer += str(a + row[7] + "\n")
            if answer == "":
                answer = config.list_empty
            c.close()
            conn.close()
            return answer

    def check_user_from_db(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        if c.fetchone() == None:
            c.close()
            conn.close()
            return False
        else:
            c.close()
            conn.close()
            return True

    def add_new_telegram_user(self, user_chat_id, user_chat_name):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO bot_user2 (user_telegram_id,user_telegram_name,start_post) VALUES (:uti,:utn,:sp)",
                  {"uti": user_chat_id, "utn": user_chat_name, "sp": storage.common_data("get", "lost_post_numb")})
        conn.commit()
        c.close()
        conn.close()

    def get_pay_status(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        row = c.fetchone()
        if row == None:
            c.close()
            conn.close()
            return config.common_error
        else:
            if str(row[4]) == "no":
                c.close()
                conn.close()
                return str(config.no_pay + config.pay_tx)
            else:
                c.close()
                conn.close()
                return config.yes_pay

    def add_insta_ac(self, user_chat_id, insta_ac):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("UPDATE bot_user2 SET user_instagram_name=:ia WHERE user_telegram_id=:uti",
                  {"uti": user_chat_id, "ia": insta_ac})
        conn.commit()
        c.close()
        conn.close()

    def get_insta_user(self, user_chat_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM bot_user2 WHERE user_telegram_id =  :userid", {"userid": user_chat_id})
        row = c.fetchone()
        user_id = row[3]
        c.close()
        conn.close()
        return user_id

    def get_users_list_who_need_works(self, author_insta_name, post_id):
        conn = sqlite3.Connection(config.db_name)
        c = conn.cursor()
        c.execute(
            "SELECT user_instagram_name FROM bot_user2 WHERE user_instagram_name !=  :userid AND start_post < :pi",
            {"userid": author_insta_name, "pi": post_id})
        rows = c.fetchall()
        users_list = []
        for i in rows:
            users_list.append(i[0])
        c.close()
        conn.close()
        return users_list


class ClockThread(threading.Thread):
    def __init__(self, interval, warning_time, post_id, author_id, link, media_id, event_type, insta_author):
        threading.Thread.__init__(self)
        self.daemon = True
        self.interval = interval
        self.warning_time = warning_time
        self.post_id = post_id
        self.author_id = author_id
        self.link = link
        self.media_id = media_id
        self.event_type = event_type
        self.insta_author = insta_author

    def self_delete(self):
        dbcon.remove_post(self.post_id)

    def run(self):
        print("New image thread add")
        time.sleep(self.warning_time)  ################Предупреждение
        print("Предупреждение об истечении времени")
        if self.event_type == "like":
            users_list = get_likes_list_from_instagram(self.insta_author, self.media_id)
            print("Выполнить работу должны:")
            need_users_list = dbcon.get_users_list_who_need_works(self.insta_author, self.post_id)
            for i in users_list:
                for j in need_users_list:
                    if str(j) == str(i):
                        need_users_list.remove(j)
            print(need_users_list)
            self.messaging(need_users_list, config.time_warning_for_user.format(self.post_id, "лайк"), "war")
        else:
            users_list = get_comments_list_from_instagram(self.insta_author, self.media_id)
            print("Выполнить работу должны:")
            need_users_list = dbcon.get_users_list_who_need_works(self.insta_author, self.post_id)
            for i in users_list:
                for j in need_users_list:
                    if str(j) == str(i):
                        need_users_list.remove(j)
            print(need_users_list)
            self.messaging(need_users_list, config.time_warning_for_user.format(self.post_id, "комментарий"), "war")
        bot.send_message(self.author_id, config.time_warning_for_author.format(self.post_id, self.link))
        time.sleep(self.interval)  ####################финальный отчет
        if self.event_type == "like":
            users_list = get_likes_list_from_instagram(self.insta_author, self.media_id)
            print("Выполнить работу должны:")
            need_users_list = dbcon.get_users_list_who_need_works(self.insta_author, self.post_id)
            for i in users_list:
                for j in need_users_list:
                    if str(j) == str(i):
                        need_users_list.remove(j)
            print(need_users_list)
            self.messaging(need_users_list, config.time_end_for_user.format(self.post_id, "лайк"), "fin")
        else:
            users_list = get_comments_list_from_instagram(self.insta_author, self.media_id)
            print("Выполнить работу должны:")
            need_users_list = dbcon.get_users_list_who_need_works(self.insta_author, self.post_id)
            for i in users_list:
                for j in need_users_list:
                    if str(j) == str(i):
                        need_users_list.remove(j)
            print(need_users_list)
            self.messaging(need_users_list, config.time_end_for_user.format(self.post_id, "комментарий"), "fin")
        bot.send_message(self.author_id, config.time_end_for_author.format(self.post_id, self.link))
        print("Проверяем список отработавших, делаем рассылку")
        print("post {} deleted!!!".format(self.post_id))
        self.self_delete()

    def messaging(self, users_list, mes_text, act):
        if act == "war":
            conn = sqlite3.Connection(config.db_name)
            c = conn.cursor()
            for i in users_list:
                c.execute("SELECT * FROM bot_user2 WHERE user_instagram_name =  :userid ", {"userid": i})
                row = c.fetchone()
                c = row[0]
                bot.send_message(c[1], mes_text)
            c.close()
            conn.close()
        else:
            conn = sqlite3.Connection(config.db_name)
            c = conn.cursor()
            for i in users_list:
                c.execute("SELECT * FROM bot_user2 WHERE user_instagram_name =  :userid ", {"userid": i})
                row = c.fetchone()
                c = row[0]
                war = row[6]
                bot.send_message(c[1], mes_text)
                if war == 2:
                    c.execute("UPDATE bot_user2 SET warning_num=3 WHERE id=:uid", {"uid": c[0]})
                    conn.commit()
                    c.execute("UPDATE bot_user2 SET pay_check='no' WHERE id=:uid", {"uid": c[0]})
                    conn.commit()
                    bot.send_message(c[1], config.user_blocked)
            c.close()
            conn.close()


dbcon = DBConnector()
storage = CommonStorage()
print(threading.enumerate())

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,certificate=open(WEBHOOK_SSL_CERT, 'r'))
cherrypy.config.update({
    'server.socket_host': WEBHOOK_LISTEN,
    'server.socket_port': WEBHOOK_PORT,
    'server.ssl_module': 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})

 # Собственно, запуск!
cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})

#if __name__ == "__main__":
    #bot.polling(none_stop=True)
