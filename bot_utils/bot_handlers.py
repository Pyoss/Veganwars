import telebot
from bot_utils import config, bot_methods
from fight import standart_actions, build, fight_main
import game_classes
from locales import localization
from adventures import dungeon_main
from chat_wars import chat_main

types = telebot.types
bot = telebot.TeleBot(config.token)


def game_exists_error(chat_id):
    bot_methods.send_message(chat_id, localization.LangTuple('errors', 'game_exists'))


class CallbackHandler:
    def __init__(self):
        self.game_dict = fight_main.fight_dict
        self.type_dicts = {'fgt': standart_actions.ActionHandler(self),
                           'build': build.BuildHandler(self),
                           'map': dungeon_main.MapHandler(self),
                           'chat': chat_main.ChatHandler(self)}

    def handle(self, call):
        call_split = call.data.split('_')
        print(call_split)
        call_type = call_split[0]
        if call_type == 'switch':
            try:
                game_classes.game_dict[call.message.chat.id].change_team(call.from_user.id)
            except KeyError:
                pass
        else:
            type_handler = self.type_dicts[call_type]
            type_handler.handle(call)

    def game_error(self, call):
        bot_methods.edit_message(call.message.chat.id, call.message.message_id,
                                 call.message.text, reply_markup=types.InlineKeyboardMarkup())
        bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="Can't find the game!")

    def actor_error(self, call):
        bot_methods.edit_message(call.message.chat.id, call.message.message_id, call.message.text,
                                 reply_markup=types.InlineKeyboardMarkup())
        bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="Turn error!")

    def finish(self, call, action, text=None):
        if action.full:
            bot.delete_message(call.message.chat.id, call.message.message_id)


