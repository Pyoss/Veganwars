#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions
from locales import localization
import sys
import inspect


class Armor(standart_actions.GameObject):
    name = None
    core_types = ['armor']
    db_string = 'armor'
    max_armor = 0
    coverage = 0
    rating = 0
    destructable = True
    real = True

    def __init__(self, actor=None, damage_left=0, obj_dict=None):
        standart_actions.GameObject.__init__(self, actor)
        self.armor = self.max_armor if not damage_left else damage_left
        self.improved = 0
        self.max_armor += self.improved
        self.rating += self.improved

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


class Breastplate(Armor):
    name = 'breastplate'
    max_armor = 5
    rating = 2
    coverage = 30
    destructable = True
    real = True


class Helmet(Armor):
    name = 'helmet'
    max_armor = 5
    rating = 5
    coverage = 10
    destructable = True
    real = True


class Shield(Armor):
    name = 'shield'
    max_armor = 5
    rating = 2
    coverage = 0
    destructable = False
    real = True


class Skeleton(Armor):
    name = 'skeleton'
    rating = 2
    max_armor = 2
    coverage = 100
    destructable = True


armor_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None and value.real}

for k, v in armor_dict.items():
    standart_actions.object_dict[k] = v
