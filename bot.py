#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from bot_utils import config, bot_handlers, bot_methods
import dynamic_dicts
from fight import fight_main, units, weapons, armors
import time
from chat_wars import chat_main, chat_lobbies, chat_menu, user_menu
import sys
import os
import subprocess

units.fill_unit_dict()

bot = telebot.TeleBot(config.token, threaded=False)
# Снимаем вебхук перед повторной установкой (избавляет от некоторых проблем)

start_time = time.time()
call_handler = bot_handlers.CallbackHandler()
game_dict = dynamic_dicts.lobby_list
types = telebot.types

bot.send_message(config.admin_id, 'Инициация бота...')
bot.locked = False


@bot.message_handler(func=lambda message: True if bot.locked and message.from_user.id != config.admin_id else False,
                     content_types=['text'])
def start(message):
    pass


@bot.message_handler(commands=['map'])
def start(message):
    from adventures import maps
    dung = chat_lobbies.Dungeon(message.chat.id, maps.Forest)
    dung.send_lobby()

@bot.message_handler(commands=['lock'])
def start(message):
    if message.from_user.id == config.admin_id:
        bot.reply_to(message, 'Бот заблокирован.')
        bot.locked = True


@bot.message_handler(commands=['unlock'])
def start(message):
    if message.from_user.id == config.admin_id:
        bot.reply_to(message, 'Бот разблокирован.')
        bot.locked = False


@bot.message_handler(commands=['unlock'])
def start(message):
    if message.from_user.id == config.admin_id:
        os.execl(sys.executable, 'python',  __file__, *sys.argv[1:])


@bot.message_handler(commands=['restart'])
def start(message):
    if message.from_user.id == config.admin_id:
        os.execl(sys.executable, 'python',  __file__, *sys.argv[1:])


@bot.message_handler(commands=['update'])
def start(message):
  
    if message.from_user.id == config.admin_id:
        bot.stop_polling()
        bot.send_message(config.main_chat_id, 'Обновление git...')
        subprocess.Popen(['bash', './update.sh'])


@bot.message_handler(commands=['error'])
def start(message):
  
    if message.from_user.id == config.admin_id:
        bot_methods.err(message.for_error)


@bot.message_handler(commands=['stop'])
def start(message):
  
    if message.from_user.id == config.admin_id:
        bot.stop_polling()


@bot.message_handler(commands=['echo'])
def start(message):
  
    if message.from_user.id == config.admin_id:
        bot_methods.err(message.chat.id)
        bot.send_message(config.admin_id, message.text)

    
@bot.message_handler(commands=["start"])
def game(message):
    if len(message.text.split(' ')) > 1:
        data = message.text.split(' ')[1].split('_')
        import dynamic_dicts
        if data[1] in dynamic_dicts.lobby_list:
            chat_main.add_user(message.from_user.id)
            user = chat_menu.get_user(message.from_user.id)
            unit_dict = user.get_fight_unit_dict(name=message.from_user.first_name)
            dynamic_dicts.lobby_list[data[1]].player_join(message.from_user.id, unit_dict=unit_dict)
            bot_methods.send_message(message.from_user.id, 'Вы успешно присоединились.')


@bot.message_handler(commands=["dicts"])
def switch(message):
    import dynamic_dicts
    dynamic_dicts.print_dicts()


@bot.message_handler(commands=['start_game'])
def start(message):
    if message.chat.id in game_dict:
        game_dict[message.chat.id].ask_start()


@bot.message_handler(commands=['pvp'])
def start(message):
    chat = chat_main.pyossession.get_chat(message.chat.id)
    chat.clear_used_items()
    dung = chat_lobbies.Lobby1x1(message.chat.id)
    dung.send_lobby()


@bot.message_handler(commands=['test_fight'])
def start(message):
    from fight.unit_files import human, red_oak, bloodbug, ogre, goblin_shaman, goblin, dragon, worm
    from fight import ai
    dct = chat_main.get_user(message.from_user.id).get_fight_unit_dict(name=message.from_user.first_name)
    enemy_3_class = ogre.Ogre
    enemy_3 = enemy_3_class()
    team_1 = {message.from_user.id: dct}
    enemy_3.armor = []
    team_2 = {(enemy_3_class, 1): enemy_3.to_dict()}
    fight_main.thread_fight([team_1, team_2], chat_id=message.chat.id)


@bot.message_handler(commands=['join_chat'])
def start(message):
    chat = chat_main.pyossession.get_chat(message.chat.id)
    chat.add_user(message.from_user.id)


@bot.message_handler(commands=['chat_management'])
def start(message):
    chat = chat_main.get_chat(message.chat.id)
    chat_menu.chat_action_dict['main'](chat, message.from_user.id, call=None).func()


@bot.message_handler(commands=['player'])
def start(message):
    user = chat_main.get_user(message.from_user.id)
    user_menu.user_action_dict['main'](user, message.from_user.id).func()


@bot.message_handler(commands=['reset'])
def start(message):
    user = chat_main.get_user(message.from_user.id)
    user.reset_abilities()


@bot.message_handler(commands=['test_add_chat'])
def start(message):
    if message.chat.id < 0:
        chat_main.add_chat(message.chat.id, message.chat.title, message.from_user.id)


@bot.message_handler(commands=['start_attack'])
def start(message):
    bot_methods.err(message)
    if message.chat.id < 0:
        chat = chat_main.pyossession.get_chat(message.chat.id)
        chat.ask_attack(message.from_user.id)


@bot.message_handler(commands=['chat_stats'])
def start(message):
        chat = chat_main.get_chat(message.chat.id)
        chat.show_chat_stats('rus')


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


@bot.callback_query_handler(func=lambda call: call)
def action(call):
    try:
        call_handler.handle(call)
    except Exception as e:
        import traceback
        bot_methods.err(traceback.format_exc())

bot.skip_pending = True

if __name__ == '__main__':
    bot.polling(none_stop=True)
