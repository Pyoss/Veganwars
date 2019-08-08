from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict, Tech
from fight.ai import Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from fight import weapons, statuses
from locales.localization import LangTuple
from PIL import Image
import random


class DragonAi(Ai):

    def find_target(self):
        if self.unit.melee_targets:
            self.unit.target = random.choice(self.unit.melee_targets)

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.breathing:
            self.action_ability('fire_breath', 8)
            return
        if len(self.unit.melee_targets) > 0:
            self.action_ability('wing_clap', self.unit.energy*len(self.unit.melee_targets))
        else:
            self.action_ability('tare_air', 5)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        if self.unit.target and self.unit.energy > 3:
            self.make_action(Attack, )


class Dragon(StandardCreature):
    unit_name = 'dragon'
    control_class = DragonAi
    emote = emote_dict['dragon_em']
    types = ['dragon']
    image = './files/images/units/dragon.jpg'
    danger = 20
    default_loot = [('living_branch', (1, 90))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandardCreature.__init__(self, name, controller, fight=fight, unit_dict=unit_dict)
        self.max_hp = 7
        self.hp = 7
        self.energy = 9
        self.max_energy = 9
        self.tail = weapons.DragonTail(self)
        self.weapon = weapons.Claws(self)
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.weapons = []
        self.breathing = False
        self.new_ability(ability_name='fire_breath', ability_func=self.fire_breath,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'),
                         cooldown=3)
        self.new_ability(ability_name='wing_clap', ability_func=self.wing_clap,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'),
                         cooldown=3)
        self.new_ability(ability_name='take_air', ability_func=self.take_air,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))
        self.new_ability(ability_name='tale_whip', ability_func=self.tail_whip,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def get_image(self):
        if self.weapon.name == 'bow':
            image = 'D:\YandexDisk\Veganwars\Veganwars\\files\images\\units\skeleton_archer.png'
        else:
            image = self.image
        return Image.open(image), 'standard', (0, 0)

    def recovery(self):
        speed = self.get_speed() if self.get_speed() > 2 and 'exhausted' not in self.statuses else 2
        recovery_speed = speed if speed < self.max_energy else self.max_energy

        self.energy += recovery_speed
        self.weapon.recovery()
        return recovery_speed

    def recovery_speed(self):
        speed = self.get_speed() if self.get_speed() > 2 and 'exhausted' not in self.statuses else 2
        recovery_speed = speed if speed < self.max_energy else self.max_energy
        return recovery_speed

    @staticmethod
    def fire_breath(ability, action):
        unit = action.unit
        damage = random.randint(8, 10)
        for target in unit.targets():
            statuses.Burning(target, stacks=damage)
        unit.string('skill_1', format_dict={'actor': unit.name})

    @staticmethod
    def wing_clap(ability, action):
        unit = action.unit
        targets = unit.melee_targets
        for target in targets:
            target.move_back()
            statuses.Prone(target)
        unit.string('skill_2', format_dict={'actor': unit.name})

    @staticmethod
    def tail_whip(ability, action):
        unit = action.unit
        unit.controller.find_target()
        target = random.choice(unit.targets())
        x = Attack(unit, unit.fight)
        x.activate(target=target, weapon=unit.tail)

    @staticmethod
    def take_air(ability, action):
        unit = action.unit
        unit.string('skill_3', format_dict={'actor': unit.name})


units_dict[Dragon.unit_name] = Dragon
