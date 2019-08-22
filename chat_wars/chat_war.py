from fight import fight_main
from threading import Thread
from bot_utils.bot_methods import send_message
from bot_utils import keyboards
from sql_alchemy import Pyossession
from dynamic_dicts import occupied_list

import engine


class GlobalWar:
    def __init__(self):
        self.stage = 'siege'
        self.stage_choices = ['siege', 'peace', 'before_attack', 'before_siege']
        self.war_actors = {}
        self.id = str(engine.rand_id())
        self.attacked_dict = {}
        self.attacked_chat = {}
        self.attacking_lobby = {}

    def add_user_to_attacked(self, user_id):
        self.attacked_dict[user_id] = 1

    def start_siege(self):
        self.announce_siege()
        self.stage = 'siege'
        self.id = str(engine.rand_id())

    def start_attack(self):
        self.announce_attack()
        self.stage = 'attack'
        self.id = str(engine.rand_id())

    def next_step(self, chat_id):
        if self.stage == 'before_siege':
            self.start_siege()
            send_message(chat_id, 'Текущий этап войны - осада.')
        elif self.stage == 'siege':
            self.stage = 'before_attack'
            self.refresh_users()
            send_message(chat_id, 'Текущий этап войны - мир.')
        elif self.stage == 'before_attack':
            self.start_attack()
            send_message(chat_id, 'Текущий этап войны - атака.')
        elif self.stage == 'attack':
            self.stage = 'before_siege'
            self.refresh_users()
            self.get_results()
            send_message(chat_id, 'Текущий этап войны - мир.')


    def get_results(self):
        from chat_wars.chat_main import Chat, User
        pyossession = Pyossession(Chat, User)
        chats = pyossession.get_chats()
        for chat in chats:
            war_data = chat.get_current_war_data()
            if war_data['attacked_by_chats']:
                for attacked_chat in war_data['attacked_by_chats']:
                    won_chat = pyossession.get_chat(attacked_chat)
                    prize_amount = chat.get_prize()
                    chat.add_resources(-prize_amount)
                    won_chat.add_resources(prize_amount)
                    send_message(chat.chat_id, 'Чат {} отнимает у вас {} ресурсов'.format(won_chat.name, prize_amount))
                    send_message(won_chat.chat_id, 'Вы отнимаете {} ресурсов у чата {}'.format(prize_amount, chat.name))
            chat.set_current_war_data({"attacked_by_chats": [], "attacks_left": 1, "chats_besieged": []})

    def add_attack_lobby(self, attacker_id, target_id):
        if attacker_id in self.attacking_lobby:
            self.attacking_lobby[attacker_id].append(target_id)
        else:
            self.attacking_lobby[attacker_id] = [target_id]

    def lobby_exists(self, attacker_id, target_id):
        if attacker_id in self.attacking_lobby:
            if target_id in self.attacking_lobby[attacker_id]:
                return True
        return False

    def release_attack_lobby(self, attacker_id, target_id):
        self.attacking_lobby[attacker_id].remove(target_id)
        if not self.attacking_lobby[attacker_id]:
            del self.attacking_lobby[attacker_id]


    def refresh_users(self):
        self.attacked_dict = {}
        self.attacked_chat = {}

    def announce_siege(self):
        pass

    def announce_attack(self):
        pass


class AttackAction:
    def __init__(self):
        self.attacker_lobby = None
        self.defender_lobby = None
        self.results = None
        self.defense_ready = False
        self.attacker_ready = False
        self.mode = None

    def get_all_user_ids(self):
        user_list = [key for key in self.attacker_lobby.team]
        user_list = [*user_list, *[key for key in self.defender_lobby.team]]
        return user_list

    def add_users_to_attacked(self):
        for user_id in self.get_all_user_ids():
            current_war.add_user_to_attacked(user_id)

    def add_chat_to_attacked(self):
        chat = self.attacker_lobby.chat_id
        if chat in current_war.attacked_chat:
            current_war.attacked_chat[chat][1] += 1
            current_war.attacked_chat[chat][0].append(self.defender_lobby.chat_id)
        else:
            current_war.attacked_chat[chat] = ([self.defender_lobby.chat_id], 1)

    def start(self):
        args = [self.attacker_lobby.to_team(), self.defender_lobby.to_team()]
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
        self.add_users_to_attacked()
        self.add_chat_to_attacked()
        if len(args[1]) < 2:
            self.process_results({'won_team': 'attacker'})
        else:
            fight = fight_main.Fight((self.attacker_lobby.chat_id, self.defender_lobby.chat_id))
            fight.form_teams(args)
            thread = Thread(target=fight.run, kwargs={'func': self.process_results})
            thread.daemon = True
            thread.start()

    def process_results(self, fight_results):
        if fight_results['won_team'] == 'attacker':
            if self.mode == 'siege':
                button = keyboards.Button('Осадить', callback_data='_'.join(['mngt', str(self.attacker_lobby.chat_id), 'besiege',
                                                                             str(self.defender_lobby.chat_id),
                                                                             current_war.id]))
                keyboard = keyboards.form_keyboard(
                    button
                )
                send_message(self.attacker_lobby.chat_id,
                             'Битва выиграна! Вы можете осадить чат {}'.format(self.defender_lobby.name),
                             reply_markup=keyboard)
            elif self.mode == 'attack':
                button = keyboards.Button('Грабить!', callback_data='_'.join(['mngt', str(self.attacker_lobby.chat_id), 'marauder',
                                                                             str(self.defender_lobby.chat_id),
                                                                             current_war.id]))
                keyboard = keyboards.form_keyboard(
                    button
                )
                send_message(self.attacker_lobby.chat_id,
                             'Битва выиграна! Вы можете ограбить чат {}'.format(self.defender_lobby.name),
                             reply_markup=keyboard)
        else:
            if self.mode == 'siege':
                send_message(self.attacker_lobby.chat_id,
                             '{} отбивает вашу попытку осады!'.format(self.defender_lobby.name))
            elif self.mode == 'attack':
                send_message(self.attacker_lobby.chat_id,
                             '{} успешно обороняется!'.format(self.defender_lobby.name))
        for user_id in self.get_all_user_ids():
            if user_id in occupied_list:
                occupied_list.remove(user_id)

current_war = GlobalWar()

