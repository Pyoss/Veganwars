#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sql_alchemy
from bot_utils import bot_methods, keyboards
from sql_alchemy import Pyossession
from locales import localization
from fight import fight_main, units, standart_actions
from adventures import dungeon_main, map_engine
from telebot import types
import engine
import dynamic_dicts
import threading
import time
import asyncio


class Chat(sql_alchemy.SqlChat):

    def get_chat_obj(self):
        return bot_methods.get_chat_administrators(self.chat_id)

    def send_message(self, text, image=None):
        bot_methods.send_message(chat_id=self.chat_id, message=text)

    def print_rights(self, user_id):
        self.send_message(self.ask_rights(user_id))

    def ask_rights(self, user_id):
        admins = bot_methods.get_chat_administrators(self.chat_id)
        if any(member.user.id == user_id for member in admins):
            return 'admin'
        return 'member'

    def alert_attack(self):
        self.send_message('В течение следующего часа можно выбрать чат для нападения.')

    def ask_attack(self, user_id):
        if self.chat_id in dynamic_dicts.attack_choosers:
            self.send_message('Цель уже выбирается кем-то другим')
        elif self.ask_rights(user_id) == 'admin':
            dynamic_dicts.attack_choosers.append(self.chat_id)
            targets = self.get_target_chats()
            buttons = []
            for target in targets:
                buttons.append(keyboards.Button(target.name, callback_data='_'.join(['chat', self.chat_id, 'attack',  target.chat_id])))
            keyboard = keyboards.form_keyboard(*buttons)
            bot_methods.send_message(user_id, 'Выберите чат для атаки', reply_markup=keyboard)
        else:
            self.send_message('У вас нет прав. Вы бесправный.')

    def get_target_chats(self):
        return [chat for chat in pyossession.get_chats() if chat.chat_id != self.chat_id]

    def get_free_equipment(self, equipment_types=None):
        equipment = []
        armory = self.get_free_armory()
        if equipment_types is not None:
            for key in armory:
                if set(equipment_types).issubset(standart_actions.object_dict[key].core_types):
                    equipment.append([key, armory[key]])
        return equipment

    # Демонстрация списка доступных рецептов
    def print_receipts(self):
        receipts = self.get_receipts()
        message = ''
        for key in receipts:
            name = standart_actions.get_name(key, 'rus')
            if receipts[key] == 'inf':
                value = 'Много'
            else:
                value = str(receipts[key])
            message += name + ' - ' + value + '\n'
        self.send_message(message)

    def print_items(self):
        used_items = engine.ChatContainer(base_dict=self.get_free_armory())
        string = 'Свободные предметы:'
        string += used_items.to_string('rus', marked=True, emoted=True)
        self.send_message(string)

    def ask_craft(self, user_id):
        if self.ask_rights(user_id) == 'admin':
            message = 'Выберите предмет для крафта.'
            craft_list = []
            receipts = self.get_receipts()
            for key in receipts:
                if receipts[key] == 'inf':
                    value = 'Много'
                else:
                    value = str(receipts[key])
                craft_list.append((key, value))
            buttons = []
            for item in craft_list:
                price = standart_actions.get_class(item[0]).price
                buttons.append(keyboards.Button(standart_actions.get_name(item[0], 'rus') + ' (' + str(price) + ')',
                                                callback_data='_'.join(['chat', self.chat_id, 'craft',  item[0]])))
            keyboard = keyboards.form_keyboard(*buttons)
            bot_methods.send_message(user_id, message, reply_markup=keyboard)

    # Распечатка количества ресурсов
    def print_resources(self):
        message = 'Количество ресурсов - ' + str(self.resources)
        self.send_message(message)




