
import sqlite3
from locales import emoji_utils
from random import choice
import string


eng = 'D:/YandexDisk/Veganwars/Veganwars/locales/en_US/locale_en.sql'
rus = 'D:/YandexDisk/Veganwars/Veganwars/locales/ru_RU/locale_ru.sql'
lang_dict = {'rus': rus, 'eng': eng}
emote_dict = emoji_utils.emote_dict
encryption_name = 'shadow'


def get_string(lang_tuple, lang):
    # Сбор сведений о игроке
    db = lang_dict[lang]
    db = sqlite3.connect(db)
    table = lang_tuple.table
    string_id = lang_tuple.row
    cursor = db.cursor()
    try:
        cursor.execute(
            'SELECT * FROM {} WHERE id=?'.format(table), (string_id,)
        )
    except sqlite3.OperationalError and sqlite3.InterfaceError:
        print(str(table) + str(string_id))
    try:
        names = list(map(lambda x: x[0], cursor.description))
    except TypeError:
        print(str(table) + str(string_id))
    string_data = cursor.fetchone()
    db.close()
    try:
        string_data = dict(zip(names, string_data))
    except TypeError:
        raise Exception(table, string_id)
    return string_data


class LangTuple:
    def __init__(self, table_row, tuple_string, format_dict=None):
        table_row = table_row.split('_', maxsplit=1)
        self.table = table_row[0]
        if len(table_row) > 1:
            self.row = table_row[1]
            self.string = tuple_string
        else:
            self.row = tuple_string
            self.string = 'name'
        self.format_dict = {} if format_dict is None else format_dict

    def str(self, lang):
        string_data = get_string(self, lang)
        tuple_string = string_data[self.string]
        return self.format(tuple_string, lang)

    def translate(self, lang):
        return self.str(lang)

    def format(self, my_string, lang):
        # Переменная шифрования сообщений
        encrypting = False

        # Поиск списка форматируемых фраз для выделения эмодзи
        try:
            format_list = [tup[1] for tup in string.Formatter().parse(my_string) if tup[1] is not None]
        except TypeError:
            raise Exception(my_string, self.table, self.row, self.string)
        except ValueError:
            raise Exception(my_string, self.table, self.row, self.string)
        format_dict = dict(self.format_dict)
        for key in format_dict:

            # Проверка на шифрование
            if 'actor' in format_dict:
                if isinstance(format_dict['actor'], LangTuple):
                    if format_dict['actor'].row == encryption_name:
                        encrypting = True

            # Перевод LangTuple, содержащихся в словаре форматирования
            if isinstance(format_dict[key], LangTuple):
                translated = format_dict[key].translate(lang)
                format_dict[key] = translated

        # Добавление словаря эмодзи к общему словарю
        if any('_em' in tup for tup in format_list):
            multi_dict = dict()
            for tup in format_list:
                if '_em*' in tup and tup not in emote_dict:
                    split_data = tup.split('*')
                    multiplier = split_data[-1]
                    if multiplier.isdigit():
                        multiplier = int(multiplier)
                    else:
                        multiplier = int(format_dict[multiplier])
                    emote = split_data[0]
                    multi_dict[tup] = emote_dict[emote]*multiplier
            my_string = my_string.format(**emote_dict, **format_dict, **multi_dict)
            if encrypting:
                my_string = self.encrypt(my_string)
            return my_string

        # Форматирование строки
        elif format_dict:
            my_string = my_string.format(**format_dict)
            if encrypting:
                my_string = self.encrypt(my_string)
            return my_string
        else:
            return my_string

    def encrypt(self, my_string):
        marks = list(map(chr, range(768, 879)))
        words = my_string.split()
        en_words = enumerate(words)
        new_string_list = []
        for i, word in en_words:
            for c in word:
                if c in emoji_utils.emote_dict.values():
                    new_string_list.append(choice(list(emoji_utils.emote_dict.values())))
                elif c == '|':
                    new_string_list.append(c)
                else:
                    c = choice(string.ascii_letters)
                    new_string_list.append(c + ''.join(choice(marks) for _ in range(20)) * c.isalnum())
            new_string_list.append(' ')
        return ''.join(new_string_list)


class StringArray:
    def __init__(self, *args):
        self.tuples = []
        self.result_dict = {}
        self.active = False
        self.add(*args)

    def row(self, *args):
        self.add(*args)
        self.tuples.append('\n')

    def add(self, *args):
        for arg in args:
            self.tuples.append(arg)
            self.active = True

    def clear(self):
        self.tuples = []
        self.result_dict = {}
        self.active = False

    def translate(self, lang):
        def parse(string_tuple, language):
            if isinstance(string_tuple, str):
                return string_tuple
            return string_tuple.translate(language)
        text = ' '.join([parse(string_tuple, lang) for string_tuple in self.tuples])
        text = text.replace('\n ', '\n')
        self.result_dict[lang] = text
        return text

    def construct(self):
        for lang in lang_dict:
            self.translate(lang)

    def __iadd__(self, other):
        self.row(other)
        return self

    def __getitem__(self, item):
        return self.result_dict[item]


class GameString(StringArray):
    def __init__(self, fight):
        StringArray.__init__(self)
        self.fight = fight
        self.effect_done = False

    def effect(self):
        if not self.effect_done:
            self.row('\n', LangTuple('fight', 'effects', {'turn_number': self.fight.turn}))
            self.effect_done = True

    def construct(self):
        for lang in self.fight.langs:
            self.translate(lang)
        self.effect_done = False


class PlayerString(StringArray):
    def __init__(self, player):
        StringArray.__init__(self)
        self.player = player

    def construct(self):
        self.translate(self.player.lang)
        return self.result_dict[self.player.lang]

    def form_translation_dict(self, *args):
        self.row(*args)
        return self.construct()


class Block:
    def __init__(self, block_str, fight):
        self.block_str = block_str
        self.fight = fight

    def act(self):
        return LangTuple('fight', self.block_str, {'turn_number': self.fight.turn})


class FightString(StringArray):
    def __init__(self, fight):
        StringArray.__init__(self)
        self.fight = fight
        self.blocks = []

    def row(self, *args):
        self.add(*args)
        self.tuples.append('\n')

    def add(self, *args):
        for arg in args:
            self.tuples.append(arg)
            self.active = True

    def block(self, blk_str):
        self.tuples = [*self.tuples, Block(blk_str, self.fight)]

    def clear(self):
        self.tuples = []
        self.blocks = []
        self.result_dict = {}
        self.active = False

    def translate(self, lang):
        def parse(string_tuple, language):
            if isinstance(string_tuple, str):
                return string_tuple
            elif isinstance(string_tuple, Block):
                if string_tuple == self.tuples[-1] \
                or isinstance(self.tuples[self.tuples.index(string_tuple) + 1], Block):
                    return ''
                else:
                    return '\n' + string_tuple.act().translate(language) + '\n'
            return string_tuple.translate(language)
        text = ' '.join([parse(string_tuple, lang) for string_tuple in self.tuples])
        text = text.replace('\n ', '\n')
        self.result_dict[lang] = text
        return text

    def construct(self):
        for lang in self.fight.langs:
            self.translate(lang)

    def __iadd__(self, other):
        self.row(other)
        return self

    def __getitem__(self, item):
        return self.result_dict[item]


def translate(*args, lang=None):
    if lang is None:
        raise Exception('Language is not chosen.')
    my_string = StringArray(*args)
    return my_string.translate(lang)



