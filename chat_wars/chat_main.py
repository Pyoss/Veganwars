#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sql_alchemy
from bot_utils import keyboards
from bot_utils.bot_methods import send_message, edit_message, delete_message, get_chat_administrators
from sql_alchemy import Pyossession
from fight import fight_main, units, standart_actions, abilities
from adventures import dungeon_main, map_engine
import engine
import dynamic_dicts
from chat_wars.chat_war import current_war, AttackAction
from chat_wars.buildings import building_dict
from threading import Thread


class Chat(sql_alchemy.SqlChat):

    def get_chat_obj(self):
        return get_chat_administrators(self.chat_id)

    def send_message(self, text, image=None):
        send_message(chat_id=self.chat_id, message=text)

    def print_rights(self, user_id):
        self.send_message(self.ask_rights(user_id))

    def ask_rights(self, user_id):
        admins = get_chat_administrators(self.chat_id)
        if any(member.user.id == user_id for member in admins):
            return 'admin'
        return 'member'

    def is_admin(self, user_id):
        admins = get_chat_administrators(self.chat_id)
        if any(member.user.id == user_id for member in admins):
            return True
        return False

# --------------------       АТАКА ЧАТОВ      ------------------------ #

    def alert_attack(self):
        self.send_message('В течение следующего часа можно выбрать чат для нападения.')

    def ask_attack(self, user_id, message_id):
        if current_war.stage == 'siege':
            string = 'Выберите чат для начала осады'
            targets = self.get_target_chats()
            buttons = []
            for target in targets:
                buttons.append(keyboards.Button(target.name + ' - ' + str(self.get_attack_price(target)),
                                                callback_data='_'.join(['mngt', 'attack',
                                                                        target.chat_id])))
            keyboard = keyboards.form_keyboard(*buttons)
        elif current_war.stage == 'attack':
            string = 'Выберите чат на атаки'
            targets = self.get_target_chats()
            buttons = []
            for target in targets:
                buttons.append(keyboards.Button(target.name, callback_data='_'.join(['mngt', 'attack',  target.chat_id])))
            keyboard = keyboards.form_keyboard(*buttons)
        else:
            delete_message(user_id, message_id)
            return False
        if self.ask_rights(user_id) == 'admin':
            edit_message(user_id, message_id, string, reply_markup=keyboard)
        else:
            self.send_message('У вас нет прав. Вы бесправный.')

    def get_target_chats(self):
        if current_war.stage == 'siege':
            target_chats = [chat for chat
                            in pyossession.get_chats() if chat.chat_id != self.chat_id]
            return target_chats
        elif current_war.stage == 'attack':
            war_data = self.get_current_war_data()
            return [chat for chat in [pyossession.get_chat(chat_id) for chat_id in war_data['chats_besieged']]]

    def get_prize(self):
        return int(self.resources*0.2)

    def get_attack_price(self, target_chat):
        attack_price = self.get_income()
        alternative = target_chat.resources*0.1
        if alternative > attack_price:
            attack_price = int(alternative)
        return attack_price

    def get_free_equipment(self, equipment_types=None):
        equipment = []
        armory = self.get_free_armory()
        if equipment_types is not None:
            for key in armory:
                if set(equipment_types).issubset(standart_actions.object_dict[key].core_types):
                    equipment.append([key, armory[key]])
        return equipment

    def attack_chat(self, call, target_chat):
        delete_message(call.from_user.id, call.message.message_id)
        from chat_wars.chat_lobbies import AttackLobby
        action = AttackAction()
        action.mode = current_war.stage
        AttackLobby(self, action, target_chat).send_lobby()

    def win_siege(self, target_chat_id):
        target_chat = pyossession.get_chat(target_chat_id)
        send_message(target_chat.chat_id, 'Чат {} осаждает ваши укрепления!'.format(self.name))
        send_message(self.chat_id, 'Вы успешно осаждаете чат {}'.format(target_chat.name))
        war_data = self.get_current_war_data()
        war_data['chats_besieged'].append(target_chat_id)
        self.set_current_war_data(war_data)

    def marauder(self, target_chat_id):
        target_chat = pyossession.get_chat(target_chat_id)
        send_message(target_chat.chat_id, 'Чат {} раграбляет ваши сокровища!'.format(self.name))
        send_message(self.chat_id, 'Чат {} ограблен!'.format(target_chat.name))
        war_data = target_chat.get_current_war_data()
        war_data['attacked_by_chats'].append(self.chat_id)
        target_chat.set_current_war_data(war_data)

    def get_maximum_attacks(self):
        return 1


# ---------------------------------- КРАФТ ------------------------------------ #

    def complete_attack(self, chat_id):
        war_data = self.get_current_war_data()
        war_data.chats_attacked.append(chat_id)
        self.set_current_war_data(war_data)

    def conquer(self, chat_id):
        chat = get_chat(chat_id)
        war_data = chat.get_current_war_data()
        war_data.conquered_by_chats.append(self.chat_id)
        chat.set_current_war_data(war_data)

