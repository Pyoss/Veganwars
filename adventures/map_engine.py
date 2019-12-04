import random

import engine, image_generator
from adventures import map_generator
from bot_utils import bot_methods
from bot_utils.keyboards import Button, DungeonButton, form_keyboard
from fight import units
from locales.emoji_utils import emote_dict
from locales.localization import LangTuple
import threading, json


class PartyMovement:

    def __init__(self, party, start_location, end_location):
        self.party = party
        self.start_location = start_location
        self.end_location = end_location

    def execute(self, call):
        if self.party.ask_move(self.end_location, call) and self.start_location.move_permission(self, call) \
                and self.end_location.move_permission(self, call):
            self.end_location.entrance_location = self.start_location
            self.party.move(self.end_location)


# --------------------------------------------- Карта Подземелья -----------------------------------------------------
# Объект карты подземелья
class DungeonMap:
    name = 'blank'
    wall_location = 'W'

    def __init__(self, length, dungeon, branch_length, branch_number, new=True, dungeon_dict=None):
        self.location_matrix = dict()
        self.length = length
        self.width = 0
        self.height = 0
        self.branch_length = branch_length
        self.branch_number = branch_number
        self.entrance = None
        self.exit = None
        self.party = None
        self.dungeon = dungeon
        self.table_row = 'dungeons_' + self.name
        self.location_dict = {}
        self.generate_location_dict()
        self.map_tuples = None
        self.negative_modifier = None
        self.positive_modifier = None

        self.balance_integer = 0
        self.generation_seed = 65
        self.neutral_chance = 0
        self.neutral_probability = 20
        self.neutral_scarceness = 100
        self.impact_integer_range = (-5, 5)
        self.negative_modifier = 1
        self.entrance_location = None

        self.statistics = {'positive': 0,
                           'negative': 0,
                           'neutral': 0}

    def generate_location_dict(self):
        pass

    def create_map(self):
        self.dungeon.map = self
        self.positive_modifier = -self.generation_seed / 100
        self.create_map_tuples()
        self.create_grid()
        self.fill_locations()

    def visualize(self):
        map_string = ''
        for x in range(0, self.width):
            for y in range(0, self.height):
                map_string += self.location_matrix[(x, y)].emote + ' '
            map_string += '\n'
        bot_methods.err(map_string)

    def create_map_tuples(self):
        self.map_tuples = map_generator.generate_core(complexity=self.dungeon.complexity * 10, length=self.length)
        if self.branch_number:
            for i in range(self.branch_number):
                map_generator.generate_branch(self.map_tuples, self.branch_length)
        for key in self.map_tuples:
            if len(self.map_tuples[key].types) == 1:
                self.map_tuples[key].types.append('default')
            self.map_tuples[key].types = tuple(self.map_tuples[key].types)
        map_generator.visualise(self.map_tuples)

    def create_grid(self):
        self.width = max(map_tuple[0] for map_tuple in self.map_tuples) + 1
        if self.width < 3:
            self.width = 3
        self.height = max(map_tuple[1] for map_tuple in self.map_tuples) + 1
        if self.height < 3:
            self.height = 3

    def fill_locations(self):
        for x in range(0, self.width):
            for y in range(0, self.height):
                if (x, y) in self.map_tuples:
                    self.location_matrix[(x, y)] = self.generate_location(x, y)
                else:
                    self.location_matrix[(x, y)] = self.generate_wall(x, y)

    def generate_location(self, x, y):
        map_tuple = self.map_tuples[(x, y)]
        del self.map_tuples[(x, y)]
        if x == 0 and y == 0:
            return self.entrance_location(0, 0, self.dungeon, map_tuple)

        if engine.roll_chance(self.neutral_chance):
            self.neutral_chance -= self.neutral_scarceness
            self.neutral_chance = 0 if self.neutral_chance < 0 else self.neutral_chance
            impact = 'neutral'
            current_modifier = 0
        else:
            self.neutral_chance += self.neutral_probability
            impact_integer = random.randint(*self.impact_integer_range) + self.balance_integer
            if impact_integer < 0:
                impact = 'negative'
                current_modifier = self.negative_modifier
            else:
                impact = 'positive'
                current_modifier = self.positive_modifier

        self.statistics[impact] += 1

        locations_pool = [location_weight for location_weight in self.location_dict[map_tuple.types]
                          if location_weight[0].impact == impact
                          and location_weight[0].available_for_pool(self.map_tuples)]

        if not locations_pool:
            locations_pool = [location_weight for location_weight in self.location_dict[map_tuple.types]
                              if location_weight[0].available_for_pool(self.map_tuples)]
        return self.create_location(x, y, map_tuple, current_modifier, locations_pool)

    def create_location(self, x, y, map_tuple, current_modifier, locations_pool):
        location = engine.get_random_with_chances(locations_pool)(x, y, self.dungeon, map_tuple)
        location.to_location_pool(map_tuple, current_modifier)
        return location

    def generate_wall(self, x, y):
        return Location(x, y, self.dungeon, map_tuple=None)

    def start(self):
        self.greetings_message()
        location = self.dungeon.map.get_location(0, 0)
        self.dungeon.party.move(location, events=False, exhaust=False)

    # Возвращает локацию от координат матрицы
    def get_location(self, x, y):
        return self.location_matrix[(int(x), int(y))]

    def greetings_message(self):
        for member in self.dungeon.party.members:
            message = LangTuple(self.table_row, 'greeting').translate(member.lang)
            bot_methods.send_message(member.chat_id, message)


