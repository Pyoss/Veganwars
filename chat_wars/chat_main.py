import sql_alchemy
from bot_utils import bot_methods, keyboards
from sql_alchemy import Pyossession
from locales import localization
from fight import fight_main, units, standart_actions
import threading
import time

attack_choosers = []
attack_lobby_list = {}
defense_lobby_list = {}


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
        if self.chat_id in attack_choosers:
            self.send_message('Цель уже выбирается кем-то другим')
        elif self.ask_rights(user_id) == 'admin':
            attack_choosers.append(self.chat_id)
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

    def get_free_weapon(self):
        weapons = []
        armory = self.get_free_armory()
        for key in armory:
            if 'weapon' in standart_actions.object_dict[key].core_types:
                weapons.append([key, armory[key]])
        return weapons


class User(sql_alchemy.SqlUser):
    lang = 'rus'

    def send_weapon_choice(self, mode, chat_id, message_id=None):
        message = 'Выберите оружие из доступного.'
        buttons = []
        for weapon in self.chat.get_free_weapon():
            buttons.append(keyboards.Button(standart_actions.get_name(weapon[0], self.lang) + ' x ' + str(weapon[1]),
                                            '_'.join(['chat',
                                                      chat_id,
                                                      'weapon',
                                                      mode,
                                                      weapon[0]])))
        buttons.append(keyboards.Button('Без оружия', '_'.join(['chat',
                                                                chat_id,
                                                                'weapon',
                                                                mode,
                                                                'None'])))
        if message_id is None:
            bot_methods.send_message(self.user_id, message, reply_markup=keyboards.form_keyboard(*buttons))
        else:
            bot_methods.edit_message(chat_id=self.user_id, message_id=message_id,
                                     message_text=message, reply_markup=keyboards.form_keyboard(*buttons) )


class Lobby:
    def __init__(self, chat_id, target_id, target_name, name):
        self.name = name
        self.target_id = target_id
        self.chat_id = chat_id
        self.message_id = None
        self.target_name = target_name
        self.team = {}
        self.text = 'Команда атаки на ' + target_name
        self.lang = 'rus'
        self.langs = [self.lang]

    def create_lobby(self):
        message = localization.GameString(self)
        next_arrow = '┞'
        end_arrow = '┕'
        i = 0
        message.row(self.text)
        team = list(self.team.items())
        if len(self.team) > 0:
            for actor in team[:-1]:
                message.row(next_arrow, actor[1][0])
            message.row(end_arrow, team[-1][1][0])
        message.row()
        i += 1
        message.construct()
        return message.result_dict[self.lang]

    def keyboard(self):
        buttons = [keyboards.Button('Присоединиться', '_'.join(['chat', self.chat_id, 'joinattack'])),
                   keyboards.Button('Начать атаку', '_'.join(['chat', self.chat_id, 'startattack', self.target_id]))]
        keyboard = keyboards.form_keyboard(*buttons, row_width=1)
        return keyboard

    def send_lobby(self):
        message = bot_methods.send_message(self.chat_id, self.create_lobby(), reply_markup=self.keyboard())
        self.message_id = message.message_id

    def update_lobby(self):
        message = self.create_lobby()
        bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message,
                                 reply_markup=self.keyboard())
        print('updated')

    def join_lobby(self, user_id, name, unit_dict):
        if user_id not in self.team:
            self.team[user_id] = [name, unit_dict, False]
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            self.update_lobby()

    def team_ready(self):
        print(self.team)
        if all(self.team[key][-1] for key in self.team.keys()):
            return True
        return False

    def attack(self):
        message = self.create_lobby()
        bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message + 'Атака началась')
        send_defense_lobby(self.target_id, self.chat_id, self.name)
        for key in self.team:
            user = pyossession.get_user(key)
            user.send_weapon_choice('atk', self.chat_id)

    def to_team(self):
        return {member[0]: (member[1][0], member[1][1]) for member in list(self.team.items())}


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
        StartChecker(attack_lobby_list[attacker_id], self).start()


