#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions, weapons
from locales import localization, emoji_utils
from bot_utils import keyboards, config
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
        self.current_coverage = self.get_coverage()
        self.armor += self.improved
        self.rating += self.improved
        self.destroyed = False

    def get_coverage(self):
        return self.coverage

    def try_placement(self, unit_dict):
        if any(armor_dict[armor['name']].placement == self.placement for armor in unit_dict['armor']):
            return False
        return True

    def block(self, dmg_done):
        blocked_damage = self.rating if self.armor > 0 else 0
        if blocked_damage > dmg_done:
            blocked_damage = dmg_done
        if self.destructable and not dmg_done > blocked_damage:
            self.dent(blocked_damage)
        return blocked_damage

    def dent(self, value):
        self.armor -= value
        if self.armor < 1:
            if not self.destroyed:
                self.destroy()
                self.destroyed = True

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

    def get_image_dict(self, user_id=None):
        return None


class Breastplate(Armor):
    name = 'breastplate'
    placement = 'body'
    max_armor = 5
    weight = 2
    rating = 2
    coverage = 25
    destructable = True
    real = True


class Cuirass(Armor):
    name = 'cuirass'
    placement = 'body'
    max_armor = 7
    weight = 3
    rating = 5
    coverage = 95
    destructable = True
    real = True


class Leather(Armor):
    name = 'leather'
    placement = 'body'
    max_armor = 10
    weight = 1
    rating = 1
    coverage = 15
    destructable = True
    real = True


class Helmet(Armor):
    name = 'helmet'
    placement = 'head'
    max_armor = 7
    rating = 5
    coverage = 5
    destructable = True
    real = True

    def get_image_dict(self, user_id=None):
        return {
         'handle': (26, 30),
         'placement': 'head',
         'file': './files/images/armor_heads/{}/cover_head.png'.format(self.name),
         'covered': False,
         'layer': 0
        }


class HeavyHelmet(Armor):
    name = 'heavy-helmet'
    placement = 'head'
    max_armor = 7
    rating = 10
    coverage = 10
    weight = 2
    destructable = True
    real = True

    def get_image_dict(self, user_id=None):
        if user_id is not None and user_id in config.special_units:
            file = './files/images/armor_heads/{}/{}/cover_head.png'.\
                    format(config.special_units[user_id], self.name)
            handle = list(int(item) for item in open('./files/images/armor_heads/{}/{}/cover_head_coord.txt'.format(config.special_units[user_id], self.name)).read().split())
        else:
            file = './files/images/armor_heads/common/{}/cover_head.png'.format(self.name)
            handle = (26, 37)
        return {
         'handle': handle,
         'placement': 'head',
         'file': file,
         'covered': False,
         'layer': 0
        }


class DragonHide(Armor):
    name = 'dragon_hide'
    placement = 'head'
    max_armor = 13
    rating = 10
    coverage = 80
    destructable = True
    real = True


class Mask(Armor):
    name = 'mask'
    placement = 'head'
    max_armor = 1
    rating = 0
    coverage = 0
    destructable = True
    real = True
    weight = 0

    def get_image_dict(self, user_id=None):
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

    def get_image_dict(self, user_id=None):
        return {
         'handle': (33, 35),
         'placement': 'head',
         'file': './files/images/mask_1.png',
         'covered': False,
         'layer': 0
        }


class Shield(Armor, weapons.OneHanded, weapons.Weapon):
    name = 'shield'
    types = ['usable', 'shield']
    placement = 'arm'
    max_armor = 5
    rating = 5
    coverage = 10
    order = 19
    destructable = True
    weight = 2
    real = True
    default_energy_cost = 2
    block_energy_cost = 1

    def get_image_dict(self, user_id=None):
        return {
         'handle': (66, 160),
         'placement': 'left_hand',
         'file': './files/images/weapons/shield_2.png',
         'covered': False,
         'layer': 2
        }

    def activate(self, action):
        unit = action.unit
        self.coverage -= 100
        self.unit.waste_energy(self.block_energy_cost)
        if self.armor <= 0:
            return False
        if unit.dmg_received > 0:
            if unit.dmg_received > self.armor and not self.destroyed:
                blocked_dmg = self.armor
                unit.dmg_received -= self.armor
                self.armor = 0
            elif self.destroyed:
                blocked_dmg = 0
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
        self.coverage += 100
        self.ask_action()

    def button(self):
        return keyboards.FightButton('name', self.unit, 'armor', self.name, special=self.get_table_row())

    def try_placement(self, unit_dict):
        if unit_dict['weapon'] is not None:
            weapon = standart_actions.object_dict[unit_dict['weapon']['name']]
            if not weapon.melee or 'two-handed' in weapon.core_types:
                return False
        return Armor.try_placement(self, unit_dict)


class HeavyShield(Shield):
    name = 'heavy-shield'
    types = ['usable', 'shield']
    placement = 'arm'
    max_armor = 10
    rating = 8
    coverage = 15
    weight = 5
    default_energy_cost = 4
    block_energy_cost = 1
    real = True

    def get_image_dict(self, user_id=None):
        return {
         'handle': (106, 240),
         'placement': 'left_hand',
         'file': './files/images/weapons/heavy-shield.png',
         'covered': False,
         'layer': 2
        }

    def available(self):
        if self.armor > 0 and self.unit.energy > 0:
            return True
        return False


armor_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None and value.real}

for k, v in armor_dict.items():
    standart_actions.object_dict[k] = v
