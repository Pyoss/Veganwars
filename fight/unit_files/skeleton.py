from locales.emoji_utils import emote_dict
from fight.units import Unit, units_dict
from fight.ai import Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from fight import weapons, statuses
from locales.localization import LangTuple
from PIL import Image
import random


class SkeletonAi(Ai):

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.weapon_ai_dict = {'default': self.default_weapon_actions,
                               'bow': self.bow_weapon_actions}

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    # Выбор алгоритма действий в зависимости от оружия
    def form_actions(self):
        if self.unit.weapon.name in self.weapon_ai_dict:
            self.weapon_ai_dict[self.unit.weapon.name]()
        else:
            self.weapon_ai_dict['default']()

    # Алгоритм действий при экипировке оружия ближнего боя
    def default_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.bone_dict['legs']:
            self.move_forward(1 if not self.unit.weapon.targets() else 0)
        else:
            self.add_action(self.unit.crawl_action, 1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)

    # Алгоритм действий при экипировке лука
    def bow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available(self.unit.target):
            self.add_action(SpecialWeaponAction, 5, info=['fgt', str(self.fight), 'special'])


class Skeleton(Unit):
    unit_name = 'skeleton'
    control_class = SkeletonAi
    emote = emote_dict['skeleton_em']
    types = ['undead']
    image = 'D:\YandexDisk\Veganwars\Veganwars\\files\images\\units\skeleton.png'
    broken_dict = {'head': 'skill_1', 'legs': 'skill_3', 'arms': 'skill_2'}
    greet_msg = 'текст-скелетов'
    danger = 12
    default_loot = [('old_bone', (1, 90))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
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
        self.max_energy = 5
        self.loot_chances['weapon'] = 50
        self.recovery_energy = 5
        self.toughness = 5
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

    @staticmethod
    def get_dungeon_format_dict(member, inventory, inventory_fill):
        return {'name': member.name,
          'bones': member['wounds'],
          'head': emote_dict['check_em' if member['bone_dict']['head'] else 'cross_em'],
          'arm': emote_dict['check_em' if member['bone_dict']['arms'] else 'cross_em'],
          'leg': emote_dict['check_em' if member['bone_dict']['legs'] else 'cross_em'],
          'equipment': member.inventory.get_equipment_string(member.lang),
          'inventory': inventory, 'fill': inventory_fill}

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

units_dict[Skeleton.unit_name] = Skeleton
