from adventures.map_engine import DungeonMap, EnemyKey
from adventures import locations
import engine
from locales import emoji_utils
from fight import fight_main, ai, items
from locales.localization import LangTuple
from bot_utils import bot_methods
import random
import inspect
import sys


class FirstDungeon(DungeonMap):
    name = 'NecromancerPit'

    def __init__(self, dungeon, new=True, dungeon_dict=None):
        DungeonMap.__init__(self, 10, dungeon,  2, 2,  new=True, dungeon_dict=None)

        self.balance_integer = 0
        self.generation_seed = 75
        self.neutral_chance = 0
        self.neutral_probability = 20
        self.neutral_scarceness = 100
        self.impact_integer_range = (-5, 5)

        self.enemy_list = (EnemyKey('bloodbug', 9, 238, 10),
                           EnemyKey('goblin', 7, 238, 10),
                           EnemyKey('bloodbug+goblin', 7, 238, 10),
                           EnemyKey('skeleton', 12, 238, 5),
                           EnemyKey('worm', 8, 238, 10),
                           EnemyKey('worm+bloodbug', 8, 238, 10),
                           EnemyKey('snail+worm', 16, 238, 4),
                           EnemyKey('goblin+goblin-bomber', 12, 238, 10))

    def generate_location_dict(self):
        base_list = [(locations.PlaceHolder, 1), (locations.PlaceHolderPos, 10), (locations.MobLocation, 10)]
        self.location_dict = engine.ListedDict(base_dict={('core', 'end'): base_list,
                                                          ('core', 'crossroad'): [(locations.CrossRoad, 1)],
                                                          ('core', 'default'): base_list,
                                                          ('branch', 'end'): base_list,
                                                          ('branch', 'crossroad'): base_list,
                                                          ('branch', 'entrance'): base_list,
                                                          ('branch', 'default'): base_list})