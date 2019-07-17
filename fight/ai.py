#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
from fight.standart_actions import MoveBack, MoveForward, SpecialWeaponAction, Item, MeleeReload, Ability, SpecialWeaponOption, Attack
from operator import attrgetter
import engine



def get_lowest_hp(team):
    try:
        if team:
            return min(team, key=attrgetter('hp'))
        else:
            return None
    except AttributeError:
        return random.choices(team)


def get_lowest_energy(team):
    if team:
        return min(team, key=attrgetter('energy'))
    else:
        return None


def get_largest_opponent_team(actor, game):
    i = 0
    for team in game.lobby:
        if actor not in team and len(team) > i:
            i = len(team)
    return i


class Ai:
    ai = True

    def __init__(self, fight):
        self.number = 0
        self.fight = fight
        self.chat_id = id(self)
        self.action_dict = {}
        self.done = True
        self.difficulty = 0
        self.unit = None
        self.talked = False

    def form_actions(self):
        pass

    def find_target(self):
        pass

    def add_action(self, action_class, chance, **kwargs):
        action = action_class(self.unit, self.fight, **kwargs)
        if 'ability' in action.types:
            if not action.ability.available():
                return False
        if 'item' in action.types:
            if not action.item.available():
                return False
        self.action_dict[action] = chance

    def action_ability(self, name, chance, target=None):
        info = ['fgt', str(self.fight), str(self.unit), 'ability', name]
        if target is not None:
            info.append(str(target))
        self.add_action(Ability, chance,
                        info=info)

    def action_item(self, name, chance, *args):
        info = ['fgt', str(self.fight), str(self.unit), 'item', name]
        for arg in args:
            info.append(arg)
        self.add_action(Item, chance,
                        info=info)

    def action_weapon(self, chance, target=None):
        info = ['fgt', str(self.fight), 'special']
        if target is not None:
            info.append(str(target))
        self.add_action(SpecialWeaponAction, chance,
                        info=info)

    def action_weapon_option(self, chance, option):
        info = ['fgt', str(self.fight), str(self.unit), 'wpspecial', option]
        self.add_action(SpecialWeaponOption, chance, info=info)

    def make_action(self, action_class, **kwargs):
        action_class(self.unit, self.fight, **kwargs).act()

    def clear_actions(self):
        self.action_dict = {}

    def get_action(self, edit=False):
        self.form_actions()
        print('Выбор действий моба ' + self.unit.name.translate(self.fight.lang) + ':')
        print('Энергия: {}'.format(self.unit.energy))
        for a in self.action_dict:
            print(str(a.name) + '     ' + str(self.action_dict[a]))
        chance_sum = sum([value for key, value in self.action_dict.items()])
        if chance_sum == 0:
            return False
        current_chance = random.randint(1, chance_sum)
        actions = list(self.action_dict.items())
        at = 1
        for action in actions:
            if current_chance in range(at, at + action[-1]):
                action[0].act()
                return True
            at += action[-1]

    def move_forward(self, chance):
            self.add_action(MoveForward, chance)

    def move_back(self, chance):
            self.add_action(MoveBack, chance)

    def attack(self, chance):
            self.add_action(Attack, chance)

    def reload(self, chance):
            self.add_action(MeleeReload, chance)

    def end_turn(self):
        self.unit.done = True


class StandardMeleeAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_energy(self.unit.weapon.targets())
            if engine.roll_chance(30):
                self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class TechAi(Ai):

    def get_action(self, edit=False):
        self.unit.done = True


# Монстры Артема
class ShadowAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_energy(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


# Монстры Пасюка
class SperMonsterAi(StandardMeleeAi):

    def form_actions(self):
        StandardMeleeAi.form_actions(self)
        self.make_action(self.unit.sperm_check_action)


class PedoBearAi(StandardMeleeAi):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.reload(1 if self.unit.energy < 1 else 0)
        if self.unit.energy > 0 and self.unit.target is not None:
            if self.unit.locked_in is not None:
                self.unit.target = self.unit.locked_in
                self.make_action(self.unit.hug_action)
            else:
                self.make_action(self.unit.find_target_action)


# Монстры Асгард
class BearAi(StandardMeleeAi):

    def find_target(self):
        stunned_targets = [target for target in self.unit.weapon.targets() if 'stun' in target.disabled]

        if stunned_targets:
            target = random.choice(stunned_targets)
        elif not self.unit.weapon.targets():
            target = None
        else:
            target = random.choice(self.unit.weapon.targets())
        self.unit.target = target

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        target = self.unit.target
        if target is not None:
            if 'stun' in target.disabled:
                self.add_action(self.unit.destroy_action, self.unit.energy)
            else:
                self.attack(self.unit.energy)


class BirdRukhAi(StandardMeleeAi):
    def __init__(self, fight):
        StandardMeleeAi.__init__(self, fight)
        self.charged = False

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if not self.charged:
            self.make_action(self.unit.stun_action)
            self.charged = True
        else:
            self.add_action(self.unit.fly_action, 1 if not self.unit.weapon.targets() else 0)
            self.attack(self.unit.energy if self.unit.target is not None else 0)
            self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class BasiliskAi(Ai):
    ai_name = 'basilisk'

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.stun_ready:
            self.add_action(self.unit.stun_action, 1)
        elif self.unit.hurt:
            self.add_action(self.unit.recovery_action, 1)
        else:
            self.add_action(self.unit.rush_action, 1 if not self.unit.weapon.targets() and self.unit.energy > 4 else 0)
            self.attack(self.unit.energy if self.unit.target is not None else 0)
            self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)




