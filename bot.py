#!/usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from bot_utils import config, bot_handlers, bot_methods
import game_classes
from fight import fight_main, units
import time, requests, threading
from chat_wars import chat_main
import cherrypy

WEBHOOK_HOST = '167.99.131.174'
WEBHOOK_PORT = 443  # 443, 80, 88 или 8443 (порт должен быть открыт!)
WEBHOOK_LISTEN = '0.0.0.0'  # На некоторых серверах придется указывать такой же IP, что и выше

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Путь к сертификату
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Путь к приватному ключу

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)

bot = telebot.TeleBot(config.token, threaded=False)
start_time = time.time()
call_handler = bot_handlers.CallbackHandler()
game_dict = game_classes.game_dict

types = telebot.types

# Снимаем вебхук перед повторной установкой (избавляет от некоторых проблем)
bot.remove_webhook()

 # Ставим заново вебхук
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

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

@bot.message_handler(commands=["start"])
def game(message):
    if len(message.text.split(' ')) > 1:
        data = message.text.split(' ')[1].split('_')
        if int(data[1]) in game_classes.game_dict:
            game_classes.game_dict[int(data[1])].join_lobby(message.from_user.id, message.from_user.first_name)


@bot.message_handler(commands=["game"])
def game(message):
    if message.chat.id not in game_dict:
        game_classes.VsGame(message.chat.id, lang='rus' if message.from_user.language_code == 'ru-RU' else 'rus')
    else:
        game_dict[message.chat.id].error('game_exists')


@bot.message_handler(commands=["ffa"])
def game(message):
    if message.chat.id not in game_dict:
        game_classes.FFAGame(message.chat.id, lang='rus' if message.from_user.language_code == 'ru-RU' else 'rus')
    else:
        game_dict[message.chat.id].error('game_exists')


@bot.message_handler(commands=["switch"])
def switch(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].change_team(message.from_user.id)


@bot.message_handler(commands=['start_game'])
def start(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].ask_start()


@bot.message_handler(commands=['map'])
def start(message):
    thread = threading.Thread(target=game_classes.Dungeon, args=[message.chat.id, 'rus'])
    thread.start()


@bot.message_handler(commands=['test_fight'])
def start(message):
    # [team={chat_id:(name, unit_dict)} or team={(ai_class, n):(ai_class.name, unit_dict)}].
    name = message.from_user.first_name
    mob_class = fight_main.units.Pasyuk
    fight_main.thread_fight(None, {message.from_user.id: (name, units.Human(name).to_dict())},
                                   {(mob_class, 1): (None, mob_class().to_dict())}, chat_id=message.chat.id)


@bot.message_handler(commands=['test'])
def start(message):
    smile_text = message.text.split()[-1]
    print(smile_text)
    output = (smile_text
              .encode('raw_unicode_escape')
              )
    bot_methods.send_message(message.chat.id, output)


@bot.message_handler(commands=['test_add_chat'])
def start(message):
    if message.chat.id < 0:
        chat_main.add_chat(message.chat.id, message.chat.title, message.from_user.id)


@bot.message_handler(commands=['start_attack'])
def start(message):
    print(message)
    if message.chat.id < 0:
        chat = chat_main.pyossession.get_chat(message.chat.id)
        chat.ask_attack(message.from_user.id)


@bot.message_handler(commands=['show_resources'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.print_resources()


@bot.message_handler(commands=['resources'])
def start(message):
    try:
        resources = int(message.text.split()[1])
        chat = chat_main.get_chat(message.chat.id)
        chat.add_resources(resources)
    except:
        return False


@bot.message_handler(commands=['show_receipts'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.print_receipts()


@bot.message_handler(func=lambda message: True,commands=['show_items'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.print_items()


@bot.message_handler(commands=['craft'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.ask_craft(message.from_user.id)


@bot.message_handler(content_types=['photo'])
def start(message):
    print(message.photo[0].file_id)


@bot.callback_query_handler(func=lambda call: call)
def action(call):
    call_handler.handle(call)

bot.skip_pending = True

# Указываем настройки сервера CherryPy
cherrypy.config.update({
    'server.socket_host': WEBHOOK_LISTEN,
    'server.socket_port': WEBHOOK_PORT,
    'server.ssl_module': 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})

 # Собственно, запуск!
cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})
