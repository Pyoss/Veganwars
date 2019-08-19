#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sql_alchemy
from bot_utils import keyboards
from bot_utils.bot_methods import send_message, edit_message, delete_message, get_chat_administrators
from sql_alchemy import Pyossession
from fight import units, standart_actions
from adventures import dungeon_main
from locales.localization import LangTuple
import engine
import dynamic_dicts
from chat_wars.chat_war import current_war, AttackAction
from chat_wars.buildings import building_dict


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

    def show_chat_stats(self, lang):
        receipts = self.get_receipts()
        message = ''
        for key in receipts:
            name = standart_actions.get_name(key, 'rus')
            if receipts[key] == 'inf':
                value = 'Много'
            else:
                value = str(receipts[key])
            message += name + ' - ' + value + '\n'
        used_items = engine.ChatContainer(base_dict=self.get_free_armory())
        lang_tuple = LangTuple('chatmanagement', 'chat_stats', format_dict={'resources': str(self.resources),
                                                                             'items': used_items.to_string(lang,
                                                                                                           marked=True,
                                                                                                           emoted=True)})
        self.send_message(lang_tuple.translate(lang))

    def print_items(self):

        used_items = engine.ChatContainer(base_dict=self.get_free_armory())
        string = 'Свободные предметы:'
        string += used_items.to_string('rus', marked=True, emoted=True)
        self.send_message(string)

# --------------------      ПРЕДМЕТЫ        ------------------------ #

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

    def create_choice_equipment(self, lobby_id, chat_id, equipment_type):
        buttons = []
        equipment_list = get_chat(chat_id).get_free_equipment([equipment_type])
        for equipment in equipment_list:
            buttons.append(keyboards.Button(standart_actions.get_name(equipment[0], self.lang) + ' x ' + str(equipment[1]),
                                            '_'.join(['lobby',
                                                      lobby_id,
                                                      'equipment',
                                                      equipment_type,
                                                      equipment[0]])))
        return buttons

    def send_equipment_choice(self, lobby_id, chat_id, equipment_type, message_id=None):
        message = self.form_equipment_message(lobby_id, equipment_type)
        buttons = self.create_choice_equipment(lobby_id, chat_id, equipment_type)
        if buttons:
            for button in self.choice_button(lobby_id, equipment_type):
                buttons.append(button)
            keyboard = keyboards.form_keyboard(*buttons)
            if message_id is None:
                send_message(self.user_id, message, reply_markup=keyboard)
            else:
                edit_message(chat_id=self.user_id, message_id=message_id, message_text=message, reply_markup=keyboard)
            return True
        else:
            return False


    def form_equipment_message(self, lobby_id, equipment_type):
        equipment_message_dict = {
            'weapon': 'Выберите оружие из доступного.',
            'items': 'Выберите комплект брони.',
            'armor': 'Выберите предметы.'
        }
        message = equipment_message_dict[equipment_type]
        inventory = dungeon_main.Inventory(member=dynamic_dicts.lobby_list[lobby_id][self.user_id]['unit_dict'])
        message += '\n Экипировка: ' + inventory.get_equipment_string(self.lang)
        message += '\n Инвентарь: ' + inventory.get_inventory_string(self.lang)
        return message

    @staticmethod
    def choice_button(lobby_id, equipment_type):
        if equipment_type == 'weapon':
            return [keyboards.Button('Без оружия', '_'.join(['lobby', lobby_id, 'equipment', equipment_type, 'ready']))]
        else:
            return [
                keyboards.Button('Готово', '_'.join(['lobby', lobby_id, 'equipment', equipment_type, 'ready'])),
                keyboards.Button('Сбросить', '_'.join(['lobby', lobby_id, 'equipment', equipment_type, 'reset']))
            ]

    def add_experience(self, experience):
        send_message(self.user_id, 'Вы получаете {} опыта'.format(experience))
        sql_alchemy.SqlUser.add_experience(self, experience)

    def get_fight_unit_dict(self, name=None):
        unit_dict = self.get_unit_dict()
        unit_dict = units.units_dict[unit_dict['unit']](name=name, unit_dict=unit_dict).to_dict()
        return unit_dict

    def add_ability(self, ability):
        ability_list = self.get_abilities()
        ability_list.append(ability.to_dict())
        if 'on_lvl' in ability.core_types:
            ability.gain(self)
        self.set_abilities(ability_list)

    def get_possible_abilities_amount(self):
        experience = self.experience
        ability_number = len(self.get_abilities())
        experience_list = (10, 20, 40, 70, 100)
        i = 0
        for exp in experience_list:
            if experience >= exp:
                i += 1
        i -= ability_number
        print(i)
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


def add_user(user_id):
    pyossession.create_user(user_id)


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

