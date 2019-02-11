#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from bot_utils import config, bot_handlers, bot_methods
import dynamic_dicts
from fight import fight_main, units
import time, requests, threading, asyncio
from chat_wars import chat_main, chat_lobbies, chat_management

WEBHOOK_HOST = '167.99.131.174'
WEBHOOK_PORT = 443  # 443, 80, 88 или 8443 (порт должен быть открыт!)
WEBHOOK_LISTEN = '0.0.0.0'  # На некоторых серверах придется указывать такой же IP, что и выше

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Путь к сертификату
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Путь к приватному ключу

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)

bot = telebot.TeleBot(config.token, threaded=False)

proxy = 'http://178.33.39.70:3128'
telebot.apihelper.proxy = {
  'http': proxy,
  'https': proxy
}
start_time = time.time()
call_handler = bot_handlers.CallbackHandler()
game_dict = dynamic_dicts.lobby_list

types = telebot.types


# Снимаем вебхук перед повторной установкой (избавляет от некоторых проблем)
bot.remove_webhook()


@bot.message_handler(commands=["start"])
def game(message):
    if len(message.text.split(' ')) > 1:
        data = message.text.split(' ')[1].split('_')
        import dynamic_dicts
        if data[1] in dynamic_dicts.lobby_list:
            dynamic_dicts.lobby_list[data[1]].join_lobby(message.from_user.id,
                                                     unit_dict=units.Human(name=message.from_user.first_name).to_dict())


@bot.message_handler(commands=["dicts"])
def switch(message):
    import dynamic_dicts
    dynamic_dicts.print_dicts()


@bot.message_handler(commands=['start_game'])
def start(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].ask_start()


@bot.message_handler(commands=['map'])
def start(message):
    chat = chat_main.pyossession.get_chat(message.chat.id)
    chat.clear_used_items()
    dung = chat_lobbies.Dungeon(message.chat.id)
    dung.send_lobby()


@bot.message_handler(commands=['join_chat'])
def start(message):
    chat = chat_main.pyossession.get_chat(message.chat.id)
    chat.add_user(message.from_user.id)


@bot.message_handler(commands=['chat_management'])
def start(message):
    chat_management.get_chat_menu(message.from_user.id)


@bot.message_handler(commands=['ffa'])
def start(message):
    chat = chat_main.pyossession.get_chat(message.chat.id)
    chat.clear_used_items()
    dung = chat_lobbies.FFA(message.chat.id)
    dung.send_lobby()


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


@bot.message_handler(commands=['show_items'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.print_items()


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


@bot.message_handler(func=lambda message: True, commands=['show_items'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.print_items()


@bot.message_handler(commands=['craft'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.ask_craft(message.from_user.id)


@bot.message_handler(commands=['next_step'])
def start(message):
        chat_main.current_war.next_step(message.chat.id)



@bot.message_handler(content_types=['photo'])
def start(message):
    print(message.photo[0].file_id)


@bot.callback_query_handler(func=lambda call: call)
def action(call):
    call_handler.handle(call)

bot.skip_pending = True

if __name__ == '__main__':
    bot.polling(none_stop=True)
