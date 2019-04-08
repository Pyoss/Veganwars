from locales.emoji_utils import emote_dict
from fight.units import Unit, units_dict
from fight.ai import Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from fight import weapons
from locales.localization import LangTuple
import random


class ZombieAi(Ai):
    ai_name = 'zombie'

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)


class Zombie(Unit):
    unit_name = 'zombie'
    types = ['zombie', 'alive']
    emote = emote_dict['zombie_em']
    control_class = ZombieAi
    greet_msg = 'текст-зомби'
    danger = 10
    loot = [('zombie_tooth', (1, 100))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
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
units_dict[Zombie.unit_name] = Zombie
