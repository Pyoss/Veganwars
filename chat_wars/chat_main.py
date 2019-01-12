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


class Lobby:
    def __init__(self, chat_id):
        self.id = str(engine.rand_id())
        self.chat_id = chat_id
        self.message_id = None
        self.team = {}
        # Команда вида {chat_id: [unit_dict, False(ready_status)]}
        self.text = 'FILL THE TEXT'
        self.lang = 'rus'
        self.langs = [self.lang]
        self.start_checker = StartChecker(self)
        self.started = False

    def create_lobby(self):
        message = localization.GameString(self)
        next_arrow = '┞'
        end_arrow = '┕'
        i = 0
        message.row(self.text)
        team = list(self.team.items())
        if len(self.team) > 0:
            for actor in team[:-1]:
                message.row(next_arrow, actor[1]['dict']['name'])
            message.row(end_arrow, team[-1][1]['dict']['name'])
        message.row()
        i += 1
        message.construct()
        return message.result_dict[self.lang]

    def keyboard(self):
        buttons = [types.InlineKeyboardButton(url='https://telegram.me/vwarsbot?start=join_{}'.format(self.id),
                                              text='Присоединиться'),
                   keyboards.Button('Начать атаку', '_'.join(['lobby', str(self.id), 'startlobby']))]
        keyboard = keyboards.form_keyboard(*buttons, row_width=2)
        return keyboard

    def start(self):
        if self.started:
            return None
        self.started = True
        self.update_lobby(keyboard=False)
        for chat_id in self.team:
            user = pyossession.get_user(chat_id)
            user.send_weapon_choice(self.id)
        self.start_checker.start()

    def next_step(self, user_id, message_id=None):

        if 'armor' in self.team[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_armor_choice(self.id, message_id=message_id)

        elif 'items' in self.team[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_item_choice(self.id, message_id=message_id)

        else:
            bot_methods.delete_message(chat_id=user_id, message_id=message_id)
            self.run()

    def run(self):
        pass

    def send_lobby(self):
        message = bot_methods.send_message(self.chat_id, self.create_lobby(), reply_markup=self.keyboard())
        self.message_id = message.message_id

    def update_lobby(self, keyboard=True):
        message = self.create_lobby()
        bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message,
                                 reply_markup=self.keyboard() if keyboard else None)
        print('updated')

    def join_lobby(self, user_id, unit_dict):
        if user_id not in self.team:
            self.team[user_id] = \
                {
                    'dict': unit_dict,
                    'equipment_choice':
                        [
                            'weapon',
                            'armor',
                            'items'
                        ],
                    'ready': False
                }
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            bot_methods.send_message(user_id, 'Вы успешно присоединились')
            self.update_lobby()

    def team_ready(self):
        if all(self.team[key]['ready'] for key in self.team.keys()):
            return True
        return False

    def to_team(self):
        return {member[0]: (member[1][0], member[1][1]) for member in list(self.team.items())}

    def __getitem__(self, item):
        return self.team[item]


class DefenseLobby(Lobby):
    def __init__(self, chat_id, target_id, target_name):
        Lobby.__init__(self, chat_id, target_id, target_name, name='')
        self.text = 'Команда защиты от ' + target_name
        print(self.chat_id)

    def keyboard(self):
        buttons = [keyboards.Button('Присоединиться', '_'.join(['chat', self.chat_id, 'joindefence'])),
                   keyboards.Button('Начать защиту', '_'.join(['chat', self.chat_id, 'startdefence', self.target_id]))]
        keyboard = keyboards.form_keyboard(*buttons, row_width=1)
        return keyboard

    def defend(self, attacker_id):
        message = self.create_lobby()
        bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message + 'Защита началась')
        for key in self.team:
            user = pyossession.get_user(key)
            user.send_weapon_choice('def', self.chat_id)
        StartChecker(dynamic_dicts.attack_lobby_list[attacker_id], self).start()


