from locales.emoji_utils import emote_dict
from fight.units import Unit, units_dict, Tech
from fight.ai import Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from fight import weapons, statuses
from locales.localization import LangTuple
from PIL import Image
import random


class RedOakAi(Ai):

    def find_target(self):
        if self.unit.melee_targets:
            self.unit.target = random.choice(self.unit.melee_targets)

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if not self.unit.branch_spawned:
            self.action_ability('spawn_grabber_branch', 8)
        if len(self.unit.melee_targets) > 0:
            self.action_ability('attack_everyone', self.unit.energy*len(self.unit.melee_targets))
        else:
            self.action_ability('throw_ancor', 5)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class GrabberBranchAi(Ai):

    def find_target(self):
        if self.unit.victim is None:
            self.unit.target = random.choice(self.unit.targets())
            self.unit.victim = self.unit.target
        else:
            self.unit.target = self.unit.victim

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.action_ability('tighten', 10)


class RedOak(Unit):
    unit_name = 'red_oak'
    control_class = RedOakAi
    emote = emote_dict['red_oak_em']
    types = ['tree']
    image = './files/images/units/red_oak.jpg'
    danger = 20
    default_loot = [('living_branch', (1, 90))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        Unit.__init__(self, name, controller, fight=fight, unit_dict=unit_dict)
        self.max_wounds = 25
        self.wounds = 25
        self.weapon = weapons.RedOakBranch(self)
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = -2
        self.damage = 0
        self.weapons = []
        self.ancor = weapons.RedOakAncor(self)
        self.new_ability(ability_name='spawn_grabber_branch', ability_func=self.spawn_grabber_branch,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'),
                         cooldown=2)
        self.new_ability(ability_name='attack_everyone', ability_func=self.attack_everyone,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))
        self.new_ability(ability_name='throw_ancor', ability_func=self.throw_ancor,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))
        self.energy = 7
        self.max_energy = 7
        self.branches = []
        self.branch_spawned = False
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def get_image(self):
        if self.weapon.name == 'bow':
            image = 'D:\YandexDisk\Veganwars\Veganwars\\files\images\\units\skeleton_archer.png'
        else:
            image = self.image
        return Image.open(image), 'standard', (0, 0)

    def to_dict(self):
        unit_dict = {
            'name': self.name,
            'unit_name': self.unit_name,
            'max_wounds': self.max_wounds,
            'wounds': self.wounds,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'evasion': self.evasion,
            'damage': self.damage,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'items': [item.to_dict() for item in self.items],
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon.to_dict(),
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]).base_dict,
            'statuses': [status.to_dict() for status in list(self.statuses.values()) if status.to_dict() is not False]
        }
        return unit_dict

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

    def rest(self):
        self.recovery()
        self.string('skill_5', format_dict={'actor': self.name, 'energy': self.recovery_speed()})

    def lose_round(self):
        pass

    def dies(self):
        self.wounds -= self.dmg_received
        if self.wounds <= 0 and self not in self.fight.dead:
            self.string('died_message', format_dict={'actor': self.name})
            for branch in self.branches:
                branch.wounds = 0
                branch.dies()
            return True
        elif self.dmg_received:
            self.string('skill_6', format_dict={'actor': self.name})
        return False

    def alive(self):
        if self.wounds > 0:
            return True
        else:
            return False

    @staticmethod
    def spawn_grabber_branch(ability, action):
        unit = action.unit
        unit.branch_spawned = True
        target = random.choice(unit.targets())

        branch_unit = unit.summon_unit(GrabberBranch, owner=unit)
        branch_unit.string('skill_7', format_dict={'actor': branch_unit.name, 'target': target.name})
        branch_unit.move_forward()
        branch_unit.victim = target

        unit.branches.append(branch_unit)

    @staticmethod
    def throw_ancor(ability, action):
        unit = action.unit
        unit.controller.find_target()
        target = random.choice(unit.targets())
        x = Attack(unit, unit.fight)
        x.activate(target=target, weapon=unit.ancor)

    @staticmethod
    def attack_everyone(ability, action):
        unit = action.unit
        unit.string('skill_3', format_dict={'actor': unit.name})
        for target in unit.melee_targets:
            x = Attack(unit, unit.fight)
            x.activate(target=target)

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        if self.energy < 0:
            self.energy = 0


