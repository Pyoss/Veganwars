from locales.emoji_utils import emote_dict
from fight.units import Unit, units_dict
from fight.ai import Ai, get_lowest_hp
from fight.standart_actions import *
import engine
from bot_utils.keyboards import *
from fight import abilities, weapons
from locales.localization import LangTuple
import random


class WormAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_hp(self.unit.weapon.targets())
            if engine.roll_chance(20):
                self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        allies = self.unit.get_allies()
        allies.remove(self.unit)
        self.clear_actions()
        self.find_target()
        self.attack(self.unit.energy if self.unit.target is not None and not self.unit.feared else 0)
        self.add_action(self.unit.crawl_action, 1 if not self.unit.weapon.targets() else 0)
        self.add_action(self.unit.crawl_back_action, 1 if self.unit.feared and self.unit.weapon.targets() else 0)
        if not self.unit.weapon.targets() and allies:
            self.add_action(Ability, self.unit.max_hp - self.unit.hp, info=['fgt', str(self.fight), str(self.unit),
                                                          'ability', 'cannibal',
                                                                            str(get_lowest_hp(allies))])
        if any(v for k, v in self.unit.fight.dead.items()):
            self.add_action(Ability, 10, info=['fgt', str(self.fight), str(self.unit),
                                                                        'ability', 'corpse-eater',
                                                                        str(random.choice([k for k, v in self.unit.fight.dead.items()
                                                                                           if self.unit.fight.dead[k]]))])
        self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)


class Worm(Unit):
    greet_msg = 'текст-червей'
    unit_name = 'worm'
    types = ['brainless', 'alive']
    emote = emote_dict['worm_em']
    control_class = WormAi
    danger = 8
    default_loot = [('worm_skin', (1, 100))]
    image = './files/images/units/worm.png'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
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
        self.energy = int(self.max_energy / 2 + 1)
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

units_dict[Worm.unit_name] = Worm
