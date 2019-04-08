#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random


class MapTuple:
    def __init__(self, x,y, number, complexity, *args):
        self.x = x
        self.y = y
        self.number = number
        self.complexity = complexity
        self.types = list(args)

    def __str__(self):
        return 'X'


class MapTuples(dict):
    # типы:
    # 'core' - основной коридор
    # 'branch' - ответвление
    # 'end' - конец основного коридора или ответвления
    def __init__(self, complexity, iterable, **kwargs):
        dict.__init__(self, iterable, **kwargs)
        self.complexity = complexity
        self.number = 0

    def new_tuple(self, x, y, *args):
        self[(x, y)] = MapTuple(x, y, self.number, self.complexity, *args)
        self.complexity += 1
        self.number += 1

    def get_tuple(self, x, y):
        return self[(x, y)]


def get_close_tuples(map_tuple):
    close = list()
    close.append((map_tuple[0], map_tuple[1] + 1))
    close.append((map_tuple[0], map_tuple[1] - 1))
    close.append((map_tuple[0] + 1, map_tuple[1]))
    close.append((map_tuple[0] - 1, map_tuple[1]))
    return [map_tuple for map_tuple in close if map_tuple[0] >= 0 and map_tuple[1] >= 0]


def get_connected(map_tuple, map_tuples):
    connected = list()
    for mp_tuple in get_close_tuples(map_tuple):
        if mp_tuple in map_tuples:
            connected.append(mp_tuple)
    return connected


# Создание основы карты
def generate_core(complexity, length):
    map_tuples = MapTuples(complexity, {})
    map_tuples.new_tuple(0, 0)

    # Метод для выбора координат следующей локации карты, отталкиваясь от предыдущей
    def next_tuple(prev_tuple):
        available_tuples = list()
        # Всегда в возможные прибавляются следующие координаты по оси X
        available_tuples.append((prev_tuple[0] + 1, prev_tuple[1]))

        # Проверяется возможность выбора нижнего координата по оси Y (Проверяется, не является ли координат
        # отрицательным, и не сущесвтует ли предыдущего координата по оси X с таким же значением Y
        check_tuple = (prev_tuple[0], prev_tuple[1] + 1)
        if check_tuple not in map_tuples.keys() and (prev_tuple[0] - 1, prev_tuple[1] + 1) not in map_tuples.keys():
            available_tuples.append(check_tuple)

        # Проверяется возможность выбора верхнего координата по оси Y (Проверяется, не является ли координат
        # отрицательным, и не сущесвтует ли предыдущего координата по оси X с таким же значением Y
        check_tuple = (prev_tuple[0], prev_tuple[1] - 1)
        if prev_tuple[1] > 1 and check_tuple not in map_tuples.keys() and\
                        (prev_tuple[0] - 1, prev_tuple[1] - 1) not in map_tuples.keys():
            available_tuples.append(check_tuple)

        # Случайным образом выбираются одни из доступных координат
        chosen_tuple = random.choice(available_tuples)
        return chosen_tuple

    # Добавляется новая занятая локация в соответствии с подобранными координатами
    for i in range(length):
        if i == length - 1:
            map_tuples.new_tuple(*next_tuple(list(map_tuples.keys())[-1]), 'core', 'end')
        else:
            map_tuples.new_tuple(*next_tuple(list(map_tuples.keys())[-1]), 'core')

    return map_tuples


# Метод создания нового ответвления
def generate_branch(map_tuples, length):
    possible_starts = dict()
    # Выбор точки старта нового ответвления данжа
    for map_tuple in map_tuples.keys():
        # Словарь с точками старта, привязанными к ответвляемому участку карты.
        # Словарь вместо списка чтобы иметь точку опоры для вычисления сложности
        new_starts = {}
        if 'end' not in map_tuples[map_tuple].types:
            for mp_tuple in get_close_tuples(map_tuple):
                if len(get_connected(mp_tuple, map_tuples)) == 1 and mp_tuple not in map_tuples:
                    new_starts[mp_tuple] = map_tuple
            possible_starts = {**possible_starts, **new_starts}
    branch_start = random.choice(list(possible_starts))
    # Изменение сложности ветки
    map_tuples.complexity = int(map_tuples[possible_starts[branch_start]].complexity) + random.randint(1, 5)
    map_tuples.new_tuple(branch_start[0], branch_start[1], 'branch', 'entrance')
    if len(map_tuples[possible_starts[branch_start]].types) < 2:
        map_tuples[possible_starts[branch_start]].types.append('crossroad')
    prolong_branch(map_tuples, branch_start, length)


# Метод увеличения длины ответвления
def prolong_branch(map_tuples, branch_start, length):
    i = 0
    current_end = branch_start
    while i < length:
        possible_tuples = [mp_tuple for mp_tuple in get_close_tuples(current_end)
                           if len(get_connected(mp_tuple, map_tuples.keys())) == 1]
        if not possible_tuples:
            break
        new_tuple = random.choice(possible_tuples)
        map_tuples.new_tuple(*new_tuple, 'branch')
        current_end = new_tuple
        i += 1
        if i == length:
            map_tuples[new_tuple].types.append('end')


# Визуализация карты
def visualise(map_tuples):
    map_length = max(map_tuple[0] for map_tuple in map_tuples) + 1
    map_height = max(map_tuple[1] for map_tuple in map_tuples) + 1
    map_dict = {}
    for x in range(map_length):
        for y in range(map_height):
            map_dict[(x, y)] = '0'

    for map_tuple in map_tuples:
        map_dict[map_tuple] = map_tuples[map_tuple]
    map_string = ''
    for y in range(map_height):
        for x in range(map_length):
            map_string += ' ' + map_dict[(x, y)].__str__() + ' '
        map_string += '\n'

if __name__ == '__main__':
    while True:
        tuples = generate_core(10, 10)
        visualise(tuples)