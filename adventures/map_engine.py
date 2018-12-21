from bot_utils import bot_methods
from bot_utils  .keyboards import Button, form_keyboard
from locales.emoji_utils import emote_dict
from locales.localization import LangTuple
from fight import units, items, weapons, armors
from adventures import locations
import Testing
import engine
import random

dungeons = {}
player_dict = {}


class PartyMovement:

    def __init__(self, party, start_location, end_location):
        self.party = party
        self.start_location = start_location
        self.end_location = end_location

    def execute(self, call):
        if self.party.ask_move(self.end_location, call) and self.start_location.move_permission(self, call) \
                and self.end_location.move_permission(self, call):
            self.party.move(self.end_location)


# --------------------------------------------- Карта Подземелья -----------------------------------------------------
# Объект карты подземелья
class DungeonMap:
    name = None
    wall_location = None

    def __init__(self, length, dungeon, new=True, dungeon_dict=None):
        self.location_matrix = dict()
        self.length = length
        self.entrance = None
        self.exit = None
        self.party = None
        self.dungeon = dungeon
        self.table_row = 'dungeons_' + self.name

    def create_map(self):
        self.dungeon.map = self
        map_tuples = Testing.generate_core(complexity=len(self.dungeon.lobby[0])*10, length=self.length)
        Testing.generate_branch(map_tuples)
        Testing.generate_branch(map_tuples)
        Testing.generate_branch(map_tuples)
        self.width = max(map_tuple[0] for map_tuple in map_tuples) + 1
        self.height = max(map_tuple[1] for map_tuple in map_tuples) + 1
        for x in range(0, self.width):
            for y in range(0, self.height):
                if (x, y) in map_tuples:
                    self.location_matrix[(x, y)] = self.generate_location(x, y, map_tuples[(x, y)])
                else:
                    self.location_matrix[(x, y)] = self.generate_wall(x, y)
        return self

    def generate_location(self, x, y, map_tuple):
        pass

    def generate_wall(self, x, y):
        return Location(x, y, self.dungeon, map_tuple=None)

    def start(self):
        #self.greetings_message()
        self.dungeon.party.move(self.dungeon.map.get_location(0, 0))

    def fill_end(self):
        pass

    def fill_entrance(self):
        pass

    def fill_crossroads(self, *args):
        pass

    def fill_dead_ends(self, *args):
        pass

    def fill_placeholders(self, *args):
        pass

    # Возвращает локацию от координат матрицы
    def get_location(self, x, y):
        return self.location_matrix[(int(x), int(y))]

    def greetings_message(self):
        for member in self.dungeon.party.members:
            message = LangTuple(self.table_row, 'greeting').translate(member.lang)
            bot_methods.send_message(member.chat_id, message)


def get_enemy(complexity, enemy_dict):
    enemy_pool = (key for key in enemy_dict if enemy_dict[key][0] < complexity < enemy_dict[key][1])
    enemy = random.choice(list(enemy_pool))
    enemy_types = [name for name in enemy.split('+')]
    danger_dict = {enemy: units.units_dict[enemy].danger for enemy in enemy_types}
    enemy_list = []
    strongest_added = False
    while complexity >= min(list(danger_dict.values())):
        strongest_enemies = [key for key in danger_dict.keys()
                                if danger_dict[key] == max(list(danger_dict.values()))]
        if strongest_enemies != enemy_types:
            if not strongest_added:
                chosen_enemy = strongest_enemies[0]
                enemy_list.append(chosen_enemy)
                strongest_added = True
            else:
                for enemy in enemy_types:
                    if complexity < danger_dict[enemy]:
                        enemy_types.remove(enemy)
                chosen_enemy = random.choice(enemy_types)
                enemy_list.append(chosen_enemy)
        else:
            chosen_enemy = random.choice(enemy_types)
            enemy_list.append(chosen_enemy)
        complexity -= danger_dict[chosen_enemy]
    return enemy_list


