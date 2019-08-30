import engine, dynamic_dicts, threading, time
from telebot import types
from bot_utils import bot_methods, keyboards
from locales import localization
from locales.localization import LangTuple
from chat_wars.chat_main import pyossession, get_chat, get_user
import image_generator
from fight import fight_main, standart_actions, units
from adventures import dungeon_main, dungeon_events
import file_manager


class Lobby:
    name = None

    def __init__(self, chat_id, skip_armory=False):
        self.id = str(engine.rand_id())
        self.chat_id = chat_id
        self.message_id = None
        self.teams = [{}]
        self.image = None
        # Команда вида {chat_id: [unit_dict, False(ready_status)]}
        self.text = 'FILL THE TEXT'
        self.lang = 'rus'
        self.langs = [self.lang]
        self.started = False
        self.table_row = None
        dynamic_dicts.lobby_list[self.id] = self
        self.skip_armory = skip_armory
        self.start_checker = StartChecker(self)

    def get_lang_tuple(self, string, format_dict=None):
        return LangTuple(self.table_row, string, format_dict=format_dict)

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
                    message.row(next_arrow, actor[1]['unit_dict']['name'])
                message.row(end_arrow, team_items[-1][1]['unit_dict']['name'])
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
                self.run_next_step(user_id=chat_id, message_id=None)

    def run_next_step(self, user_id, message_id=None):
        user = pyossession.get_user(user_id=user_id)
        print(self[user_id]['equipment_choice'])
        if self[user_id]['equipment_choice']:
            if not user.send_equipment_choice(self.id, self.chat_id,
                                              self[user_id]['equipment_choice'][-1], message_id=message_id):
                self[user_id]['equipment_choice'].pop()
                self.run_next_step(user_id, message_id=message_id)
        else:
            self.get_ready_message(user_id, message_id=message_id)

    def get_ready_message(self, user_id, message_id):
        bot_methods.edit_message(user_id, message_id, 'Вы готовы.')

    def get_image(self, user_id):
        unit_dict = self[user_id]['unit_dict']
        unit_class = units.units_dict[unit_dict['unit_name']]
        unit = unit_class(unit_dict=unit_dict)
        return unit.get_image(user_id)

    def run(self):
        pass

    def run_fight(self, *args, first_turn=None):
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id: unit_dict} or team={(ai_class, n):unit_dict}].
        try:
            fight = fight_main.Fight(chat_id=self.chat_id)
            fight.form_teams(args)
            results = fight.run(first_turn=first_turn)
            return results
        except Exception as e:
            import traceback
            bot_methods.err(traceback.format_exc())

    def send_lobby(self):
        if self.image is None:
            message = bot_methods.send_message(self.chat_id, self.create_lobby(), reply_markup=self.keyboard())
        else:
            message = bot_methods.send_image(open(self.image, 'rb'), self.chat_id, message=self.create_lobby(),
                                             reply_markup=self.keyboard())
        self.message_id = message.message_id

    def get_vacant_team(self):
        return min(self.teams, key=lambda k: len(k))

    def player_join(self, user_id, unit_dict):
        team = self.get_vacant_team()
        self.join_lobby(user_id, unit_dict, team)

    def join_lobby(self, user_id, unit_dict, team):
        if self.join_forbidden(user_id):
            return False
        unit_data = {
            'unit_dict': unit_dict,
            'equipment_choice':
                [
                    'item',
                    'armor',
                    'weapon'
                ] if not self.skip_armory else [],
            'ready': False
        }
        team[user_id] = unit_data
        self.update_lobby()

    def join_forbidden(self, user_id):
        if self.started:
            return True

        if user_id in dynamic_dicts.occupied_list:
            dynamic_dicts.occupied_list.append(user_id)
            bot_methods.send_message(user_id, 'Вы не можете сейчас присоединиться.')
            return True

        if any(user_id in team for team in self.teams):
            self.error('player_exists')
            return True

        return False

    def update_lobby(self, keyboard=True):
        message = self.create_lobby()
        if self.image is None:
            bot_methods.edit_message(self.chat_id, message_id=self.message_id, message_text=message,
                                     reply_markup=self.keyboard() if keyboard else None)
        else:
            bot_methods.bot.edit_message_caption(caption=message, chat_id=self.chat_id, message_id=self.message_id,
                                                 reply_markup=self.keyboard() if keyboard else None)

    def error(self, error):
        bot_methods.send_message(self.chat_id,
                                 localization.LangTuple('errors', error).
                                 translate(self.lang))

    def team_ready(self):
        if all(all(not team[key]['equipment_choice'] for key in team.keys()) for team in self.teams):
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


class Lobby1x1(Lobby):
    def __init__(self, chat_id, skip_armory=False):
        Lobby.__init__(self, chat_id, skip_armory=skip_armory)
        self.teams = [{}, {}]

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        for team in self.teams:
            bot_methods.send_image(image_generator.create_dungeon_image(path,
                                                                        (self.get_image(key) for key in team)),
                                   self.chat_id)
        result = self.run_fight(*[{chat_id: team[chat_id]['unit_dict'] for chat_id in team} for team in self.teams])


