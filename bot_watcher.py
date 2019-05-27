import sys
import telebot
import os
import config

bot = telebot.TeleBot(config.token, threaded=False)
admin_id = 197216910
bot.send_message(admin_id, os.environ['ERROR_MSG'])