# --------------------------------------------------------------------------------------------------
# Объект комнаты/локации карты
class Location:
    name = 'location'
    greet_msg = 'Тестовое приветствие локации'
    image = None
    emote = emote_dict['wall_em']
    visited_emote = emote_dict['visited_map_em']

    def __init__(self, x, y, dungeon, map_tuple):
        self.visited = False
        self.current = False
        self.seen = False
        self.coordinates = (x, y)
        self.x = x
        self.y = y
        self.dungeon = dungeon
        self.special = '0'
        if map_tuple is not None:
            self.complexity = map_tuple.complexity

    # Возвращает кнопку для клавиатуры карты
    def return_button(self):
        return Button(text=self.emoji(), callback_data='map_' + str(self.dungeon.chat_id) + '_move_' + '-'.join([str(item) for item in self.coordinates]))

    def buttons(self, member):
        return list()

    def handler(self, call):
        pass

    # Возвращает эмодзи карты
    def emoji(self):
        if self.current:
            return emote_dict['current_map_em']
        elif self.visited:
            return self.visited_emote
        elif self.is_close(self.dungeon.party.current_location) or self.seen:
            return self.emote
        else:
            return emote_dict['question_em']

    # Перемещение группы
    def enter_location(self, party):
        self.current = True
        party.current_location = self
        if not self.visited:
            self.greet_party()
            for member in party.members:
                member.message_id = None
        self.on_enter()
        self.visited = True

    def greet_party(self):
        if self.greet_msg:
            self.dungeon.delete_map()
            self.dungeon.party.send_message(self.greet_msg,
                                            image=self.image)

    # Проверяет, можно ли производить перемещение с данной локацией
    def move_permission(self, movement, call):
        bot_methods.answer_callback_query(call, 'Вы не можете здесь пройти.', alert=False)
        return self.available()

    def available(self):
        return False

    # Функция, запускающаяся при входе в комнату. Именно сюда планируется пихать события.
    def on_enter(self):
        self.dungeon.update_map()

    def leave_location(self):
        self.current = False

    # Функция проверяет, можно ли шагнуть из одной локации в другую
    def is_close(self, location):
        if abs(location.x - self.x) + abs(location.y - self.y) < 2:
            self.seen = True
            return True

    # Находит список локаций, расположенных вплотную к текущей
    def get_close(self):
        close_locations = []
        if self.y > 0:
            close_locations.append(self.dungeon.map.get_location(self.x, self.y-1))
        if self.y < self.dungeon.map.height - 1:
            close_locations.append(self.dungeon.map.get_location(self.x, self.y+1))
        if self.x > 0:
            close_locations.append(self.dungeon.map.get_location(self.x-1, self.y))
        if self.x < self.dungeon.map.width - 1:
            close_locations.append(self.dungeon.map.get_location(self.x+1, self.y))
        return close_locations

    # Функция проверяет, видно ли из одной локации другую
    def is_visible(self, location):
        if abs(location.x - self.x) < 2 and abs(location.y - self.y) < 2:
            return True

    # Функция возвращает список локаций, которые видно на карте из данной
    def get_visible(self):
        center_x = self.x
        center_y = self.y
        if self.y == 0:
            center_y += 1
        elif self.y == self.dungeon.map.height - 1:
            center_y -= 1
        if self.x == 0:
            center_x += 1
        elif self.x == self.dungeon.map.width - 1:
            center_x -= 1
        visible_locations_x = [center_x - 1, center_x, center_x + 1]*3
        visible_locations_y = [*[center_y - 1]*3, *[center_y]*3, *[center_y + 1]*3]
        visible_locations = list(map(self.dungeon.map.get_location, visible_locations_x, visible_locations_y))
        return visible_locations

    def create_path(self):
        self.emote = '-'

    # -------------------------------------- Методы для ориентирования вокруг локации -------------------------

    def higher(self):
        if self.y < self.dungeon.map.max_y - 1:
            return self.dungeon.map.get_location(self.x, self.y + 1)
        else:
            return None

    def lower(self):
        if self.y > 0:
            return self.dungeon.map.get_location(self.x, self.y - 1)
        else:
            return None

    def right(self):
        if self.x < self.dungeon.map.max_x - 1:
            return self.dungeon.map.get_location(self.x + 1, self.y)
        else:
            return None

    def left(self):
        if self.x > 0:
            return self.dungeon.map.get_location(self.x - 1, self.y )
        else:
            return None

    # Перевод локации в строку для сохранения

    def __str__(self):
        visited = 'visited' if self.visited else 'closed'
        return self.name + '_' + self.special + '_' + visited


class MobPack:
    def __init__(self, *args):
        self.mob_units = args

    def join_fight(self):
        team_dict = {}
        i = 0
        for unit in self.mob_units:
            team_dict[(units.units_dict[unit], i)] = (None, units.units_dict[unit]().to_dict())
            i += 1
        return team_dict


class FirstDungeon(DungeonMap):
    name = 'NecromancerPit'
    wall_location = None

    def __init__(self, dungeon, new=True, dungeon_dict=None):
        DungeonMap.__init__(self, 22, dungeon, new=True, dungeon_dict=None)
        self.low_loot = ['bandages', 'chitin', 'stimulator', 'helmet', 'breastplate', 'bandages', 'knife', 'adrenalin']
        self.enemy_dict = {'goblin': (7, 238), 'skeleton': (12, 238), 'skeleton+zombie': (12, 238), 'worm+goblin': (7, 238)}
        unused_loot = [items.Molotov().to_dict(), items.ThrowingKnife().to_dict(),
                       items.Jet().to_dict(), items.Chitin().to_dict()]
        unused_weapons = [weapons.Knife().to_dict(), weapons.Spear().to_dict(),
                          weapons.Hatchet().to_dict(), weapons.Bow().to_dict()]
        unused_armor = [armors.Breastplate().to_dict(), armors.Helmet().to_dict(), armors.Shield().to_dict()]

    def generate_location(self, x, y, map_tuple):
        goblins = False
        if x == 0 and y == 0:
            return locations.Entrance(0, 0, self.dungeon, map_tuple)
        elif x == 1 and goblins or y == 1 and goblins:
            goblins = True
            return locations.MobLocation(x, y, self.dungeon, map_tuple)
        elif 'core' in map_tuple.types:
            if 'end' in map_tuple.types:
                return locations.End(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)
            elif 'crossroad' in map_tuple.types:
                return locations.CrossRoad(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)
            else:
                return locations.MobLocation(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)
        elif 'branch' in map_tuple.types:
            if 'dead_end' in map_tuple.types:
                return locations.DeadEnd(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)
            elif 'crossroad' in map_tuple.types:
                return locations.CrossRoad(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)
            else:
                return locations.PlaceHolder2(x=x, y=y, dungeon=self.dungeon, map_tuple=map_tuple)


# --------------------------------------------------------------------------------------------------
# Объект группы в подземелье
