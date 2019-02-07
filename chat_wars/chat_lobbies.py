import engine, dynamic_dicts, threading, time
from telebot import types
from bot_utils import bot_methods, keyboards
from locales import localization
from chat_wars.chat_main import pyossession, get_chat, get_user
from fight import fight_main, standart_actions
from adventures import dungeon_main, map_engine


class Lobby:
    def __init__(self, chat_id, skip_armory=False):
        self.id = str(engine.rand_id())
        self.chat_id = chat_id
        self.message_id = None
        self.teams = [{}]
        # Команда вида {chat_id: [unit_dict, False(ready_status)]}
        self.text = 'FILL THE TEXT'
        self.lang = 'rus'
        self.langs = [self.lang]
        self.started = False
        dynamic_dicts.lobby_list[self.id] = self
        self.skip_armory = skip_armory
        self.start_checker = StartChecker(self)

    def create_lobby(self):
        message = localization.GameString(self)
        next_arrow = '┞'
        end_arrow = '┕'
        i = 0
        message.row(self.text)
        for team in self.teams:
            team_items = list(team.items())
            if len(team) > 0:
                for actor in team_items[:-1]:
                    message.row(next_arrow, actor[1]['dict']['name'])
                message.row(end_arrow, team_items[-1][1]['dict']['name'])
            message.row()
        i += 1
        message.construct()
        return message.result_dict[self.lang]

    def keyboard(self):
        buttons = [types.InlineKeyboardButton(url='https://telegram.me/vwarsbot?start=join_{}'.format(self.id),
                                              text='Присоединиться'),
                   keyboards.Button('Начать бой', '_'.join(['lobby', str(self.id), 'startlobby']))]
        keyboard = keyboards.form_keyboard(*buttons, row_width=2)
        return keyboard

    def start(self):
        if self.started:
            return None
        self.update_lobby(keyboard=False)
        self.start_checker.start()
        for team in self.teams:
            for chat_id in team:
                self.next_step(user_id=chat_id, message_id=None)

    def next_step(self, user_id, message_id=None):
        print(self[user_id])

        if 'weapon' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_weapon_choice(self.id, message_id=message_id)

        elif 'armor' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_armor_choice(self.id, message_id=message_id)

        elif 'items' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_item_choice(self.id, message_id=message_id)

        else:
            self.run()

    def run(self):
        pass

    def run_fight(self, *args):
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id: unit_dict} or team={(ai_class, n):unit_dict}].
        fight = fight_main.Fight(chat_id=self.chat_id)
        self.fight = fight
        self.fight.form_teams(args)
        results = fight.run()
        return results

    def send_lobby(self):
        message = bot_methods.send_message(self.chat_id, self.create_lobby(), reply_markup=self.keyboard())
        self.message_id = message.message_id

    def update_lobby(self, keyboard=True):
        message = self.create_lobby()
        bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message,
                                 reply_markup=self.keyboard() if keyboard else None)

    def error(self, error):
        bot_methods.send_message(self.chat_id,
                                 localization.LangTuple('errors', error).
                                 translate(self.lang))

    def join_lobby(self, user_id, unit_dict):
        if self.started:
            return False
        if not any(user_id in team for team in self.teams):
            unit_data = {
                'dict': unit_dict,
                'equipment_choice':
                    [
                        'weapon',
                        'armor',
                        'items'
                    ] if not self.skip_armory else [],
                'ready': False
            }
            if not self.teams[0]:
                self.teams[0][user_id] =  unit_data
            else:
                self.teams.append({user_id: unit_data})
            self.update_lobby()
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            bot_methods.send_message(user_id, 'Вы успешно присоединились')
        else:
            self.error('player_exists')

    def team_ready(self):
        if all(all(team[key]['ready'] for key in team.keys()) for team in self.teams):
            return True
        return False

    def to_team(self):
        pass

    def __getitem__(self, item):
        for team in self.teams:
            if item in team:
                return team[item]

    def end(self):
        del dynamic_dicts.lobby_list[self.id]


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


class Dungeon(Lobby):
    def __init__(self, chat_id):
        Lobby.__init__(self, chat_id, skip_armory=False)
        self.team = self.teams[0]
        self.map = None
        self.party = None
        self.fight = None
        self.complexity = None

    def join_lobby(self, user_id, unit_dict):
        if self.started:
            return False
        if not any(user_id in team for team in self.teams):
            unit_data = {
                'dict': unit_dict,
                'equipment_choice':
                    [
                        'weapon',
                        'armor',
                        'items'
                    ] if not self.skip_armory else [],
                'ready': False
            }
            self.team[user_id] = unit_data
            self.update_lobby()
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            bot_methods.send_message(user_id, 'Вы успешно присоединились')
        else:
            self.error('player_exists')

    def __str__(self):
        return str(self.id)

    def run(self):
        self.complexity = len(self.teams)
        self.create_dungeon_map(map_engine.FirstDungeon(self))
        dynamic_dicts.dungeons[self.id] = self
        self.add_party(player_list=self.team)
        for member in self.party.members:
            dynamic_dicts.dungeons[member.chat_id] = self
        bot_methods.send_message(self.chat_id, localization.LangTuple('utils', 'fight_start')
                                 .translate(self.lang))
        del dynamic_dicts.lobby_list[self.id]
        self.map.start()

    def end_dungeon(self, defeat=False, boss_beaten=False):
        farmed_resources = 0
        for member in self.party.members:
            for item in member.inventory:
                item_obj = standart_actions.get_class(item[0]['name'])
                if 'resource' in item_obj.core_types:
                    farmed_resources += item_obj. resources *member.inventory[item[1]][1]
        if boss_beaten:
            farmed_resources *= 2
        if defeat:
            farmed_resources = 0
        print('Поход группы {} окончен. Количество заработанных ресурсов - {}. Выгрузка результата в бд...'.format
            (self.party.leader.name, farmed_resources))
        self.delete_map()
        del dynamic_dicts.dungeons[self.id]
        for member in self.party.members:
            del dynamic_dicts.dungeons[member.chat_id]
        bot_methods.send_message(self.chat_id,
                                 'Поход группы {} окончен. Количество заработанных ресурсов - {}.'.format
                                     (self.party.leader.name, farmed_resources))
        chat = pyossession.get_chat(self.chat_id)
        chat.add_resources(farmed_resources)

    def __del__(self):
        print('Удаление объекта данжа {}...'.format(self.id))

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


