from adventures.map_engine import DungeonMap, EnemyKey
from adventures import locations
import engine
from chat_wars import chat_main
from locales import emoji_utils


class Dungeon:
    team = [1, 2]


class FirstDungeon(DungeonMap):
    name = 'first'

    def __init__(self, dungeon, new=True, dungeon_dict=None):
        DungeonMap.__init__(self, length=10, dungeon=dungeon, branch_length=3, branch_number=1,  new=True, dungeon_dict=None)
        # self.balance_integer: маятник локаций для определения положительной или отрицательной локации. Его\
        # смещение редактируется параметром location.impact_integer
        # self.generation_seed: % влияния на смещение маятника локаций в сторону положительной локации
        # self.neutral_chance: текущая вероятность появления нейтральной локации
        # self.neutral_probability: увеличение вероятности появления нейтральной локации
        # self.neutral_scarceness: уменьшение вероятности появления нейтральной локации после появления
        # self.enemy_list: [EnemyKey(минимальная сложность, максимальная сложность, вероятность появления)]

        self.balance_integer = 10
        self.generation_seed = 50
        self.neutral_chance = 0
        self.neutral_probability = 20
        self.neutral_scarceness = 100
        self.impact_integer_range = (-5, 5)
        self.wall_emote = emoji_utils.emote_dict['wall_em']

        self.enemy_list = (EnemyKey('bloodbug', 9, 238, 10),
                           EnemyKey('goblin', 7, 238, 10),
                           EnemyKey('bloodbug+goblin', 7, 238, 10),
                           EnemyKey('skeleton', 12, 238, 5),
                           EnemyKey('worm', 8, 238, 10),
                           EnemyKey('worm+bloodbug', 8, 238, 10),
                           EnemyKey('snail+worm', 16, 238, 4),
                           EnemyKey('goblin+goblin-bomber', 12, 238, 10))

    def generate_location_dict(self):
        base_list = [(locations.PlaceHolder, 1), (locations.PlaceHolderPos, 10), (locations.PlaceHolderNeg, 10)]
        self.location_dict = engine.ListedDict(base_dict={('core', 'end'): [(locations.End, 1)],
                                                          ('core', 'crossroad'): [(locations.CrossRoad, 1)],
                                                          ('core', 'default'): base_list,
                                                          ('branch', 'end'): [(locations.End, 1)],
                                                           ('branch', 'crossroad'): base_list,
                                                          ('branch', 'entrance'): base_list,
                                                          ('branch', 'default'): base_list})


class Forest(DungeonMap):
    name = 'dark_forest'

    def __init__(self, dungeon, new=True, dungeon_dict=None):
        DungeonMap.__init__(self, length=10, dungeon=dungeon, branch_length=0, branch_number=0,  new=True, dungeon_dict=None)
        # self.balance_integer: маятник локаций для определения положительной или отрицательной локации. Его\
        # смещение редактируется параметром location.impact_integer
        # self.generation_seed: % влияния на смещение маятника локаций в сторону положительной локации
        # self.neutral_chance: текущая вероятность появления нейтральной локации
        # self.neutral_probability: увеличение вероятности появления нейтральной локации
        # self.neutral_scarceness: уменьшение вероятности появления нейтральной локации после появления
        # self.enemy_list: [EnemyKey(минимальная сложность, максимальная сложность, вероятность появления)]

        self.balance_integer = -10
        self.generation_seed = 50
        self.neutral_chance = 0
        self.neutral_probability = 20
        self.neutral_scarceness = 100
        self.impact_integer_range = (-5, 5)
        self.wall_emote = emoji_utils.emote_dict['tree_em']

        self.enemy_list = (EnemyKey('goblin', 7, 238, 10),)

    def generate_location_dict(self):
        base_list = [(locations.ForestNeutral, 1), (locations.ForestPos, 10), (locations.ForestBarrow, 10)]
        self.location_dict = engine.ListedDict(base_dict={('core', 'end'): [(locations.ForestEnd, 1)],
                                                          ('core', 'crossroad'): [(locations.ForestCrossroad, 1)],
                                                          ('core', 'default'): base_list,
                                                          ('branch', 'end'): [(locations.ForestEnd, 1)],
                                                           ('branch', 'crossroad'): base_list,
                                                          ('branch', 'entrance'): base_list,
                                                          ('branch', 'default'): base_list})


class TutorialMap(DungeonMap):
    name = 'tutorial'

    def __init__(self, dungeon, new=True, dungeon_dict=None):
        from adventures.map_locations import tutorial_section_locations
        DungeonMap.__init__(self, length=10, dungeon=dungeon, branch_length=0, branch_number=0,  new=True, dungeon_dict=None)
        # self.balance_integer: маятник локаций для определения положительной или отрицательной локации. Его\
        # смещение редактируется параметром location.impact_integer
        # self.generation_seed: % влияния на смещение маятника локаций в сторону положительной локации
        # self.neutral_chance: текущая вероятность появления нейтральной локации
        # self.neutral_probability: увеличение вероятности появления нейтральной локации
        # self.neutral_scarceness: уменьшение вероятности появления нейтральной локации после появления
        # self.enemy_list: [EnemyKey(минимальная сложность, максимальная сложность, вероятность появления)]

        self.balance_integer = -10
        self.generation_seed = 50
        self.neutral_chance = 0
        self.neutral_probability = 20
        self.neutral_scarceness = 100
        self.impact_integer_range = (-5, 5)
        self.wall_emote = emoji_utils.emote_dict['wall_em']
        self.goblin_attempt = 1

        self.enemy_list = (EnemyKey('tutorial_goblin', 7, 238, 10),)
        self.entrance_location = tutorial_section_locations.TutorialEntrance

    def fill_locations(self):
        from adventures.map_locations import tutorial_section_locations
        self.width = 3
        self.height = 3
        for x in range(self.width):
            for y in range(self.height):
                if x == 0 and y == 0:
                    self.location_matrix[(x, y)] = tutorial_section_locations.TutorialEntrance(x, y, self.dungeon, self.map_tuples[(0, 0)])
                elif x == 1 and y == 0:
                    self.location_matrix[(x, y)] = tutorial_section_locations.TutorialSecondLoc(x, y, self.dungeon, self.map_tuples[(0, 0)])
                elif x == 2 and y == 0:
                    self.location_matrix[(x, y)] = tutorial_section_locations.TutorialEnemyLoc(x, y, self.dungeon, self.map_tuples[(0, 0)])
                else:
                    self.location_matrix[(x, y)] = self.generate_wall(x, y)

    def generate_location_dict(self):
        base_list = [(locations.ForestNeutral, 1), (locations.ForestPos, 10), (locations.ForestBarrow, 10)]
        self.location_dict = engine.ListedDict(base_dict={('core', 'end'): [(locations.ForestEnd, 1)],
                                                          ('core', 'crossroad'): [(locations.ForestCrossroad, 1)],
                                                          ('core', 'default'): base_list,
                                                          ('branch', 'end'): [(locations.ForestEnd, 1)],
                                                           ('branch', 'crossroad'): base_list,
                                                          ('branch', 'entrance'): base_list,
                                                          ('branch', 'default'): base_list})

    def wrap(self):
        chat_main.add_user(self.party.members[0])

