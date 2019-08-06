import telebot
import os
from bot_utils import config

bot = telebot.TeleBot(config.token, threaded=False)
bot.send_message(config.main_chat_id, 'Бот неожидано прервал работу и будет перезапущен; \n\n Код ошибки:')
try:
    bot.send_message(config.main_chat_id, os.environ['ERROR_MSG'])
except telebot.apihelper.ApiException:
    text = os.environ['ERROR_MSG']
    text_1 = text[:int(len(text)/2)]
    text_2 = text[int(len(text)/2):]
    bot.send_message(config.main_chat_id, text_1)
    bot.send_message(config.main_chat_id, text_2)
