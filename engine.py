
import random
import uuid
import json
from fight import standart_actions


class Container:
    def __init__(self, base_dict=None, base_list=None):
        self.base_dict = {} if base_dict is None else base_dict
        # Структура контейнера {случайный_айди: (словарь_предмета, количество)}
        if base_list is not None:
            [self.put(item) for item in base_list]

    def __getitem__(self, item_id):
        return self.base_dict[int(item_id)]

    def __add__(self, other):
        for item_id in other.base_dict:
            item, value = other[item_id][0], other[item_id][1]
            self.put(item, value=value)
        return self

    def __iadd__(self, other):
        return self.__add__(other)

    def keys(self):
        return self.base_dict.keys()

    def put(self, item, value=1):
        if isinstance(item, str):
            item = standart_actions.object_dict[item]().to_dict()
        self.__change__(item, value)
        return True

    def remove(self, item, value=1):
        if isinstance(item, int):
            item_id = item
        elif item.isdigit():
            item_id = int(item)
        else:
            item_id = self.get_id(item)
        if self.base_dict[item_id][1] == 'inf':
            return True
        elif self.base_dict[item_id][1] >= value:
            self.__change__(self.base_dict[item_id][0], -value)
            return True
        return False

    def __change__(self, item, value):
        item_id = self.get_id(item, value)
        if item_id:
            self.base_dict[item_id][1] += value
            if self.base_dict[item_id][1] <= 0:
                del self.base_dict[item_id]
        else:
            self.base_dict[rand_id()] = [item, value]

    def get_id(self, item, value=1):
        test = list([k for k, v in self.base_dict.items() if v[0] == item and v[1] >= value])
        if not test:
            return False
        else:
            item_id = test[0]
            return item_id

    def empty(self):
        if not self.base_dict:
            return True
        return False

    def random_split(self, number):
        new_containers = []
        for i in range(number):
            new_containers.append(Container())
        while not self.empty():
            for container in new_containers:
                item_id = random.choice(list(self.base_dict.keys()))
                container.put(self[item_id][0])
                self.remove(item_id)
                if self.empty():
                    break
        return new_containers

    def get_string(self, item_id, lang):
        item = self.base_dict[item_id]
        string = standart_actions.object_dict[item[0]['name']]().name_lang_tuple().translate(lang)
        if item[1] > 1:
            string += ' (' + str(item[1]) + ')'
        return string

    def to_string(self, lang):
        base_string = ', '.join([self.get_string(key, lang) for key in self.base_dict.keys()])
        if base_string:
            return base_string
        else:
            return 'Пусто.'

    def to_json(self):
        return json.dumps(self.base_dict)

    def from_json(self, json_dict):
        self.base_dict = json.loads(json_dict)
        return self

    def get_item_object(self, item_id, item_name=None, unit=None):
        if item_id == 'weapon':
            item_dict = self.member['weapon']
        elif item_id == 'armor':
            item_dict = next(item_dict for item_dict in self.member['armor'] if item_dict['name'] == item_name)
        else:
            item_dict = self[item_id][0]
        return standart_actions.object_dict[item_dict['name']](unit=unit, obj_dict=item_dict)

    def fight_list(self, unit):
        fight_list = []
        for key in self.base_dict.keys():
            item = self.get_item_object(key)
            if 'fight' in item.core_types:
                for i in range(self.base_dict[key][1]):
                    fight_list.append(self.get_item_object(key, unit=unit))
        return fight_list

    def inv_list(self, unit):
        inv_list = []
        for key in self.base_dict.keys():
            item = self.get_item_object(key)
            if 'fight' not in item.core_types:
                for i in range(self.base_dict[key][1]):
                    inv_list.append(self.get_item_object(key, unit=unit))
        return inv_list


class ReceiptsContainer(Container):

    def put(self, item, value=1):
        self.__change__(item, value)
        return True

    def __change__(self, item, value):
        if value == 'inf':
            self.base_dict[item] = value
            return True
        self.base_dict[item] += value
        if self.base_dict[item] <= 0:
            del self.base_dict[item]
        else:
            self.base_dict[item] = value

    def remove(self, item, value=1):
        print(self.base_dict)
        if self.base_dict[item] == 'inf':
            return True
        elif self.base_dict[item] >= value:
            self.__change__(item, -value)
            return True
        return False


def throw_dice(cap: int):
    return random.randint(1, cap)


def damage_roll(dice_num: int, bonus: int):
    damage = 0
    current_dice = 0
    while current_dice != dice_num:
        x = throw_dice(10)
        if x + bonus > 10:
            damage += 1
        current_dice += 1
    return damage


def roll_chance(chance: int):
    if chance > random.randint(1, 100):
        return True
    return False


def rand_id():
    return uuid.uuid4().int >> 112
