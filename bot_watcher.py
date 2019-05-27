import sys
import telebot
import os

bot = telebot.TeleBot('777849028:AAFKdy8OJcLn37H7A8bJVsSCTSB-5S37zf4', threaded=False)
admin_id = 197216910
bot.send_message(admin_id, os.environ['ERROR_MSG'])