# --------------------       ЗДАНИЯ      ------------------------ #

    def available_buildings(self):
        buildings = self.get_buildings()
        return [key for key, value in building_dict.items() if key not in buildings or
                building_dict[key].max_lvl > buildings[key]]

    def buy_building(self, building_name):
        if self.resources >= building_name[building_dict].get_price(self) and building_name in self.available_buildings():
            return True
        else:
            return False

    def build(self, user, building_name):
        buildings = self.get_buildings()
        if building_name in buildings:
            buildings[building_name] += 1
        else:
            buildings[building_name] = 1
        self.set_buildings(buildings)

    def construction_lvl(self):
        return sum([value for key, value in self.get_buildings().items()])

    def available_buildings_message(self, user, message_id):
        available_buildings = self.available_buildings()
        buttons = []
        for building in available_buildings:
            building_object = building_dict[building]()
            price = building_object.get_price(self)
            name = building_object.get_string('name').translate('rus')
            button = keyboards.Button('{} - {}'.format(name, price),
                                      callback_data='_'.join(['mngt', 'build','menu', building]))
            buttons.append(button)
        buttons.append(keyboards.ChatButton('Назад', 'rus', 'menu', named=True))
        edit_message(user.user_id, message_id=message_id, message_text='Доступные для постройки здания',
                     reply_markup=keyboards.form_keyboard(*buttons))

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

# --------------------      ПРЕДМЕТЫ        ------------------------ #

    def items_menu(self, user_id, message_id):
        item_string = 'Меню предметов.'
        buttons = []
        buttons.append(keyboards.ChatButton('Крафт', 'rus', 'craft-list', named=True))
        buttons.append(keyboards.ChatButton('Назад', 'rus', 'menu', named=True))
        edit_message(user_id, message_id, item_string, reply_markup=keyboards.form_keyboard(*buttons))

    def item_menu_string(self, user_id):
        item_list = self.get_armory()
        item_string = 'Меню предметов.'

    def ask_craft(self, user_id, message_id):
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
                buttons.append(keyboards.ChatButton(standart_actions.get_name(item[0], 'rus') + ' (' + str(price) + ')',
                                                'rus', 'craft', item[0], named=True))
            buttons.append(keyboards.ChatButton('Назад', 'rus', 'menu', named=True))
            edit_message(user_id, message_id, message, reply_markup=keyboards.form_keyboard(*buttons))

    def ask_add_item(self, item_name, user_id, message_id):
        if self.ask_rights(user_id) == 'admin':
            receipts = self.get_receipts()
            item_price = standart_actions.object_dict[item_name].price
            if item_name in receipts.keys() and self.resources >= item_price:
                self.create_item(item_name, item_price)
            delete_message(user_id, message_id)

    def create_item(self, item_name, item_price):
        self.add_item(item_name)
        self.delete_receipt(item_name)
        self.add_resources(-item_price)

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
            send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            edit_message(chat_id=self.user_id, message_id=message_id,
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
            send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            edit_message(chat_id=self.user_id, message_id=message_id,
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
            send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            edit_message(chat_id=self.user_id, message_id=message_id,
                                     message_text=message, reply_markup=keyboards.form_keyboard(*buttons) )

    def add_experience(self, experience):
        send_message(self.user_id, 'Вы получаете {} опыта'.format(experience))
        sql_alchemy.SqlUser.add_experience(self, experience)

    def get_unit_dict(self, name=None):
        class_dict = self.get_class()
        abilities_list = self.get_abilities()
        unit_dict = units.units_dict[class_dict['unit']](name=name).to_dict()
        for ability in abilities_list:
            if not any(ablty['name'] == ability['name'] for ablty in unit_dict['abilities']):
                unit_dict['abilities'].append(ability)
        return unit_dict

    def add_ability(self, ability):
        ability_list = self.get_abilities()
        ability_list.append(ability.to_dict())
        self.set_abilities(ability_list)

    def get_possible_abilities_amount(self):
        experience = self.experience
        ability_number = len(self.get_abilities())
        experience_list = (10, 50)
        i = 0
        for exp in experience_list:
            if experience >= exp:
                i += 1
        i -= ability_number
        return i if i > 0 else False

    def get_experience_to_lvl(self):
        experience_list = (10, 50)
        for item in experience_list:
            if self.experience < item:
                return item
        return 10000



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
            edit_message(call.message.chat.id, call.message.message_id, name + ' - произведено.')
        elif action == 'cancel':
            delete_message(call.message.chat.id, call.message.message_id)


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


def get_users():
    return pyossession.get_users()

pyossession = Pyossession(Chat, User)
pyossession.start_session()

