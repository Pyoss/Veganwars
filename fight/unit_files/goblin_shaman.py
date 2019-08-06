from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons
import random


class GoblinShamanAi(StandardMeleeAi):
    ai_name = 'goblin'
    snatch_targets = []

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.fire_storm = (emote_dict['earth_em'], emote_dict['random_em'], emote_dict['ignite_em'])
        self.flash = (emote_dict['palm_em'], emote_dict['ignite_em'])
        self.ignite = (emote_dict['ignite_em'],)
        self.strong_ignite = (emote_dict['strength_em'], emote_dict['ignite_em'])

    def find_target(self):
        self.unit.target = random.choice(self.unit.targets())

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        team_state = self.get_team_state()
        if not self.unit.melee_targets:
            self.add_spell(self.fire_storm, self.unit.energy)
        if team_state == 'losing' and self.unit.melee_targets:
            self.move_back(self.unit.energy)
        elif team_state == 'losing':
            self.add_spell(self.strong_ignite, self.unit.energy, self.unit.target)
        elif team_state == 'competing':
            self.add_spell(self.flash, self.unit.energy, self.unit.target)
        elif team_state == 'winning':
            self.add_spell(self.strong_ignite, self.unit.energy, self.unit.target)
        else:
            self.add_spell(self.ignite, self.unit.energy, self.unit.target)
        self.reload(3 - self.unit.energy if self.unit.energy < 3 else 0)


class GoblinShaman(StandardCreature):
    unit_name = 'goblin_shaman'
    control_class = GoblinShamanAi
    emote = emote_dict['goblin_em']
    image = './files/images/units/sword_goblin.png'
    body_height = 'low'

    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 4
        self.toughness = 4
        self.hp = 4
        self.abilities = [abilities.SpellCaster(self), abilities.Dodge(self)]
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

units_dict[GoblinShaman.unit_name] = GoblinShaman