class LobbyFFA(Lobby):
    def __init__(self, chat_id, skip_armory=False):
        Lobby.__init__(self, chat_id, skip_armory=skip_armory)
        self.teams = []

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        for team in self.teams:
            bot_methods.send_image(image_generator.create_dungeon_image(path,
                                                                        (self.get_image(key) for key in team)),
                                   self.chat_id)
        result = self.run_fight(*[{chat_id: team[chat_id]['unit_dict'] for chat_id in team} for team in self.teams])

    def player_join(self, user_id, unit_dict):
        self.teams.append({})
        self.join_lobby(user_id, unit_dict, self.teams[-1])


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
        try:
            self.lobby.run()
        except Exception:
            import traceback
            bot_methods.err(traceback.format_exc())


class Dungeon(Lobby):
    def __init__(self, chat_id, map_type):
        Lobby.__init__(self, chat_id, skip_armory=False)
        self.table_row = 'dungeons_' + map_type.name
        self.team = self.teams[0]
        self.map = None
        self.party = None
        self.fight = None
        self.complexity = None
        self.map_type = map_type
        self.text = self.get_lang_tuple('recruit_text')
        self.lang = 'rus'

    def __str__(self):
        return str(self.id)

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        bot_methods.send_image(image_generator.create_dungeon_image(path,
                                                                    (self.get_image(key) for key in self.team)),
                               self.chat_id)
        # len(self.teams)
        self.complexity = 1
        self.create_dungeon_map()
        dynamic_dicts.dungeons[self.id] = self
        self.add_party(player_list=self.team)
        for member in self.party.members:
            dynamic_dicts.dungeons[member.chat_id] = self
        bot_methods.send_message(self.chat_id, localization.LangTuple('utils', 'fight_start')
                                 .translate(self.lang))
        del dynamic_dicts.lobby_list[self.id]
        self.map.start()

    def get_event_list(self):
        # return [(dungeon_events.GoblinChaser, 1)]
        return []

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
        self.delete_map()
        try:
            if not defeat:
                for team in self.teams:
                    for key in team:
                        dynamic_dicts.occupied_list.remove(key)
        except:
            pass
        for member in self.party.members:
            del dynamic_dicts.dungeons[member.chat_id]

        message = self.form_result_string(farmed_resources, self.party.collected_receipts.to_string('rus'))
        bot_methods.send_message(self.chat_id,
                                 message)
        chat = pyossession.get_chat(self.chat_id)
        chat.add_resources(farmed_resources)
        chat.add_receipt(self.party.collected_receipts)
        if not defeat:
            chat.add_receipt(self.party.collected_receipts)
        user_list = list(map(get_user, [member.chat_id for member in self.party.members]))
        self.party.distribute_experience(user_list)

    def form_result_string(self, resources, receipts_string, boss_beaten=False):
        message = 'Поход группы {} окончен.\n' \
                  ' Количество заработанных ресурсов - {}\n'.format(self.party.leader.name, resources)
        if receipts_string != 'Пусто.':
            message += 'Группа добыла рецепты: {}'.format(receipts_string)
        return message

    def create_dungeon_map(self):
        self.map_type(self).create_map()

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


class MobFight(Lobby):
    def __init__(self, chat_id, mob_list):
        Lobby.__init__(self, chat_id, skip_armory=False)
        self.team = self.teams[0]
        self.complexity = None
        self.mob_list = mob_list
        self.lang = 'rus'
        self.image = file_manager.my_path + '/files/images/backgrounds/dragon_lair.png' if bot_methods.images else None
        self.text = 'ЕТО ДРАКОН РРРРРРР'

    def __str__(self):
        return str(self.id)

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        bot_methods.send_image(image_generator.create_dungeon_image(path,
                                                                    (self.get_image(key) for key in self.team)),
                               self.chat_id, message=','.join([self[key]['unit_dict']['name'] for key in self.team.keys()]))
        result = self.run_fight(*[{chat_id: self.team[chat_id]['unit_dict'] for chat_id in self.team}, {units.units_dict[mob]: units.units_dict[mob]().to_dict() for mob in self.mob_list}])


class AttackLobby(Lobby):
    def __init__(self, chat, attack_action, target_chat):
        Lobby.__init__(self, chat.chat_id, skip_armory=False)
        self.team = self.teams[0]
        self.attack_action = attack_action
        attack_action.attacker_lobby = self
        self.target_chat_id = target_chat.chat_id
        self.target_chat_name = target_chat.name
        self.target_chat = target_chat
        self.defence_send = False
        self.chat = chat
        self.text = 'Нападение на чат {}'.format(self.target_chat_name)

    def join_forbidden(self, user_id):
        if Lobby.join_forbidden(self, user_id):
            return True
        if self.attack_action.defender_lobby is not None and user_id in self.attack_action.defender_lobby.team:
            return True
        return False

    def run_next_step(self, user_id, message_id=None):
        if not self.defence_send:
            DefenceLobby(self.attack_action, self).send_lobby()
            self.defence_send = True
        Lobby.run_next_step(self, user_id, message_id=message_id)

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        image = image_generator.create_dungeon_image(path, (self.get_image(key) for key in self.team))
        caption = ', '.join([self[key]['unit_dict']['name'] for key in self.team.keys()])
        bot_methods.send_image(image, self.attack_action.defender_lobby.chat_id, message=caption)
        bot_methods.send_image(image, self.chat_id, message=caption)
        self.attack_action.attack_ready = True
        if self.attack_action.defense_ready:
            self.attack_action.start()

    def to_team(self):
        team_dict = {chat_id: self.team[chat_id]['unit_dict'] for chat_id in self.team}
        team_dict['marker'] = 'attacker'
        return team_dict