def get_enemy(complexity, total_enemy_list):
    enemy_pool = (enemy_key for enemy_key in total_enemy_list if enemy_key.min_complexity < complexity < enemy_key.max_complexity)
    enemy = engine.get_random_with_chances([(enemy_key.name, enemy_key.probability) for enemy_key in list(enemy_pool)])
    enemy_types = [name for name in enemy.split('+')]
    danger_dict = {enemy: units.units_dict[enemy].danger for enemy in enemy_types}
    fighting_enemy_list = []
    strongest_added = False
    while complexity >= min(list(danger_dict.values())):
        strongest_enemies = [key for key in danger_dict.keys()
                                if danger_dict[key] == max(list(danger_dict.values()))]
        if strongest_enemies != enemy_types:
            if not strongest_added:
                chosen_enemy = strongest_enemies[0]
                fighting_enemy_list.append(chosen_enemy)
                strongest_added = True
            else:
                for enemy in enemy_types:
                    if complexity < danger_dict[enemy]:
                        enemy_types.remove(enemy)
                chosen_enemy = random.choice(enemy_types)
                fighting_enemy_list.append(chosen_enemy)
        else:
            chosen_enemy = random.choice(enemy_types)
            fighting_enemy_list.append(chosen_enemy)
        complexity -= danger_dict[chosen_enemy]
    return fighting_enemy_list


