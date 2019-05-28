from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai, get_lowest_energy
from fight.standart_actions import *
from bot_utils.keyboards import *
from PIL import Image
from fight import abilities, weapons, items
import random


class GoblinBomberAi(StandardMeleeAi):
    ai_name = 'goblin'
    snatch_targets = []

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.item_action_dict = {'throwknife': self.use_throwing_knife,
                                 'bomb': self.use_bomb,
                                 'mine': self.use_mine}

    def find_target(self):
        self.unit.target = get_lowest_energy(self.unit.targets())
        if engine.roll_chance(30):
            self.unit.target = random.choice(self.unit.targets())

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_back(5 - self.unit.energy if self.unit.melee_targets and self.unit.target.weapon.melee else 0)
        if not self.unit.items:
            if engine.roll_chance(30) and not self.unit.searching:
                self.unit.searching = True
            if not self.unit.searching:
                self.add_action(self.unit.search_bag_action, self.unit.energy*2)
            else:
                self.add_action(self.unit.find_item_action, self.unit.energy*2)
        else:
            for item in self.unit.items:
                if item.name in self.item_action_dict:
                    self.item_action_dict[item.name]()
                    break

    def use_throwing_knife(self):
        self.action_item('throwknife', self.unit.energy, str(self.unit.target))

    def use_bomb(self):
        self.action_item('bomb', self.unit.energy)

    def use_mine(self):
        self.action_item('mine', self.unit.energy, str(random.randint(1, 4)))


class GoblinBomber(StandardCreature):
    greet_msg = 'текст-гоблина'
    unit_name = 'goblin-bomber'
    control_class = GoblinBomberAi
    emote = emote_dict['goblin_em']
    default_loot = [('goblin_ear', (1, 70)), ('goblin_ear', (1, 30)), ('bandages', (1, 5)), ('bandages', (1, 5))]
    image = './files/images/units/goblin_bomber.png'
    danger = 7

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.unit_name_marker = 'goblin'
        # Максимальные параметры
        self.max_hp = 3
        self.toughness = 3
        self.hp = 3
        self.abilities = [abilities.Dodge(self)]
        self.searching = False
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        else:
            if engine.roll_chance(50):
                self.searching = True
            else:
                self.items.append(items.Bomb(self))

        self.energy = int(self.max_energy / 2 + 1)
        self.search_bag_action = self.create_action('search_bag', self.search_bag, None, order=10)
        self.find_item_action = self.create_action('find_item', self.find_item, None, order=10)
        self.item_pool = [(items.Mine, 1),
                          (items.Bomb, 3),
                          (items.ThrowingKnife, 2)]

    @staticmethod
    def search_bag(action):
        unit = action.unit
        unit.string('skill_1', format_dict={'actor': unit.name})
        unit.searching = True

    @staticmethod
    def find_item(action):
        unit = action.unit
        found_item = engine.get_random_with_chances([(items.Mine, 1),
                          (items.Bomb, 3),
                          (items.ThrowingKnife, 2)]
                                                    )(unit)
        unit.items.append(found_item)
        unit.string('skill_2', format_dict={'actor': unit.name, 'item': found_item.name_lang_tuple()})
        unit.searching = False

    def get_image(self):
        return Image.open(self.image), 'low', (0, 0)

    def generate_loot(self):
        loot_container = StandardCreature.generate_loot(self)
        loot_container.put(engine.get_random_with_chances(self.item_pool).name)
        return loot_container

units_dict[GoblinBomber.unit_name] = GoblinBomber