class DefenceLobby(Lobby):
    def __init__(self, attack_action, attack_lobby):
        Lobby.__init__(self, attack_lobby.target_chat.chat_id, skip_armory=False)
        self.chat = attack_lobby.target_chat
        self.team = self.teams[0]
        self.attack_action = attack_action
        attack_action.defender_lobby = self
        self.attack_lobby = attack_lobby
        self.name = attack_lobby.target_chat.name
        self.text = 'Защита от чата {}'.format(attack_lobby.chat.name)

    def run(self):
        path = file_manager.my_path + '/files/images/backgrounds/camp.jpg'
        image = image_generator.create_dungeon_image(path, (self.get_image(key) for key in self.team))
        caption = ', '.join([self[key]['unit_dict']['name'] for key in self.team.keys()])
        bot_methods.send_image(image, self.attack_action.attacker_lobby.chat_id, message=caption)
        bot_methods.send_image(image, self.chat_id, message=caption)
        self.attack_action.attack_ready = True
        if self.attack_action.attack_ready:
            self.attack_action.start()

    def join_forbidden(self, user_id):
        if Lobby.join_forbidden(self, user_id):
            return True
        if user_id in self.attack_action.attacker_lobby.team:
            return True
        return False

    def to_team(self):
        team_dict = {chat_id: self.team[chat_id]['unit_dict'] for chat_id in self.team}
        team_dict['marker'] = 'defender'
        return team_dict


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

        elif action == 'equipment':
            user_id = call.from_user.id
            unit_dict = lobby[user_id]['unit_dict']
            user = get_user(call.from_user.id)
            chat = get_chat(lobby.chat_id)
            item_type = call_data[3]
            item_name = call_data[-1]
            item = standart_actions.object_dict[item_name]() if item_name not in ['reset', 'ready'] else None
            if item_name == 'reset':
                if item_type == 'armor':
                    for armor in unit_dict['armor']:
                        chat.delete_used_item(armor['name'])
                    unit_dict['armor'] = []
                elif item_type == 'item':
                    for item_unit in unit_dict['inventory'].values():
                        chat.delete_used_item(item_unit[0]['name'], value=item_unit[1])
                    unit_dict['inventory'] = {}
                user.send_equipment_choice(call_data[1], chat.chat_id, item_type, message_id=call.message.message_id)
            elif item_name == 'ready':
                lobby[user_id]['equipment_choice'].pop()
                lobby.run_next_step(user_id, message_id=call.message.message_id)

            elif item_name not in chat.get_free_armory():
                bot_methods.answer_callback_query(call, 'Этого предмета уже нет на складе')
                user.send_equipment_choice(call_data[1], chat.chat_id, item_type, message_id=call.message.message_id)
            elif not item.try_placement(unit_dict):
                bot_methods.answer_callback_query(call, 'Вы не можете это экипировать.')

            elif item_type == 'weapon':
                chat.use_item(item_name)
                unit_dict['weapon'] = item.to_dict()
                lobby[user_id]['equipment_choice'].pop()
                lobby.run_next_step(user_id, message_id=call.message.message_id)
            elif item_type == 'armor':
                chat.use_item(item_name)
                unit_dict['armor'].append(item.to_dict())
                user.send_equipment_choice(call_data[1], chat.chat_id, item_type, message_id=call.message.message_id)
            elif item_type == 'item':
                chat.use_item(item_name)
                test = list(k for k, v in unit_dict['inventory'].items() if v[0]['name'] == item.name)
                if test:
                    unit_dict['inventory'][test[0]][1] += 1
                else:
                    unit_dict['inventory'][engine.rand_id()] = [item.to_dict(), 1]
                user.send_equipment_choice(call_data[1], chat.chat_id, item_type, message_id=call.message.message_id)


def send_mob_choice(chat_id):
    mob_list = ['dragon', 'ogre']
    buttons = []
    for mob in mob_list:
        buttons.append(keyboards.Button(mob, 'mobchoice_{}_{}'.format(mob, chat_id)))
    keyboard = keyboards.form_keyboard(*buttons)
    bot_methods.send_message(chat_id, 'Выберите противника', reply_markup=keyboard)


class MobChoiceHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        bot_methods.delete_message(call=call)
        MobFight(int(call_data[-1]), mob_list=[call_data[-2]]).send_lobby()