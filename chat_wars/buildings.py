from locales.localization import LangTuple
import inspect, sys


class Building:
    name = None
    default_price = 100
    max_lvl = 3

    def __init__(self):
        pass

    def get_string(self, string_action, format_dict=None):
        return LangTuple('buildings_' + self.name, string_action, format_dict=format_dict)

    @staticmethod
    def can_build(chat):
        return True

    def get_price(self, chat):
        return Building.default_price * (chat.construction_lvl() + 1)


class Wall(Building):
    name = 'wall'


class Barrack(Building):
    name = 'barracks'


class Treasury(Building):
    name = 'treasury'


class Smith(Building):
    name = 'smith'

building_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}