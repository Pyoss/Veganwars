from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons, statuses
import random


class OgreAi(StandardMeleeAi):
    ai_name = 'ogre'
    snatch_targets = []

    def __init__(self, fight):
        Ai.__init__(self, fight)

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.grabbed_target is not None:
            self.action_ability('ogre_throw', 10)
            return
        if len(self.unit.targets()) != len(self.unit.melee_targets):
            self.action_ability('ogre_charge', self.unit.energy)
        self.action_ability('ogre_grab', 5 if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_forward(4 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)

    def get_action(self, edit=False):
        action = Ai.get_action(self, edit=edit)
        if action.name == 'ability':
            print(action.ability.name)
            if action.ability.name is 'ogre_charge':
                self.unit.target = random.choice([trgt for trgt in self.unit.targets() if trgt not in self.unit.melee_targets])
                self.unit.announce(self.unit.to_string('skill_2', format_dict={'target': self.unit.target.name}))
                return
            elif action.ability.name is 'ogre_grab':
                self.unit.announce(self.unit.to_string('skill_2', format_dict={'target': self.unit.target.name}))
                return

        elif engine.roll_chance(50) and action.name == 'melee_reload':
            self.unit.announce(self.unit.to_string('skill_1'))





class Ogre(StandardCreature):
    unit_name = 'ogre'
    control_class = OgreAi
    emote = emote_dict['ogre_em']
    image = './files/images/units/ogre.png'
    body_height = 'high'

    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 6
        self.toughness = 8
        self.hp = 6
        self.speed = 13
        self.max_energy = 7
        self.melee_accuracy = 1
        self.weapon = weapons.Cleaver(self)
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = int(self.max_energy / 2 + 1)
        self.loot_chances['weapon'] = 5
        self.grabbed_target = None
        self.new_ability(ability_name='ogre_grab', ability_func=self.grab,
                         ability_type='instant', cooldown=3,
                         name_tuple=self.to_string('button_1'))
        self.new_ability(ability_name='ogre_charge', ability_func=self.charge,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'), cooldown=2)
        self.new_ability(ability_name='ogre_throw', ability_func=self.throw,
                         ability_type='instant',
                         name_tuple=self.to_string('button_1'))

    def get_image(self):
        return Image.open(self.image), self.body_height, (0, 0)

    @staticmethod
    def grab(ability, action):
        self = action.unit
        if 'dodge' in self.target.action or 'back' in self.target.action:
            self.string('skill_6', format_dict={'target': self.target.name})
        else:
            self.string('skill_5', format_dict={'target': self.target.name})
            self.target.disabled.append(self)
            self.grabbed_target = self.target
        self.waste_energy(4)

    @staticmethod
    def charge(ability, action):
        self = action.unit
        self.move_forward()
        x = Attack(self, self.fight, stringed=False)
        x.activate()
        if x.dmg_done:
            self.string('skill_3', format_dict={'target': self.target.name, 'damage': x.dmg_done,
                                                'weapon': self.weapon.name_lang_tuple()})
        else:
            self.string('skill_4', format_dict={'target': self.target.name,
                                                'weapon': self.weapon.name_lang_tuple()})

    @staticmethod
    def throw(ability, action):
        self = action.unit
        damage = 3
        statuses.Prone(self.grabbed_target)
        self.grabbed_target.receive_damage(damage)
        self.grabbed_target.disabled.remove(self)
        self.grabbed_target.move_back()
        if len(self.targets()) > 1:
            target = random.choice([trgt for trgt in self.targets() if trgt != self.grabbed_target])
            if 'dodge' not in self.target.action:
                self.string('skill_7', format_dict={'target_1': self.grabbed_target.name, 'target_2': target.name,
                                                    'damage': damage})
                target.receive_damage(damage)
                target.move_back()
                statuses.Prone(target)
                self.grabbed_target = None
                return
        self.string('skill_8', format_dict={'target_1': self.grabbed_target.name,
                                            'damage': damage})
        self.grabbed_target = None

units_dict[Ogre.unit_name] = Ogre
