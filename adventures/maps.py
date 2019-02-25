from adventures.map_engine import DungeonMap
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
        DungeonMap.__init__(self, 6, dungeon,  2, 2,  new=True, dungeon_dict=None)
        self.enemy_dict = {'goblin': (0, 238)}