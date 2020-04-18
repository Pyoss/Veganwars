from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons
import random
import file_manager
import json


class TutorialGoblinAi(StandardMeleeAi):
    ai_name = 'tutorial_goblin'

    def __init__(self):
        Ai.__init__(self)
        self.action_pattern_dict = {'default': self.default_weapon_actions}
        self.hint_done = False

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.action_pattern_dict['default']()

    def default_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        if not self.hint_done and self.unit.attempt < 3:
            self.unit.announce(self.get_hint_tuples('rus')[str(self.unit.attempt)])
            self.hint_done = True
        if StandardMeleeAi.nessesary_actions(self):
            return
        self.move_forward(1 if not self.unit.weapon.targets() and self.unit.energy > 2 else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy <= 2 else 0)

    def get_hint_tuples(self, lang):
        hint_tuples = json.loads(self.unit.to_string('skill_1').translate(lang))
        return hint_tuples


class TutorialGoblin(StandardCreature):
    greet_msg = 'текст-гоблина'
    unit_name = 'tutorial_goblin'
    control_class = TutorialGoblinAi
    emote = emote_dict['goblin_em']
    body_height = 'low'

    danger = 7

    def __init__(self, name=None, controller=None, unit_dict=None, complexity=None, attempt=None):
        StandardCreature.__init__(self, name, controller=controller, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.toughness = 5
        self.hp = 4
        self.weapon = weapons.Spear(self)
        self.attempt = attempt
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = int(self.max_energy / 2 + 1)
        self.loot_chances['weapon'] = 5

    def get_image(self):
        if self.weapon.name == 'spear':
            image = file_manager.my_path + './files/images/units/harpoon_goblin.png'
        else:
            image = file_manager.my_path + './files/images/units/fist_goblin.png'
        return Image.open(image), self.body_height, (0, 0)

units_dict[TutorialGoblin.unit_name] = TutorialGoblin
