import random
from chat_wars.chat_main import get_chat, get_user
from bot_utils import keyboards
from locales.emoji_utils import emote_dict
from bot_utils.bot_methods import send_message, edit_message, delete_message, get_chat_administrators
chat_wars_activated = False



class TestChat:

    def __init__(self, resources, income):
        self.conquerors_list = []
        self.income = income
        self.resources = resources
        self.given_resources = 0

    def attack(self, target_chat):
        attack_price = self.income
        if attack_price < target_chat.resources * 0.1:
            attack_price = int(target_chat.resources * 0.1)
        if self.resources < attack_price:
            print('Атака слишком дорога.')
        else:
            self.resources -= attack_price
            print('Нападение началось.')
            target_chat.conquerors_list.append(self)

    def distribute_lose(self):
        left_out_conquerors = []
        conquerors = self.conquerors_list
        if len(self.conquerors_list) > 5:
            conquerors = random.choices(self.conquerors_list, 5)
        for chat in conquerors:
            chat.given_resources += int(self.resources*0.2)
            self.resources -= self.resources*0.2
            if self.resources <= 0:
                print('Чат разорен!')
        print(left_out_conquerors)

    def get_final(self):
        print(self.resources)
        print(self.given_resources)


def get_chat_menu(user_id, message_id=None):
    user = get_user(user_id)
    chat = user.chat
    if not any(user.user.id == user_id for user in get_chat_administrators(chat.chat_id)):
        send_message(chat.chat_id, 'Кажется, вы не администратор.')
        return False
    string = 'Управление чатом ВВарс'
    buttons = [
        keyboards.ChatButton('Атака','rus', 'attackchoice', named=True, emoji=emote_dict['locked_em']
        if not chat_wars_activated else None),
        keyboards.ChatButton('Арсенал', 'rus', 'arsenal', named=True),
        keyboards.ChatButton('Постройки', 'rus', 'buildings', named=True),
        keyboards.ChatButton('Закрыть', 'rus', 'close', named=True)]
    keyboard = keyboards.form_keyboard(*buttons)
    if message_id is None:
        send_message(user_id, string, reply_markup=keyboard)
    else:
        edit_message(user_id, message_id, message_text=string, reply_markup=keyboard)


class ManageHandler:
    def __init__(self, handler):
        self.handler = handler

    @staticmethod
    def handle(call):
        call_data = call.data.split('_')
        user_id = call.from_user.id
        user = get_user(user_id)
        chat = user.chat
        action = call_data[1]
        if action == 'attackchoice':
            chat.ask_attack(user_id, call.message.message_id)
        elif action == 'craft':
            chat.ask_craft(user_id, call.message.message_id)
        elif action == 'buildings':
            chat.ask_buildings(user_id, call.message.message_id)
        elif action == 'close':
            delete_message(user_id, call.message.message_id)
        elif action == 'attack':
            target = call.data[2]
            chat.start_attack(user_id, call.message.message_id, target)
        elif action == 'build':
            building_name = call.data[2]
            chat.building_menu(building_name, call.message.message_id)