class AttackLobby(Lobby):
    def __init__(self, chat, attack_action, target_chat):
        Lobby.__init__(self, chat.chat_id, skip_armory=True)
        self.team = self.teams[0]
        self.attack_action = attack_action
        attack_action.attacker_lobby = self
        self.target_chat_id = target_chat.chat_id
        self.target_chat_name = target_chat.name
        self.target_chat = target_chat
        self.defence_send = False
        self.chat = chat
        self.text = 'Нападение на чат {}'.format(self.target_chat_name)

    def join_lobby(self, user_id, unit_dict):
        if self.started:
            return False
        if not any(user_id in team for team in self.teams):
            unit_data = {
                'dict': unit_dict,
                'equipment_choice':
                    [
                        'weapon',
                        'armor',
                        'items'
                    ] if not self.skip_armory else [],
                'ready': False
            }
            self.team[user_id] = unit_data
            self.update_lobby()
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            bot_methods.send_message(user_id, 'Вы успешно присоединились')
        else:
            self.error('player_exists')

    def next_step(self, user_id, message_id=None):
        print(self[user_id])
        if not self.defence_send:
            DefenceLobby(self.attack_action, self).send_lobby()
            self.defence_send = True
        if 'weapon' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_weapon_choice(self.id, message_id=message_id)

        elif 'armor' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_armor_choice(self.id, message_id=message_id)

        elif 'items' in self[user_id]['equipment_choice']:
            user = pyossession.get_user(user_id=user_id)
            user.send_item_choice(self.id, message_id=message_id)

        else:
            self.run()

    def run(self):
        self.attack_action.attack_ready = True
        if self.attack_action.defense_ready:
            self.attack_action.start()

    def to_team(self):
        team_dict = {chat_id: self.team[chat_id]['dict'] for chat_id in self.team}
        team_dict['marker'] = 'attacker'
        return team_dict


class DefenceLobby(Lobby):
    def __init__(self, attack_action, attack_lobby):
        Lobby.__init__(self, attack_lobby.target_chat.chat_id, skip_armory=True)
        self.chat = attack_lobby.target_chat
        self.team = self.teams[0]
        self.attack_action = attack_action
        attack_action.defender_lobby = self
        self.attack_lobby = attack_lobby
        self.name = attack_lobby.target_chat.name
        self.text = 'Защита от чата {}'.format(attack_lobby.chat.name)

    def join_lobby(self, user_id, unit_dict):
        if self.started:
            return False
        if not any(user_id in team for team in self.teams):
            unit_data = {
                'dict': unit_dict,
                'equipment_choice':
                    [
                        'weapon',
                        'armor',
                        'items'
                    ] if not self.skip_armory else [],
                'ready': False
            }
            self.team[user_id] = unit_data
            self.update_lobby()
            chat = get_chat(self.chat_id)
            chat.add_user(user_id)
            bot_methods.send_message(user_id, 'Вы успешно присоединились')
        else:
            self.error('player_exists')

    def run(self):
        self.attack_action.attack_ready = True
        if self.attack_action.attack_ready:
            self.attack_action.start()

    def to_team(self):
        team_dict = {chat_id: self.team[chat_id]['dict'] for chat_id in self.team}
        team_dict['marker'] = 'defender'
        return team_dict


class FFA(Lobby):

    def run(self):
        args = []
        for team in self.teams:
            args.append({chat_id: team[chat_id]['dict'] for chat_id in team})
        fight_main.thread_fight(None, *args, chat_id=self.chat_id)
        self.end()


class LobbyHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    @staticmethod
    def handle(call):
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
            unit_dict = lobby[user_id]['dict']
            user = get_user(call.from_user.id)
            chat = user.chat
            if weapon_name != 'None':
                free_armory = chat.get_free_armory()
                if weapon_name not in free_armory:
                    bot_methods.answer_callback_query(call, 'Этого предмета уже нет на складе')
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
            unit_dict = lobby[user_id]['dict']
            user = get_user(call.from_user.id)
            chat = user.chat
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
            unit_dict = lobby[user_id]['dict']
            user = get_user(call.from_user.id)
            chat = user.chat
            if item_name == 'reset':
                for item in unit_dict['inventory'].values():
                    chat.delete_used_item(item[0]['name'], value=item[1])
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