class StartChecker:
    def __init__(self, attack_lobby, defence_lobby):
        self.attack_lobby = attack_lobby
        self.defence_lobby = defence_lobby

    def start(self):
        thread = threading.Thread(target=self.check)
        thread.start()

    def check(self):
        while not self.attack_lobby.team_ready() or not self.defence_lobby.team_ready():
            time.sleep(10)
        self.start_fight()

    def start_fight(self):
        ChatWar(self.attack_lobby, self.defence_lobby)


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
    attack_lobby_list[chat_id] = lobby


def send_defense_lobby(chat_id, target_id, target_name):
    lobby = DefenseLobby(chat_id, target_id, target_name)
    lobby.create_lobby()
    lobby.send_lobby()
    defense_lobby_list[str(chat_id)] = lobby


class ChatHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        action = call_data[2]
        if action == 'attack':
            title = get_chat(call_data[1]).name
            bot_methods.delete_message(call.message.chat.id, call.message.message_id)
            send_attack_lobby(call_data[1], call_data[-1], get_chat(call_data[-1]).name, title)
        elif action == 'defend':
            defense_lobby_list[str(call.message.chat.id)].join_lobby(call.from_user.id,
                                                                     call.from_user.first_name,
                                                                     units.Human(call.from_user.first_name).to_dict())
        elif action == 'startattack':
            admins = bot_methods.get_chat_administrators(call.message.chat.id)
            if len(attack_lobby_list[str(call.message.chat.id)].team) < 1:
                bot_methods.answer_callback_query(call, text='Команды нет.')
            elif any(member.user.id == call.from_user.id for member in admins):
                attack_lobby_list[str(call.message.chat.id)].attack()
            else:
                bot_methods.answer_callback_query(call, text='У вас нет прав.')
        elif action == 'startdefence':
            admins = bot_methods.get_chat_administrators(call.message.chat.id)
            if len(defense_lobby_list[str(call.message.chat.id)].team) < 1:
                bot_methods.answer_callback_query(call, text='Команды нет.')
            elif any(member.user.id == call.from_user.id for member in admins):
                defense_lobby_list[str(call.message.chat.id)].defend(call_data[-1])
            else:
                bot_methods.answer_callback_query(call, text='У вас нет прав.')
        elif action == 'joinattack':
            lobby = attack_lobby_list[call_data[1]]
            lobby.join_lobby(call.from_user.id,
                             call.from_user.first_name,
                             units.Human(call.from_user.first_name).to_dict())
        elif action == 'joindefence':
            lobby = defense_lobby_list[call_data[1]]
            lobby.join_lobby(call.from_user.id,
                             call.from_user.first_name,
                             units.Human(call.from_user.first_name).to_dict())
        elif action == 'weapon':
            lobby = None
            if call_data[-2] == 'atk':
                lobby = attack_lobby_list[call_data[1]]
            elif call_data[-2] == 'def':
                lobby = defense_lobby_list[call_data[1]]
            user_id = call.from_user.id
            weapon_name = call_data[-1]
            unit_dict = lobby.team[user_id][1]
            chat = get_chat(call_data[1])
            if weapon_name != 'None':
                free_armory = chat.get_free_armory()
                if weapon_name not in free_armory:
                    bot_methods.answer_callback_query(call, 'Этого оружия уже нет на складе')
                    user = get_user(call.from_user.id)
                    user.send_weapon_choice(call_data[-2], call_data[1], message_id=call.message.message_id)
                else:
                    bot_methods.delete_message(call.message.chat.id, call.message.message_id)
                    chat.use_item(weapon_name)
                    unit_dict['weapon'] = standart_actions.object_dict[weapon_name]().to_dict()
                    lobby.team[user_id][2] = True
            else:
                bot_methods.delete_message(call.message.chat.id, call.message.message_id)
                lobby.team[user_id][2] = True


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

