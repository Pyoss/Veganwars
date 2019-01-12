#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions, statuses, weapons, units
from bot_utils import keyboards, bot_methods, config
from locales.localization import *
import time
import random
import engine
import threading
import dynamic_dicts


def thread_fight(game, *args, chat_id=None):
    # В качестве аргумента должны быть переданы словари команд в виде
    # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
    target = run_fight
    args = [game, *args]
    kwargs = {'chat_id': chat_id}
    thread = threading.Thread(target=target, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()


def run_fight(game, *args, chat_id=None):
    # В качестве аргумента должны быть переданы словари команд в виде
    # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
    fight = Fight(chat_id=chat_id)
    fight.form_teams(args)
    results = fight.run()
    return results


class Team:
    def __init__(self, *args):
        self.units = list(args)
        self.captain = self.units[0]

    def name(self):
        if len(self.units) < 2:
            return self.captain.name
        else:
            return LangTuple('fight', 'team', format_dict={'team_name': self.captain.name})

    def alive_actors(self):
        return (unit for unit in self.units if unit.alive())


class Player:
    ai = False

    def __init__(self, chat_id, lang, fight):
        self.lang = lang
        self.chat_id = chat_id
        self.message_id = None
        self.player_string = PlayerString(self)
        self.fight = fight
        self.unit = None

    def get_action(self, edit=False):
        self.unit.active = True
        self.ask_action(edit=edit)

    def ask_action(self, edit=False):
        keyboard = keyboards.form_turn_keyboard(self.unit)
        lang_tuple = self.unit.menu_string()
        if not edit:
            self.message_id = self.send_message(lang_tuple, reply_markup=keyboard).message_id
        else:
            self.edit_message(lang_tuple, reply_markup=keyboard)

    def end_turn(self):
        self.unit.done = True
        self.delete_message()

    def forced_end_turn(self):
        self.unit.done = True
        self.edit_message(LangTuple('fight', 'time_up'))
        statuses.AFK(self.unit)
        self.fight.action_queue.append(standart_actions.Skip(self.unit, self.fight))

    def send_message(self, lang_tuple, reply_markup=None):
        return bot_methods.send_message(self.chat_id, lang_tuple.translate(self.lang), reply_markup=reply_markup)

    def edit_message(self, lang_tuple, reply_markup=None):
        return bot_methods.edit_message(self.chat_id, self.message_id,
                                        lang_tuple.translate(self.lang), reply_markup=reply_markup)

    def delete_message(self):
        bot_methods.delete_message(self.chat_id, self.message_id)


class ActionQueue:
    def __init__(self):
        self.action_list = []

    def append(self, action):
        self.action_list.append(action)

    def run_queue_section(self, order_limit):
        while self.action_list:
            if self.action_list[-1].order <= order_limit:
                self.action_list.pop().activate()
            else:
                break

    def run_actions(self):
        self.action_list.sort(key=lambda x: x.order, reverse=True)
        self.run_queue_section(20)

    def run_effects(self):
        self.run_queue_section(40)

    def run_post_results(self):
        self.run_queue_section(60)


class Fight:
    def __init__(self, chat_id=None, test=False):
        self.turn = 1
        self.id = str(engine.rand_id())
        self.chat_id = chat_id
        self.units_dict = dict()
        self.units = list()
        self.langs = ['rus']
        self.lang = self.langs[0]
        self.dead = {}
        self.teams = []
        self.public = True
        self.listeners = list()
        self.action_queue = ActionQueue()
        self.string_tuple = FightString(self)
        dynamic_dicts.fight_dict[str(self.id)] = self

    #  ---------- Основная функция, отвечающая за сражение между готовыми командами -------

    def run(self):
        # self._send_chosen_weapons_()
        results = self.fight_loop()
        return results

    def send_message(self, *args):
        message = PlayerString(self)
        message.row(*args)
        message.construct()
        return bot_methods.send_message(self.chat_id, message.result_dict[self.lang])

    def unit_talk(self, unit_id, text):
        unit = self.units_dict[unit_id]
        if not unit.controller.talked:
            unit.controller.talked = True
            for teammate in unit.team:
                if not unit.controller.ai and unit != teammate:
                    pass


    def add_player(self, chat_id, name, unit_dict=None):
        # Добавление бота в словарь игроков и список игроков конкретного боя
        controller = Player(chat_id, 'rus', self)
        unit_class = units.units_dict[unit_dict['unit_name']] if unit_dict is not None else units.Zombie
        unit = unit_class(name, controller=controller, fight=self, unit_dict=unit_dict)
        self.units_dict[unit.id] = unit
        dynamic_dicts.unit_talk[unit.id] = self
        self.units.append(unit)
        self.listeners.append(controller)
        return unit

    def add_ai(self, unit, name, unit_dict=None, **kwargs):
        print(kwargs)
        if isinstance(unit, tuple):
            unit = unit[0]
        print(unit)
        print(unit.control_class)
        controller = unit.control_class(self)
        unit = unit(name, controller=controller, fight=self, unit_dict=unit_dict, **kwargs)
        if unit.name is None:
            print(unit.name)
            unit.form_ai_name()
            unit.named = False
        if unit.weapon is None:
            unit.weapon = weapons.weapon_dict[unit.default_weapon](unit)
        self.units_dict[unit.id] = unit
        self.units.append(unit)
        return unit

    def add_unit(self, delta, name, unit_dict=None):
        if isinstance(delta, int):
            return self.add_player(delta, name, unit_dict=unit_dict)
        else:
            return self.add_ai(delta, name, unit_dict=unit_dict)

    def form_teams(self, team_dicts):
        # [team={chat_id:(name, unit_dict)} or team={(ai_class.name, id):(name/None, unit_dict)}]
        print(team_dicts)
        self.teams = [Team(*[self.add_unit(key, value['name'],
                                           unit_dict=value) for key, value in team_dict.items()])
                      for team_dict in team_dicts]
        for team in self.teams:
            for actor in team.units:
                actor.team = team

    def add_team(self, team):
        self.teams.append(team)
        for unit in team.units:
            unit.fight = self
            self.units.append(unit)
            self.units_dict[unit.chat_id] = unit
            unit.team = team

    def choose_build(self):
        for unit in self.units:
            unit.start_abilities()

    def _send_chosen_weapons_(self):
        weapon_string = emote_dict['weapon_em'] +\
                        '|Выбор оружия\n' \
                        + '\n'.join([unit.name
                                     + ' - '
                                     + LangTuple(unit.weapon.table_row, 'name').translate(self.lang)
                                    if isinstance(unit.name, str) else unit.name.translate(self.lang)
                                    + ' - ' + LangTuple(unit.weapon.table_row, 'name').translate(self.lang)
                                    for unit in self.units])
        bot_methods.send_message(self.chat_id, weapon_string)

    def active_actors(self):
        return [unit for unit in self.units if unit.alive() and not unit.disabled]

    def players(self):
        return [unit for unit in self.units if not unit.controller.ai]

    def alive_units(self):
        return [unit for unit in self.units if unit.alive()]

    def announce(self, lang_tuple, image=None):
        for listener in [listener for listener in self.listeners if listener.chat_id != self.chat_id]:
            text = lang_tuple.translate(listener.lang)
            if image is None:
                bot_methods.send_message(listener.chat_id, text)
            else:
                bot_methods.send_image(image, listener.chat_id, text)

    def fight_loop(self):
        while self.in_progress():
            self.fill_active_actors()
            self.activate_statuses_and_passives()
            self.get_action()
            self.execute_queue()
            self.get_results()
            self.act_results()
            self.action_queue.run_post_results()
            self.kill_units()
            self.send_string()
            self.refresh()
        self.clear()
        return self.ending()

    def clear(self):
        for player in self.players():
            player.clear()

    def in_progress(self):
        if len([team for team in self.teams if any(unit.alive() for unit in team.units)]) > 1:
            return True
        return False

    def fill_active_actors(self):
        for unit in self.active_actors():
            if not unit.controller.ai:
                unit.done = False
                unit.active = True
            unit.get_targets()

    def activate_statuses_and_passives(self):
        for unit in self.alive_units():
            unit.activate_passives()
        for unit in self.units:
            unit.activate_statuses()

    def get_action(self):
        for unit in self.active_actors():
            unit.get_action()
        self.wait_action()

    def wait_action(self):
        x = 0
        while not all(unit.done for unit in self.active_actors()) and x < config.turn_time:
            time.sleep(1)
            x += 1
        for actor in [unit for unit in self.active_actors() if not unit.done]:
            actor.active = False
        for actor in [unit for unit in self.active_actors() if not unit.done]:
            actor.controller.forced_end_turn()

    def execute_queue(self):
        self.string_tuple.row(LangTuple('fight', 'turn', {'turn_number': self.turn}))
        self.action_queue.run_actions()
        self.string_tuple.block('effects')
        self.action_queue.run_effects()

    # Определение команды, получившей больше всего урона. Отъем жизней.
    def get_results(self):

        # Выясняется победившая команда сравнением полученного командами урона
        dmg_received_dict = {team: sum(unit.dmg_received for unit in team.units if unit.alive()) for team in self.teams}

        # Команда(ды), получившая наибольшее количество урона, считается проигравшей
        losers = [key for key, value in dmg_received_dict.items()
                  if value == max(value for key, value in dmg_received_dict.items())]\

        # Расстановка блока результатов
        self.string_tuple.block('results')

        # Отнятие жизней
        for team in losers:
            for unit in team.units:
                unit.lose_round()

    def act_results(self):

        for unit in self.alive_units():
            unit.energy -= unit.wasted_energy
            if unit.hp_delta > 0:
                if unit.hp_delta + unit.hp > unit.max_hp:
                    unit.hp_delta = unit.max_hp - unit.hp
                unit.hp += unit.hp_delta
                self.string_tuple.row(LangTuple('fight', 'hp_gain', format_dict={'actor': unit.name,
                                                                                 'hp': unit.hp,
                                                                                 'hp_delta':  unit.hp_delta,
                                                                                 'hp_was': unit.hp - unit.hp_delta}))
            elif unit.hp_delta < 0 or unit.hp_changed:
                if abs(unit.hp_delta) > unit.hp:
                    unit.hp_delta = - unit.hp
                unit.hp += unit.hp_delta
                self.string_tuple.row(LangTuple('fight', 'hp_loss', format_dict={'actor': unit.name,
                                                                                 'hp': unit.hp,
                                                                                 'hp_delta':  abs(unit.hp_delta)}))

    def kill_units(self):
        for unit in self.units:
            if unit.dies():
                self.dead[unit] = True

    def send_string(self):
        self.string_tuple.construct()
        if self.string_tuple.active:
            for listener in [listener for listener in self.listeners if listener.chat_id != self.chat_id]:
                time.sleep(2)
                listener.send_message(self.string_tuple[listener.lang])
                if not listener.unit.alive():
                    self.listeners.remove(listener)
            if self.public:
                self.send_message(self.string_tuple[self.lang])
        self.string_tuple.clear()

    def refresh(self):
        for unit in self.units:
            unit.refresh()
        self.turn += 1

    def ending(self):
        won_teams = [team for team in self.teams if any(unit.alive() for unit in team.units)]
        if won_teams:
            self.string_tuple.row(LangTuple('fight', 'winner', {'team_name': won_teams[0].name()}))
        else:
            self.string_tuple.row(LangTuple('fight', 'draw'))

        ending_dict = {'winners': [], 'loser': [], 'loot': engine.Container()}
        for team in self.teams:
            if team in won_teams:
                for unit in team.units:
                    if not unit.summoned:
                        ending_dict['winners'].append(unit.to_dict())
            else:
                for unit in team.units:
                    if not unit.summoned:
                        ending_dict['loser'].append(unit.to_dict())
                        if not unit.alive():
                            loot = unit.generate_loot()
                            ending_dict['loot'] += loot
        del dynamic_dicts.fight_dict[str(self.id)]
        return ending_dict

    def edit_queue(self, action):
        self.action_queue.append(action)
        self.sort_queue()

    def sort_queue(self):
        self.action_queue.action_list.sort(key=lambda x: x.order, reverse=True)

    def __str__(self):
        return str(self.id)

    def __getitem__(self, item):
        return self.units_dict[int(item)]
