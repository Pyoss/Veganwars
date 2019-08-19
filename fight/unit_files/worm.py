from locales.emoji_utils import emote_dict
from fight.units import Unit, units_dict, StandardCreature
from fight.ai import Ai, get_lowest_hp, StandardMeleeAi
from fight.standart_actions import *
import engine
from bot_utils.keyboards import *
from fight import abilities, weapons
from locales.localization import LangTuple
import random


class WormAi(StandardMeleeAi):

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
        if StandardMeleeAi.nessesary_actions(self):
            return
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


class Worm(StandardCreature):
    greet_msg = 'текст-червей'
    unit_name = 'worm'
    types = ['brainless', 'alive']
    emote = emote_dict['worm_em']
    control_class = WormAi
    danger = 8
    default_loot = [('worm_skin', (1, 100))]
    image = './files/images/units/worm.png'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.feared = False
        # Максимальные параметры
        self.max_hp = 3
        self.hp = self.max_hp
        self.max_energy = 5
        self.toughness = 4
        self.weapon = weapons.Fangs(self)
        self.default_weapon = 'fangs'
        self.abilities = [abilities.Cannibal(self), abilities.CorpseEater(self)]
        self.energy = int(self.max_energy / 2 + 1)
        self.crawl_action = self.create_action('worm-crawl-forward', self.crawl, 'button_1', order=10)
        self.crawl_back_action = self.create_action('worm-crawl-back', self.crawl_back, 'button_2', order=1)

        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

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
