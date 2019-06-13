from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons
import random


class TreeFolkAi(StandardMeleeAi):
    ai_name = 'treefolk'

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


class TreeFolk(StandardCreature):
    unit_name = 'treefolk'
    control_class = TreeFolkAi
    emote = emote_dict['tree_em']