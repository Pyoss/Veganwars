#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
from bot_utils import config
import threading
import os

types = telebot.types
bot = telebot.TeleBot(config.token)
admin_bot = telebot.TeleBot(os.environ['ADMIN_TOKEN'])
admin_mode = False
images = False


# Переопределение метода отправки сообщения (защита от ошибок)
def send_message(chat_id, message, reply_markup=None, parse_mode='markdown', to_admin=False):
    if admin_mode and chat_id != config.admin_id:
        bot.send_message(config.admin_id, message)
    return bot.send_message(chat_id, message, reply_markup=reply_markup, parse_mode=parse_mode)


def edit_message(chat_id, message_id, message_text, reply_markup=None, parse_mode='markdown'):
    return bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                 text=message_text, reply_markup=reply_markup, parse_mode=parse_mode)


def send_image(image, chat_id, message=None, reply_markup=None, parse_mode='markdown', to_admin=False):
    if admin_mode and chat_id != config.admin_id:
        if message is not None:
            bot.send_message(config.admin_id, message)
    if not images:
        if message is not None:
            return bot.send_message(chat_id, message, reply_markup=reply_markup)
        return
    return bot.send_photo(chat_id=chat_id, caption=message, photo=image, reply_markup=reply_markup)


def delete_message(chat_id=None, message_id=None, call=None):
    if call is not None:
        return bot.delete_message(call.message.chat.id, call.message.message_id)
    return bot.delete_message(chat_id, message_id)


def err(text):
    #print(str(text))
    admin_bot.send_message(config.admin_id, str(text), parse_mode=None)


def get_chat_administrators(chat_id):
    return bot.get_chat_administrators(chat_id)


def create_timer(func, delay):
    timer = threading.Timer(func, delay)
    timer.start()


def answer_callback_query(call, text, alert=True):
    bot.answer_callback_query(call.id, text=text, show_alert=alert)
