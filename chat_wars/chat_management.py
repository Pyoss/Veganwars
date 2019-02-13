import random
from chat_wars.chat_main import get_chat, get_user
from chat_wars.chat_menu import chat_action_dict
from bot_utils import keyboards
from locales.emoji_utils import emote_dict
from bot_utils.bot_methods import send_message, edit_message, delete_message, get_chat_administrators
from chat_wars.buildings import building_dict
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
