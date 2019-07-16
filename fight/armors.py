#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions
from locales import localization, emoji_utils
from bot_utils import keyboards
import sys
import inspect


class Armor(standart_actions.GameObject):
    name = None
    core_types = ['armor']
    db_string = 'armor'
    placement = 'body'
    max_armor = 0
    coverage = 0
    weight = 1
    covering = True
    rating = 0
    destructable = True
    real = True
    emote = emoji_utils.emote_dict['shield_em']

    def __init__(self, unit=None, damage_left=0, obj_dict=None):
        standart_actions.GameObject.__init__(self, unit)
        self.armor = self.max_armor if not damage_left else damage_left
        self.improved = 0
        self.armor += self.improved
        self.rating += self.improved

    def try_placement(self, unit_dict):
        if any(armor_dict[armor['name']].placement == self.placement for armor in unit_dict['armor']):
            return False
        return True

    def block(self, dmg_done):
        blocked_damage = self.rating if self.armor else 0
        if blocked_damage > dmg_done:
            blocked_damage = dmg_done
        if self.destructable and not dmg_done > blocked_damage:
            self.dent(blocked_damage)
        return blocked_damage

    def dent(self, value):
        self.armor -= value
        if self.armor < 1:
            self.destroy()

    def destroy(self):
        standart_actions.AddString(localization.LangTuple('armor_' + self.name, 'destroyed',
                                                          format_dict={'name': self.unit.name}), 23, self.unit)

    def clear(self):
        pass

    def to_dict(self):
        this_dict = standart_actions.GameObject.to_dict(self)
        if self.improved != self.__class__().improved:
            this_dict['improved'] = self.improved
        return this_dict

    def available(self):
        return False


class Breastplate(Armor):
    name = 'breastplate'
    placement = 'body'
    max_armor = 5
    weight = 2
    rating = 2
    coverage = 30
    destructable = True
    real = True

    def get_image_dict(self):
        return {
         'handle': (55, 90),
         'placement': 'body_armor',
         'file': './files/images/breastplate.png',
         'covered': 'scarf',
         'layer': 3
        }


class Helmet(Armor):
    name = 'helmet'
    placement = 'head'
    max_armor = 5
    rating = 5
    coverage = 10
    destructable = True
    real = True

    def get_image_dict(self):
        return {
         'handle': (26, 30),
         'placement': 'head',
         'file': './files/images/helmet.png',
         'covered': False,
         'layer': 0
        }


class Mask(Armor):
    name = 'mask'
    placement = 'head'
    max_armor = 1
    rating = 0
    coverage = 0
    destructable = True
    real = True
    weight = 0

    def get_image_dict(self):
        return {
         'handle': (49, 70),
         'placement': 'head',
         'file': './files/images/mask.png',
         'covered': False,
         'layer': 0
        }


class SteamPunk_Mask(Armor):
    name = 'steampunk_mask'
    placement = 'head'
    max_armor = 1
    rating = 0
    coverage = 0
    destructable = True
    real = True
    weight = 0

    def get_image_dict(self):
        return {
         'handle': (33, 35),
         'placement': 'head',
         'file': './files/images/mask_1.png',
         'covered': False,
         'layer': 0
        }


class Shield(Armor):
    name = 'shield'
    types = ['usable']
    placement = 'arm'
    max_armor = 5
    rating = 5
    coverage = 10
    order = 19
    destructable = True
    weight = 2
    real = True

    def get_image_dict(self):
        return {
         'handle': (66, 160),
         'placement': 'left_hand',
         'file': './files/images/shield_2.png',
         'covered': False,
         'layer': 2
        }

    def activate(self, action):
        unit = action.unit
        if not self.armor:
            return False
        if unit.dmg_received > 0:
            if unit.dmg_received > self.armor:
                blocked_dmg = self.armor
                unit.dmg_received -= self.armor
                self.armor = 0
            else:
                blocked_dmg = unit.dmg_received
                self.armor -= unit.dmg_received
                unit.dmg_received = 0
            self.string('use', format_dict={'actor': unit.name, 'dmg': blocked_dmg})

            if self.armor <= 0:
                self.destroy()
        else:
            self.string('use_fail', format_dict={'actor': unit.name})

    def available(self):
        if self.armor > 0:
            return True
        return False

    def act(self, action):
        self.unit.fight.action_queue.append(action)
        for action_type in action.action_type:
            self.unit.action.append(action_type)
        self.on_cd()
        self.ask_action()

    def button(self):
        return keyboards.FightButton('name', self.unit, 'armor', self.name, special=self.get_table_row())

    def try_placement(self, unit_dict):
        if unit_dict['weapon'] is not None:
            weapon = standart_actions.object_dict[unit_dict['weapon']['name']]
            if not weapon.melee or 'two-handed' in weapon.core_types:
                return False
        return Armor.try_placement(self, unit_dict)


armor_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None and value.real}

for k, v in armor_dict.items():
    standart_actions.object_dict[k] = v