class GrabberBranch(Tech):
        unit_name = 'grabber_branch'
        control_class = GrabberBranchAi
        emote = emote_dict['red_oak_em']
        types = ['tree']

        def __init__(self, name=None, controller=None, fight=None, unit_dict=None, owner=None):
            Unit.__init__(self, name=name, controller=controller, fight=fight, unit_dict=unit_dict)
            self.owner = owner
            self.wounds = 10
            self.evasion = 0
            self.state = 'reach'
            self.weapon = weapons.Knife(self)
            self.victim = None
            self.new_ability(ability_name='tighten', ability_func=self.tighten,
                             ability_type='instant',
                             name_tuple=self.to_string('button_1'))

        def dies(self):
            self.wounds -= self.dmg_received
            if self.wounds <= 0 and self not in self.fight.dead:
                print(self.name)
                if self.state == 'lift':
                    self.string('died_message_1', format_dict={'actor': self.name, 'target': self.victim.name})
                    statuses.Prone(self.victim)
                else:
                    self.string('died_message', format_dict={'actor': self.name})
                self.release()
                self.owner.branch_spawned = False
                return True
            elif self.dmg_received:
                self.string('fire_out', format_dict={'actor': self.name})
            return False

        def grab(self, target):
            if 'dodge' in target.action or 'back' in target.action:
                self.string('skill_8', format_dict={'actor': self.name,
                                                    'target': target.name})

            else:
                self.string('skill_1', format_dict={'actor': self.name,
                                                    'target': target.name})
                statuses.CustomStatus(target, 21, 70, self.tighten,
                                      name='branch-grabbed',
                                      additional_buttons_actions=[('free', self.force_free,
                                                                   LangTuple('unit_' + self.unit_name, 'button_1'))])
                self.move_forward()
                target.rooted.append(self)
                self.state = 'grabbed'

        def pull(self):
            self.string('skill_2', format_dict={'actor': self.name,
                                                'target': self.target.name})

            units_to_melee = [unit for unit in self.victim.targets() if 'forward' in unit.action]
            if not units_to_melee:
                units_to_melee = self.victim.targets()
            for unit in units_to_melee:
                if unit not in self.victim.melee_targets:
                    unit.melee_targets.append(self.victim)
                    self.victim.melee_targets.append(unit)

        def fling(self):
            damage = 3
            self.target.receive_damage(damage)
            self.target.move_back()
            self.string('skill_10', format_dict={'actor': self.name,
                                                'target': self.target.name,
                                                 'damage': damage})
            statuses.Prone(self.victim)
            self.free()

        def choke(self):
            if self.target.alive():
                damage = 2
                self.target.receive_damage(damage)
                self.string('skill_9', format_dict={'actor': self.name,
                                                    'target': self.target.name,
                                                    'damage': damage})
            else:
                self.fling()

        @staticmethod
        def tighten(ability, action):
            unit = action.unit
            if unit.state == 'reach':
                unit.grab(unit.target)
                unit.victim = unit.target
            elif unit.state == 'grabbed':
                chance = random.randint(1, 3)
                if chance == 1:
                    unit.pull()
                    unit.state = 'pull'
                elif chance == 2:
                    unit.fling()
                    unit.state = 'free'
                elif chance == 3:
                    unit.choke()
                    unit.state = 'choking'
            elif unit.state == 'choking':
                    unit.choke()
            elif unit.state == 'pull':
                unit.string('skill_3', format_dict={'actor': unit.name,
                                                    'target': unit.target.name})
                statuses.Buff(unit.victim, 'range_accuracy', -5, 2)
                statuses.Buff(unit.victim, 'melee_accuracy', -3, 2)
                unit.state = 'lift'
            elif unit.state == 'lift':
                unit.string('skill_4', format_dict={'actor': unit.name, 'target': unit.target.name})
                unit.state = 'free'
                unit.target.statuses['branch-grabbed'].finish()
                unit.target.change_hp(-10)
            elif unit.state == 'free':
                unit.string('skill_7', format_dict={'actor': unit.name, 'target': unit.target.name})
                unit.move_forward()
                unit.state = 'reach'
            elif unit.state == 'broken':
                unit.state = 'free'

        def free(self):
            self.release()
            if self.state == 'lift':
                self.string('skill_6', format_dict={'actor': self.name, 'target': self.target.name})
                statuses.Prone(self.victim)
            self.victim = None
            self.controller.find_target()

        def release(self):
            if self.victim is not None and self.victim.alive():
                if 'branch-grabbed' in self.victim.statuses:
                    self.victim.statuses['branch-grabbed'].finish()
                    self.victim.rooted.remove(self)

        def force_free(self):
            if self.victim.energy > self.wounds:
                if self.state != 'lift':
                    self.string('skill_5', format_dict={'actor': self.name, 'target': self.target.name})
                self.free()
                self.state = 'broken'
            else:
                self.string('button_2', format_dict={'target': self.victim.name})

        def alive(self):
            if self.wounds > 0:
                return True
            return False


units_dict[RedOak.unit_name] = RedOak
