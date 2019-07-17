import telebot
import os
from bot_utils import config

bot = telebot.TeleBot(config.token, threaded=False)
bot.send_message(config.main_chat_id, 'Бот неожидано прервал работу и будет перезапущен; \n\n Код ошибки:')
bot.send_message(config.main_chat_id, os.environ['ERROR_MSG'])
