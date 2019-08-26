from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict, Tech
from fight.ai import Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from fight import weapons, statuses, armors
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
        if self.unit.breathing + 1 == self.fight.turn:
            self.action_ability('fire_breath', 8)
            self.unit.breathing = 0
            return
        if len(self.unit.melee_targets) > 0 and not self.unit.acted:
            self.action_ability('wing_clap', self.unit.energy*len(self.unit.melee_targets))
        elif self.unit.breathing != self.fight.turn:
            self.action_ability('take_air', self.unit.energy)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.action_ability('tail_whip', self.unit.energy)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)

    def get_action(self, edit=False):
        action = Ai.get_action(self, edit=edit)
        self.unit.acted = True
        if action.name == 'ability':
            if action.ability.name == 'wing_clap':
                return
            if action.ability.name == 'take_air':
                self.unit.breathing = self.fight.turn
        if self.unit.energy > 2 and self.unit.hp < self.unit.max_hp/2:
            Ai.get_action(self, edit=edit)
            if action.name == 'ability':
                if action.ability.name == 'take_air':
                    self.unit.breathing = self.fight.turn


class Dragon(StandardCreature):
    unit_name = 'dragon'
    control_class = DragonAi
    emote = emote_dict['dragon_em']
    types = ['alive', 'massive']
    image = './files/images/units/sword_goblin.png'
    danger = 20
    body_height = 'standard'
    default_loot = [('living_branch', (1, 90))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller, fight=fight, unit_dict=unit_dict)
        self.max_hp = 7
        self.hp = 7
        self.energy = 9
        self.max_energy = 9
        self.damage = 2
        self.toughness = 8
        self.tail = weapons.DragonTail(self)
        self.weapon = weapons.BearClaw(self)
        self.default_weapon = weapons.BearClaw(self)
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.weapons = []
        self.armor = [armors.DragonHide(self)]
        self.breathing = -1
        self.acted = False
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
                         name_tuple=self.to_string('button_1'), ability_order=10)
        self.new_ability(ability_name='tail_whip', ability_func=self.tail_whip,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def recovery(self):
        self.acted = False
        return StandardCreature.recovery(self)

    def get_image(self):
        if self.weapon.name == 'knife':
            image = random.choice(('./files/images/units/knife_goblin.png',))
        elif self.weapon.name == 'harpoon':
            image = './files/images/units/harpoon_goblin.png'
        else:
            image = './files/images/units/fist_goblin.png'
        return Image.open(image), self.body_height, (0, 0)

    def recovery_speed(self):
        speed = self.get_speed() if self.get_speed() > 2 and 'exhausted' not in self.statuses else 2
        recovery_speed = speed if speed < self.max_energy else self.max_energy
        return recovery_speed

    @staticmethod
    def fire_breath(ability, action):
        unit = action.unit
        unit.waste_energy(2)
        damage = random.randint(8, 10)
        target = random.choice(unit.targets())
        if 'dodge' in target.action:
            unit.string('skill_4', format_dict={'actor': unit.name, 'target': target.name})
        else:
            unit.string('skill_1', format_dict={'actor': unit.name, 'target': target.name})
            if 'shield' not in target.action:
                statuses.Burning(target, stacks=damage)

    @staticmethod
    def wing_clap(ability, action):
        unit = action.unit
        unit.waste_energy(2)
        targets = unit.melee_targets
        for target in targets:
            target.move_back()
            statuses.Prone(target)
        unit.string('skill_2', format_dict={'actor': unit.name})

    @staticmethod
    def tail_whip(ability, action):
        unit = action.unit
        unit.waste_energy(2)
        unit.controller.find_target()
        target = random.choice(unit.targets())
        x = Attack(unit, unit.fight)
        x.activate(target=target, weapon=unit.tail)

    @staticmethod
    def take_air(ability, action):
        unit = action.unit
        unit.string('skill_3', format_dict={'actor': unit.name})


units_dict[Dragon.unit_name] = Dragon