class Dungeon(Lobby):
    def __init__(self, chat_id):
        Lobby.__init__(self, chat_id)
        self.map = None
        self.party = None
        self.fight = None
        self.complexity = None
        dynamic_dicts.lobby_list[self.id] = self

    def __str__(self):
        return str(self.id)

    def run(self):
        self.complexity = len(self.team)
        self.create_dungeon_map(map_engine.FirstDungeon(self))
        dynamic_dicts.dungeons[self.id] = self
        self.add_party(player_list=self.team)
        for member in self.party.members:
            dynamic_dicts.dungeons[member.chat_id] = self

        bot_methods.send_message(self.chat_id, localization.LangTuple('utils', 'fight_start')
                                 .translate(self.lang))
        del dynamic_dicts.lobby_list[self.id]
        self.map.start()

    def run_fight(self, *args):
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
        fight = fight_main.Fight(chat_id=self.chat_id)
        self.fight = fight
        self.fight.form_teams(args)
        results = fight.run()
        return results

    def end_dungeon(self, defeat=False, boss_beaten=False):
        farmed_resources = 0
        for member in self.party.members:
            for item in member.inventory:
                print(item)
                item_obj = standart_actions.get_class(item[0]['name'])
                if 'resource' in item_obj.core_types:
                    farmed_resources += item_obj.resources*member.inventory[item[1]][1]
                print('Ресурсы -' + str(farmed_resources))
        if boss_beaten:
            farmed_resources *= 2
        if not defeat:
            return farmed_resources
        return 0

    def create_dungeon_map(self, map_type):
        self.map = map_type.create_map()

    def add_party(self, player_list):
        self.party = dungeon_main.Party(player_list, self.chat_id, self.id)

    # Возвращает текущюю локацию группы
    def current_location(self):
        return self.party.current_location

    # Возвращает клавиатуру с картой
    def generate_map_keyboard(self):
        buttons = [room.return_button() for room in self.party.current_location.get_visible()]
        return keyboards.form_keyboard(*buttons, row_width=3)

    def send_movement_map(self):
        keyboard = self.generate_map_keyboard()
        for member in self.party.members:
            member.message_id = bot_methods.send_message(member.chat_id, member.member_string(), reply_markup=keyboard).message_id

    def update_map(self, new=False):
        text = self.party.leader.member_string()
        if self.party.leader.message_id is None:
            self.send_movement_map()
        else:
            for member in self.party.members:
                member.update_map(new=new)

    def delete_map(self):
        if self.party.leader.message_id is not None:
            for member in self.party.members:
                bot_methods.delete_message(message_id=member.message_id, chat_id=member.chat_id)
                member.message_id = None


class StartChecker:
    def __init__(self, lobby):
        self.lobby = lobby

    def start(self):
        thread = threading.Thread(target=self.check)
        thread.daemon = True
        thread.start()

    def check(self):
        while not self.lobby.team_ready():
                time.sleep(2)
        self.start_fight()

    def start_fight(self):
        self.lobby.run()


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


def add_weapon(chat_id):
    chat = get_chat(chat_id)
    chat.add_item('hatchet')


def send_attack_lobby(chat_id, target_id, target_name, name):
    lobby = Lobby(chat_id, target_id, target_name, name)
    lobby.create_lobby()
    lobby.send_lobby()
    dynamic_dicts.attack_lobby_list[chat_id] = lobby


def send_defense_lobby(chat_id, target_id, target_name):
    lobby = DefenseLobby(chat_id, target_id, target_name)
    lobby.create_lobby()
    lobby.send_lobby()
    dynamic_dicts.defense_lobby_list[str(chat_id)] = lobby


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


class LobbyHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        action = call_data[2]
        try:
            lobby = dynamic_dicts.lobby_list[call_data[1]]
        except:
            return False
        if action == 'startlobby':
            dynamic_dicts.lobby_list[call_data[1]].start()
        elif action == 'weapon':
            user_id = call.from_user.id
            weapon_name = call_data[-1]
            unit_dict = lobby.team[user_id]['dict']
            chat = get_chat(lobby.chat_id)
            if weapon_name != 'None':
                free_armory = chat.get_free_armory()
                if weapon_name not in free_armory:
                    bot_methods.answer_callback_query(call, 'Этого предмета уже нет на складе')
                    user = get_user(call.from_user.id)
                    user.send_weapon_choice(call_data[1], message_id=call.message.message_id)
                    return False
                else:
                    chat.use_item(weapon_name)
                    unit_dict['weapon'] = standart_actions.object_dict[weapon_name]().to_dict()
            lobby[user_id]['equipment_choice'].remove('weapon')
            lobby.next_step(user_id, message_id=call.message.message_id)
        elif action == 'armor':
            user_id = call.from_user.id
            armor_action = call_data[-1]
            unit_dict = lobby.team[user_id]['dict']
            chat = get_chat(lobby.chat_id)
            if armor_action == 'reset':
                for armor in unit_dict['armor']:
                    chat.delete_used_item(armor['name'])
                unit_dict['armor'] = []
            elif armor_action == 'ready':
                try:
                    lobby[user_id]['equipment_choice'].remove('armor')
                except:
                    return False
                lobby.next_step(user_id, message_id=call.message.message_id)
                return True
            else:
                free_armory = chat.get_free_armory()
                if armor_action not in free_armory:
                    bot_methods.answer_callback_query(call, 'Этого предмета уже нет на складе')
                    user = get_user(call.from_user.id)
                    user.send_armor_choice(call_data[1], message_id=call.message.message_id)
                    return False
                else:
                    armor = standart_actions.object_dict[armor_action]()
                    if not armor.try_placement(unit_dict):
                        bot_methods.answer_callback_query(call, 'Вы не можете это экипировать.')
                    else:
                        chat.use_item(armor_action)
                        unit_dict['armor'].append(armor.to_dict())

            user = get_user(call.from_user.id)
            user.send_armor_choice(call_data[1], message_id=call.message.message_id)
        elif action == 'item':
            user_id = call.from_user.id
            item_name = call_data[-1]
            unit_dict = lobby.team[user_id]['dict']
            chat = get_chat(lobby.chat_id)
            if item_name == 'reset':
                for item in unit_dict['inventory'].values():
                    print(item)
                    chat.delete_used_item(item[0]['name'])
                unit_dict['inventory'] = {}
            elif item_name == 'ready':
                try:
                    lobby[user_id]['equipment_choice'].remove('items')
                except:
                    return False
                bot_methods.delete_message(chat_id=user_id, message_id=call.message.message_id)
                lobby[user_id]['ready'] = True
                return True
            else:
                free_armory = chat.get_free_armory()
                if item_name not in free_armory:
                    bot_methods.answer_callback_query(call, 'Этого предмета уже нет на складе')
                    user = get_user(call.from_user.id)
                    user.send_item_choice(call_data[1], message_id=call.message.message_id)
                    return False
                else:
                    item = standart_actions.object_dict[item_name]()
                    if sum(v[1] for k, v in unit_dict['inventory'].items()) > 2:
                        bot_methods.answer_callback_query(call, 'Вы набрали максимальное количество предметов.')
                    elif not item.try_placement(unit_dict):
                        bot_methods.answer_callback_query(call, 'Вы не можете это экипировать.')
                    else:
                        chat.use_item(item_name)
                        test = list(k for k, v in unit_dict['inventory'].items() if v[0]['name'] == item.name)
                        if test:
                            unit_dict['inventory'][test[0]][1] += 1
                        else:
                            unit_dict['inventory'][engine.rand_id()] = [item.to_dict(), 1]

            user = get_user(call.from_user.id)
            user.send_item_choice(call_data[1], message_id=call.message.message_id)


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

