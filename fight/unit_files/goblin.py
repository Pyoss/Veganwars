from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons
import random


class GoblinAi(StandardMeleeAi):
    ai_name = 'goblin'
    snatch_targets = []

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.action_pattern_dict = {'default': self.default_weapon_actions,
                                    'fist': self.snatch_weapon_action,
                                    'bow': self.bow_weapon_actions,
                                    'crossbow': self.crossbow_weapon_actions,
                                    'harpoon': self.harpoon_weapon_actions}

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.weapon.name in self.action_pattern_dict:
            self.action_pattern_dict[self.unit.weapon.name]()
        else:
            self.action_pattern_dict['default']()

    def snatch_weapon_action(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)
        if self.unit.target is not None and 'natural' not in self.unit.target.weapon.types \
                and not self.unit.weapon_to_member and not self.unit.lost_weapon:
            self.action_ability('weapon-snatcher',
                                (2 - self.unit.target.energy if self.unit.target.energy < 3 else 0)*5,
                                target=self.unit.target)
        elif self.unit.lost_weapon:
            self.add_action(PickUpWeapon, 5 - self.unit.energy if self.unit.energy < 3 else 0)

    def default_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(3 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)

    def bow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_back(5 - self.unit.energy if self.unit.melee_targets and self.unit.target.weapon.melee else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available(self.unit.target):
            self.action_weapon(self.unit.energy + 1 if self.unit.energy > 0 else 0)

    def harpoon_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_forward(2 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available():
            self.action_weapon_option(self.unit.energy if self.unit.energy > 0 else 0,
                                      str(random.choice(self.unit.targets())))

    def crossbow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_back(5 - self.unit.energy if self.unit.melee_targets
                                                       and self.unit.target.weapon.melee
                                                       and not self.unit.weapon.loaded else 0)
        if not self.unit.weapon.loaded:
            self.action_weapon(self.unit.energy if self.unit.target is not None else 0)
        else:
            self.attack(self.unit.energy if self.unit.target is not None else 0)


class Goblin(StandardCreature):
    greet_msg = 'текст-гоблина'
    unit_name = 'goblin'
    control_class = GoblinAi
    emote = emote_dict['goblin_em']
    default_loot = [('goblin_ear', (1, 70)), ('goblin_ear', (1, 30)), ('bandages', (1, 5)), ('bandages', (1, 5))]
    image = './files/images/units/sword_goblin.png'
    body_height = 'low'

    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.toughness = 5
        self.hp = 4
        self.abilities = [abilities.WeaponSnatcher(self), abilities.Dodge(self)]
        self.weapon = engine.get_random_with_chances(
            ((weapons.Fist, 2),)
        )(self)
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = int(self.max_energy / 2 + 1)
        self.loot_chances['weapon'] = 5
        self.stole = False

    def get_image(self):
        if self.weapon.name == 'knife':
            image = random.choice(('./files/images/units/knife_goblin.png',))
        elif self.weapon.name == 'harpoon':
            image = './files/images/units/harpoon_goblin.png'
        else:
            image = './files/images/units/fist_goblin.png'
        return Image.open(image), self.body_height, (0, 0)

    def generate_loot(self):
        if self.stole:
            self.loot_chances['weapon'] = 100
        return StandardCreature.generate_loot(self)


units_dict[Goblin.unit_name] = Goblin