class User(sql_alchemy.SqlUser):
    lang = 'rus'

    def create_choice_equipment(self, lobby_id, equipment_list, equipment_type):
        buttons = []
        for equipment in equipment_list:
            buttons.append(keyboards.Button(standart_actions.get_name(equipment[0], self.lang) + ' x ' + str(equipment[1]),
                                            '_'.join(['lobby',
                                                      lobby_id,
                                                      equipment_type,
                                                      equipment[0]])))
        return buttons

    def send_weapon_choice(self, lobby_id, message_id=None):
        message = 'Выберите оружие из доступного.'
        inventory = dungeon_main.Inventory(member=dynamic_dicts.lobby_list[lobby_id][self.user_id]['dict'])
        message += '\n Экипировка: ' + inventory.get_equipment_string(self.lang)
        message += '\n Инвентарь: ' + inventory.get_inventory_string(self.lang)
        buttons = self.create_choice_equipment(lobby_id, self.chat.get_free_equipment(['weapon']), 'weapon')
        buttons.append(keyboards.Button('Без оружия', '_'.join(['lobby',
                                                                lobby_id,
                                                                'weapon',
                                                                'None'])))
        if message_id is None:
            bot_methods.send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            bot_methods.edit_message(chat_id=self.user_id, message_id=message_id,
                                     message_text=message, reply_markup=keyboards.form_keyboard(*buttons) )

    def send_armor_choice(self, lobby_id, message_id=None):
        message = 'Выберите комплект брони.'
        inventory = dungeon_main.Inventory(member=dynamic_dicts.lobby_list[lobby_id][self.user_id]['dict'])
        message += '\n Экипировка: ' + inventory.get_equipment_string(self.lang)
        message += '\n Инвентарь: ' + inventory.get_inventory_string(self.lang)
        buttons = self.create_choice_equipment(lobby_id, self.chat.get_free_equipment(['armor']), 'armor')
        buttons.append(keyboards.Button('Готово', '_'.join(['lobby',
                                                                lobby_id,
                                                                'armor',
                                                                'ready'])))
        buttons.append(keyboards.Button('Сбросить', '_'.join(['lobby',
                                                                lobby_id,
                                                                'armor',
                                                                'reset'])))
        if message_id is None:
            bot_methods.send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            bot_methods.edit_message(chat_id=self.user_id, message_id=message_id,
                                     message_text=message, reply_markup=keyboards.form_keyboard(*buttons) )

    def send_item_choice(self, lobby_id, message_id=None):
        message = 'Выберите предметы.'
        inventory = dungeon_main.Inventory(member=dynamic_dicts.lobby_list[lobby_id][self.user_id]['dict'])
        message += '\n Экипировка: ' + inventory.get_equipment_string(self.lang)
        message += '\n Инвентарь: ' + inventory.get_inventory_string(self.lang)
        buttons = self.create_choice_equipment(lobby_id, self.chat.get_free_equipment(['item']), 'item')
        buttons.append(keyboards.Button('Готово', '_'.join(['lobby',
                                                                lobby_id,
                                                                'item',
                                                                'ready'])))
        buttons.append(keyboards.Button('Сбросить', '_'.join(['lobby',
                                                                lobby_id,
                                                                'item',
                                                                'reset'])))
        if message_id is None:
            bot_methods.send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            bot_methods.edit_message(chat_id=self.user_id, message_id=message_id,
                                     message_text=message, reply_markup=keyboards.form_keyboard(*buttons) )


class ChatWar:
    def __init__(self, attacker_lobby, defender_lobby):
        args = [attacker_lobby.to_team(), defender_lobby.to_team()]
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
        fight = fight_main.Fight()
        fight.form_teams(args)
        self.results = fight.run()

    def process_results(self):
        print(self.results['winners'])


class ChatHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        action = call_data[2]
        if action == 'craft':
            chat = get_chat(call_data[1])
            item_name = call_data[-1]
            item_class = standart_actions.get_class(item_name)
            name = standart_actions.get_name(item_name, 'rus')
            chat.add_resources(-item_class.price)
            chat.add_item(item_name)
            chat.delete_receipt(item_name)
            bot_methods.edit_message(call.message.chat.id, call.message.message_id, name + ' - произведено.')
        elif action == 'cancel':
            bot_methods.delete_message(call.message.chat.id, call.message.message_id)


def add_chat(chat_id, name, creator):
    pyossession.create_chat(chat_id, name)
    chat = pyossession.get_chat(chat_id)
    chat.add_user(creator)


def get_chats():
    return pyossession.get_chats()


def get_chat(chat_id):
    return pyossession.get_chat(chat_id)


def get_user(chat_id):
    return pyossession.get_user(chat_id)

pyossession = Pyossession(Chat, User)
pyossession.start_session()