# --------------------------------------------------------------------------------------------------
# Объект комнаты/локации карты
class Location:
    name = 'location'
    image = None
    image_file = None
    finish = False
    default_emote = emote_dict['wall_em']
    impact = 'neutral'
    impact_integer = 0
    standard_mobs = False

    def __init__(self, x, y, dungeon, map_tuple):
        self.state = 'entrance'
        self.table_row = 'locations_' + self.name
        self.visited = False
        self.current = False
        self.seen = False
        self.action_expected = False
        self.coordinates = (x, y)
        self.x = x
        self.y = y
        self.dungeon = dungeon
        self.special = '0'
        self.mobs = None
        self.mob_team = None
        self.mob_image = None
        self.receipts = engine.ChatContainer()
        if map_tuple is not None:
            self.complexity = map_tuple.complexity
        self.emote = self.get_emote()
        self.get_mobs()
        self.loot = engine.ChatContainer()
        self.cleared_emote = ' '
        self.entrance_location = None
        self.cleared = False
        self.create_images()

    def get_button_tuples(self, lang):
        button_tuples = json.loads(LangTuple(self.table_row, 'buttons').translate(lang))
        return button_tuples

    def create_images(self):
        if self.mobs is not None:
            self.mob_image = image_generator.create_dungeon_image(self.image_file, self.mobs.get_image_tuples())

    def get_mobs(self):
        if self.standard_mobs:
            mobs = get_enemy(self.complexity, self.dungeon.map.enemy_list)
            self.mobs = MobPack(*mobs, complexity=self.complexity)

    def fight(self, first_turn=None):
        for member in self.dungeon.party.members:
            member.occupied = True
        thread = threading.Thread(target=self.location_fight, kwargs={'first_turn': first_turn})
        thread.start()

    def get_emote(self):
        return self.dungeon.map.wall_emote

    def get_greet_tuple(self):
        return LangTuple(self.table_row, 'greeting')

    def get_lang_tuple(self, string):
        return LangTuple(self.table_row, string)

    @staticmethod
    def answer_callback_query(call, text, alert=True):
        bot_methods.answer_callback_query(call, text, alert=alert)

    @classmethod
    def available_for_pool(cls, map_tuples):
        return True

    def to_location_pool(self, map_tuple, current_modifier):
        dngn_map = self.dungeon.map
        dngn_map.balance_integer += self.impact_integer*current_modifier

    # Возвращает кнопку для клавиатуры карты
    def return_button(self):
        return Button(text=self.emoji(), callback_data='map_' + str(self.dungeon.chat_id) + '_move_' + '-'.join([str(item) for item in self.coordinates]))

    def get_buttons(self, member):
        return list()

    def handler(self, call):
        bot_methods.err(call.data)
        data = call.data.split('_')
        action = data[3]
        for tpl in self.get_action_dict():
            if str(tpl[0]) == action:
                tpl[1](call)

    def to_map(self, call):
        bot_methods.bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
        for member in self.dungeon.party.members:
            member.occupied = False
        self.dungeon.update_map(new=True)

    # Возвращает эмодзи карты
    def emoji(self):
        if self.current:
            return emote_dict['current_map_em']
        elif self.cleared:
            return self.cleared_emote
        elif self.is_close(self.dungeon.party.current_location) or self.seen:
            return self.get_emote()
        else:
            return emote_dict['unseen_em']

    def get_image(self):
        return self.image

    # Вход группы в локацию
    def enter_location(self, party, new_map=False):
        # Формирование новой картинки (для заполнения картинки новыми объектами)
        self.image = self.get_image()

        self.current = True
        party.current_location = self

        if not self.cleared:
            self.dungeon.delete_map()
            for member in party.members:
                member.message_id = None
                member.occupied = True
            self.enter()
            self.visited = True
        else:
            # В случае повторного посещения пустой локации

            self.on_enter(new_map=new_map)

    def form_mobs_team(self):
        self.mob_team = self.mobs.team_dict

    def available(self):
        return False

    @staticmethod
    def create_button(name_or_lang_tuple, member, *args, named=False):
        return DungeonButton(name_or_lang_tuple, member, *args, named=named)

    # Проверяет, можно ли производить перемещение с данной локации
    def move_permission(self, movement, call):
        bot_methods.answer_callback_query(call, 'Вы не можете здесь пройти.', alert=False)
        return self.available()

    # Функция, запускающаяся при входе в комнату. Именно сюда планируется пихать события.
    def enter(self):
        lang_tuple = self.get_greet_tuple()
        self.dungeon.party.send_message(lang_tuple, image=self.image, leader_reply=True,
                                        short_member_ui=True, reply_markup_func=self.get_action_keyboard)
        if not self.action_expected:
            self.dungeon.update_map(new=True)

    # -------- СОЗДАНИЕ КНОПОК ДЕЙСТВИЯ -------
    # get_encounter_button = [(Название действия, доступного при входе: его функция)]
    # get_idle_buttons: [(Название действия, доступного всегда: его функция)]
    # ------------------------------------------------------------------------------------------------------------------

    def get_button_list(self):
        return {
                'idle': self.get_idle_buttons(),
                'encounter': self.get_encounter_button()
                }

    def get_action_dict(self):
        action_dict = {}
        for value in self.get_button_list().values():
            for tpl in value:
                action_dict[tpl[0]] = tpl[1]
        return action_dict

    def get_idle_buttons(self):
        return list()

    def get_encounter_button(self):
        return list()

    def get_action_keyboard(self, member):
        buttons = self.get_button_list()['encounter']
        print(buttons)
        if buttons:
            buttons = [(self.get_button_tuples(member.lang)[str(button[0])], str(button[0])) for button in buttons]
            keyboard = form_keyboard(*[self.create_button(button[0], member, 'location', str(button[1]),
                                                          named=True) for button in buttons])
            self.action_expected = True
            return keyboard
        else:
            self.action_expected = False
            return

    # ------------------------------------------------------------------------------------------------------------------

    def reset_message(self, db_string, image=None, keyboard_func=True, short_member_ui=False):
        if not keyboard_func:
            keyboard_func = None
        else:
            keyboard_func = self.get_action_keyboard
        for member in self.dungeon.party.members:
            member.delete_message()
        self.dungeon.party.send_message(self.get_lang_tuple(db_string), image=image, reply_markup_func=keyboard_func,
                                        short_member_ui=short_member_ui)

    def victory(self):
        self.dungeon.party.send_message(LangTuple('dungeon', 'victory'), image=self.image,
                                        reply_markup_func=self.get_action_keyboard)

    def on_enter(self, new_map=False):
        self.dungeon.update_map(new=new_map)

    def collect_receipts(self):
        if self.receipts:
            self.dungeon.party.send_message('Вы находите следующие рецепты: {}'.format(self.receipts.to_string('rus')))
            self.dungeon.party.collected_receipts += self.receipts

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

    def location_fight(self, first_turn=None):
            results = self.dungeon.run_fight(self.dungeon.party.join_fight(), self.mob_team, first_turn=first_turn)
            self.process_fight_results(results)

    def process_fight_results(self, results):
        if not any(unit_dict['name'] == self.dungeon.party.leader.unit_dict['name'] for unit_dict in results['winners']):

                def get_exit_keyboard(mmbr):
                    keyboard = form_keyboard(DungeonButton('Покинуть карту', mmbr, 'menu', 'defeat', named=True))
                    return keyboard

                self.dungeon.party.send_message('Вы проиграли!', reply_markup_func=get_exit_keyboard)
        else:
            for member in self.dungeon.party.members:
                member.occupied = False
                member.unit_dict = [unit_dict for unit_dict in results['winners']
                                    if unit_dict['name'] == member.unit_dict['name']][0]
                member.inventory.update()
            loot = results['loot'] + self.loot
            experience = sum([units.units_dict[mob].experience for mob in self.mobs.mob_units if self.mobs is not None])
            self.dungeon.party.experience += experience
            self.dungeon.party.distribute_loot(loot)
            self.collect_receipts()
            self.victory()


class MobPack:
    def __init__(self, *args, complexity=None):
        self.mob_units = args
        self.complexity = complexity
        self.team_dict = self.generate_team()

    def generate_team(self):
        team_dict = {'marker': 'mobs'}
        i = 0
        for unit in self.mob_units:
            team_dict[(units.units_dict[unit], i)] = units.units_dict[unit](complexity=self.complexity).to_dict()
            i += 1
        return team_dict

    def get_image_tuples(self):
        for k, v in self.team_dict.items():
            if k != 'marker':
                yield units.units_dict[v['unit_name']](unit_dict=v).get_image()


class EnemyKey:
    def __init__(self, name, min_complexity, max_complexity, probability):
        self.name = name
        self.min_complexity = min_complexity
        self.max_complexity = max_complexity
        self.probability = probability

# --------------------------------------------------------------------------------------------------
# Объект группы в подземелье