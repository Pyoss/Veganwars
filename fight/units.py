#!/usr/bin/env python
# -*- coding: utf-8 -*-
from locales.localization import LangTuple
from locales.emoji_utils import emote_dict
from fight import standart_actions, weapons, ai, statuses, armors, abilities, items
from bot_utils.keyboards import *
import random
import engine
import uuid
import json
import inspect
import sys


class Unit:
    control_class = None
    unit_name = 'unit'
    emote = '?'
    types = ['alive']
    summoned = False

    # Список предметов, выпадающих из юнита при убийстве. Имеет вид [name: (quantity, chance)]
    loot = []
    # Вероятности, с которыми Вы можете получить оружие, броню или предметы цели при её смерти
    loot_chances = {'armor': 0, 'weapon': 0, 'items': 0}

    def __init__(self, name, controller=None, unit_dict=None, fight=None, complexity=None):

        # То, как осуществляется управление юнитом
        self.controller = controller
        if controller is not None:
            self.controller.unit = self
        self.done = False
        self.active = True

        # Список доступных действий для клавиатуры

        # Параметры игрока
        self.name = name
        self.id = engine.rand_id()
        self.fight = fight
        self.team = None
        self.lang = None
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.energy = 0
        self.weapon = weapons.Fist(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []

        # Параметры для боя
        self.default_weapon = weapons.Fist(self)
        self.lost_weapon = []
        self.boosted_attributes = {}

        # Временные параметры
        self.blocked_damage = 0
        self.dmg_received = 0
        self.wasted_energy = 0
        self.hp_delta = 0
        self.melee_targets = []
        self.statuses = {}
        self.target = None
        self.action = []
        self.disabled = []
        self.hp_changed = False

        # Параметры для ai
        self.number = 1
        self.named = True

    def available_actions(self):
        actions = [(1, WeaponButton(self, self.weapon)), (1, MoveForward(self)), (1, self.weapon.reload_button()),
                   (3, AdditionalKeyboard(self))]
        return actions

    def additional_actions(self):
        actions = [(1, MoveForward(self)), (1, MoveBack(self))]
        return actions

    def equip_from_dict(self, unit_dict):
        for key, value in unit_dict.items():
            setattr(self, key, value)
        if unit_dict['weapon'] is not None:
            self.weapon = weapons.weapon_dict[unit_dict['weapon']['name']](self, obj_dict=unit_dict['weapon'])
        else:
            self.weapon = weapons.weapon_dict[self.default_weapon](self)
        self.weapons = []
        self.abilities = [abilities.ability_dict[ability['name']](self, obj_dict=ability) for ability in unit_dict['abilities']]
        self.items = engine.Container(base_dict=unit_dict['inventory']).fight_list(self)
        self.inventory = engine.Container(base_dict=unit_dict['inventory']).inv_list(self)
        self.armor = [armors.armor_dict[armor['name']](self, obj_dict=armor) for armor in unit_dict['armor']]

    # -----------------------  Менеджмент энергии и жизней -----------------------------

    def recovery(self):
        pass

    def add_energy(self, number):
        pass

    def waste_energy(self, energy):
        self.wasted_energy += energy

    def change_hp(self, hp):
        self.hp_delta += hp
        self.hp_changed = True

    # -----------------------  Функции, связанные с оружием -----------------------------

    def equip_weapon(self, weapon):
        self.weapon = weapon

    def lose_weapon(self):
        weapon = self.weapon
        self.weapons.remove(weapon)
        self.lost_weapon.append(weapon)
        weapon.get_lost()
        if self.weapon == weapon:
            self.equip_weapon(self.default_weapon)

    def pick_up_weapon(self):
        self.get_weapon(self.lost_weapon[0])
        self.lost_weapon.remove(self.lost_weapon[0])

    def change_weapon(self):
        if len(self.weapons) > 1:
            self.weapon = self.weapons[0 if self.weapon == self.weapons[1] else 1]
        else:
            self.weapon = self.weapons[0]

    def get_weapon(self, weapon):
        self.weapons.append(weapon)
        self.weapon = weapon

    def get_hit_chance(self, weapon):
        # Шанс попасть в противника из заданного оружия
        return weapon.get_hit_chance()

    def add_weapon(self, weapon):
        self.weapon = weapon
        self.weapons.append(weapon)

    def change_attribute(self, attr, value):
        if hasattr(self, attr):
            setattr(self, attr, (getattr(self, attr) + value))

    # -----------------------  Функции, связанные с броней -----------------------------

    def equip_armor(self, armor):
        self.armor.append(self)

    # ------------------------  Менеджмент целей и движение -----------------

    def targets(self):
        return [unit for unit in self.fight.units if unit not in self.team.units and unit.alive()]

    def get_allies(self):
        return list([unit for unit in self.team.units if unit.alive()])

    def get_targets(self):
        for unit in self.melee_targets:
            if not unit.alive():
                self.melee_targets.remove(unit)

    def move_back(self):
        for actor in self.targets():
            if self in actor.melee_targets:
                actor.melee_targets.remove(self)
        self.melee_targets = []

    def move_forward(self):
        for unit in self.targets():
            if unit not in self.melee_targets:
                unit.melee_targets.append(self)
                self.melee_targets.append(unit)

    # ------------------------- Активация способностей -------------------

    def activate_statuses(self, sp_type=None, action=None):
        for k, v in self.statuses.items():
            if sp_type is not None:
                if sp_type in v.types and self.alive():
                    v.act(action=action)
            else:
                if self.alive() or 'permanent' in v.types:
                    v.act()

    def activate_abilities(self, sp_type, action=None):
        for ability in self.abilities:
            if sp_type in ability.types:
                ability.act(action=action)

    def on_hit(self, action):
        self.activate_statuses('on_hit', action=action)
        self.activate_abilities('on_hit', action=action)

    def receive_hit(self, action):
        # Применение брони
        print(self.statuses)
        if action.dmg_done > 0:
            self.activate_statuses('receive_hit', action=action)
        if action.dmg_done > 0:
            armor_data = self.activate_armor(action.dmg_done)
            if armor_data[0] >= action.dmg_done:
                action.dmg_done = 0
                action.armored = armor_data[1]
            self.activate_abilities('receive_hit', action)

    def activate_passives(self):
        self.activate_abilities('passive')

    def actions(self):
        return [action for action in self.fight.action_queue.action_list if action.unit == self]

    # -------------------------- Функции сообщений бота ---------------------

    def get_status_string(self):
        statuses_info = []
        for key, value in self.statuses.items():
            if value.menu_string():
                statuses_info.append(value.menu_string())
        return '|'.join(statuses_info)

    def add_armor_string(self):
        for key in self.act_armor_dict:
            armor_string = LangTuple('fight', 'armor', format_dict={'actor': self.name,
                                                                    'damage_blocked': self.act_armor_dict[key],
                                                                    'armor': LangTuple('armor', key)})
            standart_actions.AddString(armor_string, 22, self)
        self.act_armor_dict = {}

    def info_string(self):
        pass

    def menu_string(self):
        pass

    def start_abilities(self):
        for ability in self.abilities:
            if 'start' in ability.types:
                ability.start_act()

    def announce(self, lang_tuple, image=None):
        self.fight.announce(lang_tuple, image=image)

    # ---------------------------- Методы боя ------------------------------

    def refresh(self):
        self.dmg_received = 0
        self.active = False
        self.target = None
        self.action = []
        self.hp_changed = False

    def alive(self):
        pass

    def activate_armor(self, dmg_done):
        if not self.armor:
            return 0, None
        armor = list(self.armor)
        armor.sort(key=lambda x: x.rating)
        blocked_damage = 0
        acted_piece = None
        for piece in armor:
            chance = piece.coverage
            if engine.roll_chance(chance):
                blocked_damage = piece.block(dmg_done)
                acted_piece = piece
                break
        return blocked_damage, acted_piece

    def receive_damage(self, dmg_done):
        # Получение урона
        damage = dmg_done
        self.dmg_received += damage if damage > 0 else 0

    def lose_round(self):
        pass

    def dies(self):
        if not self.alive() and self not in self.fight.dead:
            self.fight.string_tuple.row(LangTuple('fight', 'death', format_dict={'actor': self.name}))
            return True
        return False

    # ---------------------------- Служебные методы ------------------------------

    def __str__(self):
        return str(self.id)

    def end_turn(self):
        self.controller.end_turn()

    def get_action(self, edit=False):
        self.controller.get_action(edit=edit)

    def stats(self):
        pass

    def clear(self):
        for armor in self.armor:
            armor.clear()

    def to_string(self, string, format_dict=None):
        lang_tuple = localization.LangTuple('unit_' + self.unit_name, string, format_dict=format_dict)
        return lang_tuple

    def string(self, string, format_dict=None, order=0):
        lang_tuple = self.to_string(string, format_dict=format_dict)
        if not order:
            self.fight.string_tuple.row(lang_tuple)
        else:
            standart_actions.AddString(lang_tuple=lang_tuple, unit=self, order=order)

    def create_action(self, name, func, button_name, order=5):
        if name not in standart_actions.action_dict:
            standart_actions.UnitAction(name, func, button_name, order=order)
        return standart_actions.action_dict[name]

    def action_button(self, name, button_name, available):
            button = FightButton(button_name, self, name, special='unit_' + self.unit_name)
            button.available = available
            return button

    def boost_attribute(self, key, value):
        if key in self.boosted_attributes:
            self.boosted_attributes[key] += value
        else:
            self.boosted_attributes[key] = value

    def form_ai_name(self):
        same_class_units = [unit for unit in self.fight.units if unit.unit_name == self.unit_name and not unit.named]
        if self.number == any(unit.number for unit in same_class_units):
            self.number = len(same_class_units) + 1
        if self.number == 1:
            self.name = localization.LangTuple('unit_' + self.unit_name, 'name')
        else:
            self.name = localization.LangTuple('unit_' + self.unit_name,
                                               'name-number', format_dict={'number': self.number})

    def summon_unit(self, unit_class, name=None, unit_dict=None, **kwargs):
        new_unit = self.fight.add_ai(unit_class, name=name, unit_dict=unit_dict, **kwargs)
        new_unit.team = self.team
        self.team.units.append(new_unit)
        new_unit.summoned = True
        return new_unit

    # Выдавание конечного списка лута при смерти.
    def generate_loot(self):
        loot = engine.Container()
        for item in self.loot:
            if engine.roll_chance(item[1][1]):
                loot.put(item[0], value=item[1][0])
        if engine.roll_chance(self.loot_chances['weapon']) and not self.weapon.natural:
            loot.put(self.weapon.name)
        for piece in self.armor:
            if engine.roll_chance(self.loot_chances['armor']):
                loot.put(piece.name)
        for item in self.items:
            if engine.roll_chance(self.loot_chances['items']):
                loot.put(item.name)
        return loot


class StandartCreature(Unit):

    danger = 7

    def __init__(self, name, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 6
        self.recovery_energy = 5
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapon = None
        self.default_weapon = 'fist'
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'recovery_energy': self.recovery_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]).base_dict,
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon
        }
        if unit_dict['weapon'] is not None:
            if unit_dict['weapon'].natural:
                unit_dict['weapon'] = None
            else:
                unit_dict['weapon'] = unit_dict['weapon'].to_dict()
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        if unit_dict['hp'] < 1:
            unit_dict['hp'] = 1
        return unit_dict

    def recovery(self):
        if self.recovery_energy:
            self.energy += self.recovery_energy
        else:
            self.energy = self.max_energy
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number
        self.recovery_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness


class Human(StandartCreature):
    unit_name = 'human'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        if unit_dict is None:
            self.abilities = [abilities.Dodge(self)]


class Necromancer(Human):
    unit_name = 'necromancer'
    control_class = ai.SkeletonAi
    emote = emote_dict['skeleton_em']

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 6
        self.recovery_energy = 5
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapon = weapons.Knife(self)
        self.weapons = []
        self.abilities = [abilities.Witch(self), abilities.Necromancer(self)]
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'recovery_energy': self.recovery_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': [*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        if unit_dict['hp'] < 1:
            unit_dict['hp'] = 1
        return unit_dict

    def recovery(self):
        if self.recovery_energy:
            self.energy += self.recovery_energy
        else:
            self.energy = self.max_energy
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number
        self.recovery_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness


class Pyromant(Human):
    unit_name = 'human'

    def __init__(self, name, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 6
        self.recovery_energy = 5
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapon = random.choice([weapons.Crossbow, weapons.Hatchet, weapons.Spear])(self)
        self.weapons = []
        self.abilities = [abilities.Muscle(self)]
        self.items = [items.Bandages(self), items.Bandages(self), items.Adrenalin(self)]
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'recovery_energy': self.recovery_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': [*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        if unit_dict['hp'] < 1:
            unit_dict['hp'] = 1
        return unit_dict

    def recovery(self):
        if self.recovery_energy:
            self.energy += self.recovery_energy
        else:
            self.energy = self.max_energy
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number
        self.recovery_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness


class Tech(Unit):
    control_class = ai.TechAi
    types = ['tech']
    summoned = True


class Skeleton(Unit):
    unit_name = 'skeleton'
    control_class = ai.SkeletonAi
    emote = emote_dict['skeleton_em']
    types = ['undead']
    broken_dict = {'head': 'skill_1', 'legs': 'skill_3', 'arms': 'skill_2'}
    greet_msg = 'текст-скелетов'
    image = 'AgADAgADBaoxG5L9kUuqFj563vC1uiiXOQ8ABMxTxezbQ5wjrfAAAgI'
    danger = 12
    loot = [('old_bone', (1, 100))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller, fight=fight, unit_dict=unit_dict)
        self.max_wounds = 15
        self.wounds = 15
        self.bone_dict = {'head': True, 'legs': True, 'arms': True}
        self.weapon = random.choice([weapons.Knife, weapons.Bow])(self)
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapons = []
        self.crawl_action = self.create_action('crawl', self.crawl, 'button_1', order=10)
        self.crawl_back_action = self.create_action('crawl-back', self.crawl_back, 'button_2', order=10)
        self.default_weapon = weapons.Teeth(self)
        self.crawling = False
        self.energy = 5
        self.recovery_energy = 5
        self.toughness = 5
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def to_dict(self):
        unit_dict = {
            'name': self.name,
            'unit_name': self.unit_name,
            'max_wounds': self.max_wounds,
            'wounds': self.wounds,
            'bone_dict': self.bone_dict,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'items': [item.to_dict() for item in self.items],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict(),
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]).base_dict
        }
        return unit_dict

    def recovery(self):
        self.energy = 5
        self.weapon.recovery()

    def lose_round(self):
        pass

    def shatter(self):
        broken = False
        while len([key for key in self.bone_dict.keys() if self.bone_dict[key]]) > int(self.max_wounds/(self.max_wounds -
                                                                                                         self.wounds + 1)):
            broken = random.choice([key for key in self.bone_dict.keys() if self.bone_dict[key]])
            self.bone_dict[broken] = False
            self.string(self.broken_dict[broken], format_dict={'actor': self.name})
            if broken == 'arms':
                if self.bone_dict['head']:
                    self.default_weapon = weapons.Teeth(self)
                    self.weapon = weapons.Teeth(self)
                else:
                    self.default_weapon = weapons.Fist(self)
                    self.weapon = weapons.Fist(self)
            elif broken == 'head':
                self.melee_accuracy -= 3
                if not self.bone_dict['arms']:
                    self.default_weapon = weapons.Fist(self)
                    self.weapon = weapons.Fist(self)
            broken = True
        if broken:
            return True
        # В ином случае
        self.string('skill_8', format_dict={'actor': self.name})

    def dies(self):
        self.wounds -= self.dmg_received
        if self.wounds <= 0 and self not in self.fight.dead:
            self.string('died_message', format_dict={'actor': self.name})
            return True
        elif self.dmg_received:
            self.shatter()
            return False

    def alive(self):
        if self.wounds > 0:
            return True
        else:
            return False

    def crawl(self, action):
        if not action.unit.crawling:
            action.unit.crawling = True
            action.unit.string('skill_4', format_dict={'actor': action.unit.name})
        else:
            action.unit.crawling = False
            action.unit.string('skill_5', format_dict={'actor': action.unit.name})
            for actor in action.unit.targets():
                if actor not in action.unit.melee_targets:
                    actor.melee_targets.append(action.unit)
                    action.unit.melee_targets.append(actor)

    def crawl_back(self, action):
        action.unit.string('skill_6', format_dict={'actor': action.unit.name})
        action.unit.disabled.append('backing')
        statuses.CustomStatus(action.unit, 1, 1, action.unit.be_back)

    def be_back(self):
        self.string('skill_7', format_dict={'actor': self.name})
        self.disabled.remove('backing')
        for unit in self.targets():
            if self in unit.melee_targets:
                unit.melee_targets.remove(self)
        self.melee_targets = []

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        if ['firearm'] not in self.weapon.types:
            self.energy = 5
        if self.energy < 0:
            self.energy = 0

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'bones': self.wounds,
                                      'head': emote_dict['check_em' if self.bone_dict['head'] else 'cross_em'],
                                      'arm': emote_dict['check_em' if self.bone_dict['arms'] else 'cross_em'],
                                      'leg': emote_dict['check_em' if self.bone_dict['legs'] else 'cross_em'],
                                      'weapon': LangTuple('weapon_' + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def crawl_available(self):
        if self.melee_targets or not self.weapon.melee:
            return False
        return True

    def available_actions(self):
        actions = [(1, WeaponButton(self, self.weapon)),
                   (1, MoveForward(self) if self.bone_dict['legs']
                   else self.action_button('crawl', 'button_1', self.crawl_available)),
                   (3, AdditionalKeyboard(self))]
        return actions

    def additional_actions(self):
        actions = [(1, MoveBack(self) if self.bone_dict['legs']
                   else self.action_button('crawl-back', 'button_2', True))]
        return actions


class Lich(Skeleton):
    unit_name = 'lich'
    control_class = ai.LichAi
    types = ['undead', 'boss']
    blood_spell_img = 'AgADAgADeaoxG8zb0EsDfcIlLz_K6IyROQ8ABDkUYT5md9D4O2MBAAEC'
    greet_msg = 'текст-лича'
    image = 'AgADAgADaaoxG8zb0Eus0hQfCdFJd0eXOQ8ABF-FiJZxVRuJTV0BAAEC'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        complexity = 30 if complexity is None else complexity
        Skeleton.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.max_wounds = complexity
        self.wounds = complexity
        self.weapon = weapons.Claws(self)
        self.default_weapon = weapons.Teeth(self)
        self.blood_touch_action = self.create_action('blood_touch', self.blood_touch, 'button_1', order=5)
        self.chain_action = self.create_action('chain', self.chain, 'button_2', order=5)
        self.check_blood_action = self.create_action('check_blood', self.check_blood, 'button_3', order=20)
        self.summon_skeleton_action = self.create_action('summon_skeleton', self.summon_skeleton, 'button', order=11)
        self.chains = False
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def shatter(self):
        self.string('skill_8', format_dict={'actor': self.name})

    def blood_touch(self, action):
        unit = action.unit
        target = unit.target
        statuses.Bleeding(target)
        unit.string('skill_1', format_dict={'actor': unit.name, 'target': target.name})

    def chain(self, action):
        unit = action.unit
        target = unit.target
        unit.chains = True
        unit.string('skill_2', format_dict={'actor': unit.name, 'target': target.name})

        class Chains(Tech):
            unit_name = 'lich_chains'

            def __init__(chains, name=None, controller=None, fight=None, unit_dict=None, target=None):
                Unit.__init__(chains, name=name, controller=controller, fight=fight, unit_dict=unit_dict)
                chains.wounds = 1
                chains.evasion = -5
                chains.chained = target
                chains.chained.disabled.append(chains.unit_name)

            def dies(chains):
                chains.wounds -= chains.dmg_received
                if chains.wounds <= 0 and chains not in chains.fight.dead:
                    chains.string('died_message', format_dict={'actor': chains.name})
                    chains.chained.disabled.remove(chains.unit_name)
                    unit.chains = False
                    return True

            def alive(chains):
                if chains.wounds > 0:
                    return True
                return False
        chain_unit = unit.summon_unit(Chains, target=target)
        chain_unit.move_forward()

    def check_blood(self, action):
        unit = action.unit
        triggered = False
        for target in unit.targets():
            if any(actn.name == 'bleeding' for actn in target.actions()) and 'bleeding' in target.statuses:
                if target.statuses['bleeding'].strength >= 9:
                    triggered = True
                    break
                elif target.statuses['bleeding'].strength > 6 and 'idle' not in target.action:
                    triggered = True
                    break
        if triggered:
            unit.announce(unit.to_string('skill_5', format_dict={'actor': unit.name}), image=unit.blood_spell_img)
            standart_actions.Custom(unit.string, 'skill_3', unit=unit, order=22, format_dict={'actor': unit.name})
            for target in unit.targets():
                statuses.Bleeding(target)

    def summon_skeleton(self, action):
        unit = action.unit
        unit.summon_unit(Skeleton)
        unit.string('skill_4', format_dict={'actor': unit.name})


class Zombie(Unit):
    unit_name = 'zombie'
    types = ['zombie', 'alive']
    emote = emote_dict['zombie_em']
    control_class = ai.ZombieAi
    greet_msg = 'текст-зомби'
    image = 'AgADAgADqqoxG8_E6Uu_il72AlGXdRuiOQ8ABHWprqpYxXCGvpYBAAEC'
    danger = 10
    loot = [('zombie_tooth', (1, 100))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 3
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 4
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapon = weapons.PoisonedFangs(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]),
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        return unit_dict

    def recovery(self):
        self.energy = 5
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        if ['firearm'] not in self.weapon.types:
            self.energy = 5
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness


class Ghoul(Zombie):
    unit_name = 'zombie'
    types = ['zombie', 'alive']
    emote = emote_dict['zombie_em']
    control_class = ai.ZombieAi

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 3
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 4
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.weapon = weapons.PoisonedFangs(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': [*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        return unit_dict

    def recovery(self):
        self.energy = 5
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        if ['firearm'] not in self.weapon.types:
            self.energy = 5
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness


class Basilisk(Unit):
    unit_name = 'basilisk'
    types = ['animal', 'alive']
    emote = emote_dict['basilisk_em']
    control_class = ai.BasiliskAi

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 5
        self.hp = self.max_hp
        self.max_energy = 6
        self.recovery_energy = 0
        self.toughness = 6
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 2
        self.weapon = weapons.PoisonedBloodyFangs(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy

        self.stun_action = self.create_action('basilisk-stun', self.stun, 'button_1', order=5)
        self.rush_action = self.create_action('basilisk-rush', self.rush, 'button_2', order=10)
        self.recovery_action = self.create_action('basilisk-recovery', self.rest, 'button_3', order=5)
        self.hurt = False
        self.stun_ready = False

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'melee_accuracy': self.melee_accuracy,
            'recovery_energy': self.recovery_energy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': [*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        return unit_dict

    def rest(self, action):
        unit = action.unit
        if unit.recovery_energy:
            unit.energy += unit.recovery_energy
        else:
            unit.energy = unit.max_energy
        unit.weapon.recovery()
        unit.change_hp(1)
        unit.hurt = False
        unit.stun_ready = True
        unit.string('skill_1', format_dict={'actor': action.unit.name})

    def rush(self, action):
        unit = action.unit
        for target in unit.targets():
            if target not in unit.melee_targets:
                unit.melee_targets.append(target)
                target.melee_targets.append(unit)
        statuses.Buff(unit, 'damage', 1, 1)
        unit.string('skill_2', format_dict={'actor': action.unit.name})

    def stun(self, action):
        unit = action.unit
        names = []
        unit.stun_ready = False
        for target in unit.melee_targets:
            statuses.Stun(target)
            target.receive_damage(3)
            names.append(target.name)
        if names:
            unit.string('skill_3', format_dict={'actor': unit.name, 'targets': ' ,'.join(names)})
        else:
            unit.string('skill_4', format_dict={'actor': unit.name})

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness
            self.hurt = True

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        self.hurt = False
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy


class Goblin(StandartCreature):
    greet_msg = 'текст-гоблина'
    image = 'AgADAgADqqoxG8_E6Uu_il72AlGXdRuiOQ8ABHWprqpYxXCGvpYBAAEC'
    unit_name = 'goblin'
    control_class = ai.GoblinAi
    emote = emote_dict['skeleton_em']
    loot = [('goblin_ear', (1, 100)), ('goblin_ear', (1, 50))]

    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 3
        self.abilities = [abilities.WeaponSnatcher(self), abilities.Dodge(self)]
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy
        self.loot_chances['weapon'] = 100


class Worm(Unit):
    greet_msg = 'текст-червей'
    image = 'AgADAgADCaoxG5L9kUuNAAHxLjBBsf8cQ_MOAAR12ygrBhqdi80aAwABAg'
    unit_name = 'worm'
    types = ['brainless', 'alive']
    emote = emote_dict['worm_em']
    control_class = ai.WormAi
    danger = 7
    loot = [('worm_skin', (1, 100))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        Unit.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.feared = False
        # Максимальные параметры
        if unit_dict is None:
            self.max_hp = 3
            self.hp = self.max_hp
            self.max_energy = 5
            self.recovery_energy = 5
            self.toughness = 4
            self.melee_accuracy = 0
            self.range_accuracy = 0
            self.evasion = 0
            self.damage = 0
        else:
            self.max_hp = unit_dict['max_hp']
            self.hp = unit_dict['hp']
            self.max_energy = unit_dict['max_energy']
            self.recovery_energy = unit_dict['recovery_energy']
            self.toughness = unit_dict['toughness']
            self.melee_accuracy = unit_dict['melee_accuracy']
            self.range_accuracy = unit_dict['range_accuracy']
            self.evasion = unit_dict['evasion']
            self.damage = unit_dict['damage']
        # Снаряжение
        if unit_dict is None:
            self.weapon = weapons.Teeth(self)
            self.weapons = []
            self.abilities = [abilities.Cannibal(self), abilities.CorpseEater(self)]
            self.items = []
            self.armor = []
            self.inventory = []
        else:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy
        self.crawl_action = self.create_action('worm-crawl-forward', self.crawl, 'button_1', order=10)
        self.crawl_back_action = self.create_action('worm-crawl-back', self.crawl_back, 'button_2', order=1)

    def to_dict(self):
        unit_dict = {
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'melee_accuracy': self.melee_accuracy,
            'recovery_energy': self.recovery_energy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]).base_dict,
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict()
        }
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        return unit_dict

    def crawl(self, action):
        action.unit.string('skill_1', format_dict={'actor': action.unit.name})
        for actor in action.unit.targets():
            if actor not in action.unit.melee_targets:
                actor.melee_targets.append(action.unit)
                action.unit.melee_targets.append(actor)

    def crawl_back(self, action):
        action.unit.string('skill_2', format_dict={'actor': action.unit.name})
        for actor in action.unit.targets():
            if action.unit in actor.melee_targets:
                actor.melee_targets.remove(action.unit)
        action.unit.feared = False
        action.unit.melee_targets = []

    def recovery(self):
        if self.recovery_energy:
            self.energy += self.recovery_energy
        else:
            self.energy = self.max_energy
        self.weapon.recovery()

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        return LangTuple('unit_' + self.unit_name, 'player_menu',
                         format_dict={'actor': self.name, 'hp': self.hp,
                                      'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                 + self.weapon.name, 'name'),
                                      'statuses': self.get_status_string()})

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            self.hp_delta -= 1 + self.dmg_received // self.toughness
            if len([unit for unit in self.team.units if unit.alive()]) > 1:
                self.feared = True


# Мобы Артема

class Shadow(StandartCreature):
    unit_name = 'shadow'
    control_class = ai.StandartMeleeAi
    emote = emote_dict['skeleton_em']

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 3
        self.evasion = 1
        self.abilities = [abilities.WeaponSnatcher(self), abilities.Dodge(self)]
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy


class Snail(StandartCreature):
    unit_name = 'snail'
    control_class = ai.SnailAi
    emote = emote_dict['skeleton_em']

    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, summoned=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        summoned = 0 if summoned is None else summoned
        self.max_hp -= summoned*2
        if self.max_hp < 1:
            self.max_hp = 1
        self.hp = self.max_hp
        self.add_energy(-summoned)
        self.default_weapon = 'teeth'
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy
        self.split_check_action = self.create_action('split_check', self.split_check, 'button_3', order=59)
        self.crawl_action = self.create_action('worm-crawl-forward', self.crawl, 'button_1', order=10)

    def crawl(self, action):
        action.unit.string('skill_1', format_dict={'actor': action.unit.name})
        for actor in action.unit.targets():
            if actor not in action.unit.melee_targets:
                actor.melee_targets.append(action.unit)
                action.unit.melee_targets.append(actor)

    def split_check(self, action):
        print('check')
        unit = action.unit
        if unit.hp <= 0 and unit.max_hp > 1:
            unit.split(action)

    def split(self, action):
        unit = action.unit
        unit.summon_unit(Snail, summoned=unit.summoned+1)
        unit.summon_unit(Snail, summoned=unit.summoned+1)
        unit.string('skill_2', format_dict={'actor': unit.name})

    def dies(self):
        if not self.alive() and self not in self.fight.dead:
            return True
        return False


# Мобы Пасюка

class SperMonster(StandartCreature):
    unit_name = 'spermonster'
    control_class = ai.SperMonsterAi
    emote = emote_dict['spermonster_em']

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.max_hp = 5
        self.hp = self.max_hp
        self.toughness = 4
        self.triggered = False
        self.default_weapon = 'cock'
        self.weapon = weapons.Cock(self)
        self.abilities = [abilities.Spermonster(self)]
        self.sperm_check_action = self.create_action('sperm_check', self.sperm_check, 'button_3', order=59)

    def sperm_check(self, action):
        unit = action.unit
        if not unit.triggered and unit.hp <= 1:
            unit.triggered = True
            unit.sperm_shower(action)

    def sperm_shower(self, action):
        unit = action.unit
        target = random.choice(unit.targets())
        unit.string('skill_1', format_dict={'actor': unit.name, 'target': target.name})
        statuses.Stun(target)


class PedoBear(StandartCreature):
    unit_name = 'pedobear'
    control_class = ai.PedoBearAi
    emote = emote_dict['pedobear_em']

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.find_target_action = self.create_action('find_target', self.find_target, 'button_3', order=5)
        self.hug_action = self.create_action('hug', self.hug, 'button_3', order=10)
        self.locked_in = None
        self.max_hp = 6
        self.hp = self.max_hp

    def find_target(self, action):
        unit = action.unit
        targets = unit.weapon.targets()
        target = random.choice(targets)
        unit.string('skill_1', format_dict={'actor': unit.name, 'target': unit.target.name})
        unit.locked_in = target

    def hug(self, action):
        unit = action.unit
        if 'dodge' not in unit.target.action and 'move' not in unit.target.action:
            unit.damage += 1
            unit.target.receive_damage(unit.damage)
            unit.string('skill_2', format_dict={'actor': unit.name, 'target': unit.target.name, 'damage': unit.damage})
            unit.string('skill_4', format_dict={'actor': unit.name}, order=23)
            unit.locked_in = None
        else:
            unit.string('skill_3', format_dict={'actor': unit.name, 'target': unit.target.name})
            unit.locked_in = None


# Мобы Асгард

class BirdRukh(StandartCreature):
    unit_name = 'bird_rukh'
    control_class = ai.BirdRukhAi

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.fly_action = self.create_action('bird_fly', self.fly, 'button_1', order=10)
        self.stun_action = self.create_action('bird_stun', self.stun, 'button_2', order=10)
        self.weapon = weapons.RukhBeak(self)

    def stun(self, action):
        unit = action.unit
        targets = unit.targets()
        unit.string('skill_2', format_dict={'actor': unit.name})
        for target in targets:
            if 'dodge' not in target.action:
                statuses.Stun(target)
                target.receive_damage(3)

    def fly(self, action):
        unit = action.unit
        unit.move_forward()
        unit.string('skill_1', format_dict={'actor': unit.name})


class Bear(StandartCreature):
    unit_name = 'bear'
    control_class = ai.BearAi

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.destroy_action = self.create_action('destroy', self.destroy, 'button_1', order=10)
        self.weapon = weapons.BearClaw(self)

    def destroy(self, action):
        unit = action.unit
        unit.damage += 3
        attack = standart_actions.BaseAttack(unit=unit, fight=unit.fight)
        attack.activate()
        unit.damage -= 3
        unit.string('skill_1', format_dict={'actor': unit.name, 'target': unit.target.name, 'damage': attack.dmg_done})

# Тут Пасюк учится кодить под либу Игоря
        
class Pasyuk(StandartCreature):
    unit_name = 'pasyuk'
    control_class = ai.StandartMeleeAi
    
    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandartCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.weapon = weapons.Knife(self)
        

# Конец кода Пасюка      

units_dict = {Human.unit_name: Human,
              Skeleton.unit_name: Skeleton,
              Unit.unit_name: Unit,
              Zombie.unit_name: Zombie,
              Goblin.unit_name: Goblin,
              Worm.unit_name: Worm,
              Basilisk.unit_name: Basilisk,
              Lich.unit_name: Lich,
              Shadow.unit_name: Shadow,
              Snail.unit_name: Snail,
              Bear.unit_name: Bear,
              PedoBear.unit_name: PedoBear,
              BirdRukh.unit_name: BirdRukh,
              SperMonster.unit_name: SperMonster,
              Pasyuk.unit_name: Pasyuk}
