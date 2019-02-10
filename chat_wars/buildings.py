from locales.localization import LangTuple
from bot_utils.keyboards import form_keyboard, ChatButton
from locales.emoji_utils import emote_dict
from bot_utils.bot_methods import send_message, edit_message
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

    def send_menu(self, user, chat, message_id):
        buttons = []
        build_string = 'Построить'
        if self.name not in chat.available_buildings() or chat.resources <= self.get_price(chat):
            build_string = emote_dict['locked_em'] + build_string
        buttons.append(ChatButton(build_string, 'rus', 'build', 'make', self.name, named=True))
        buttons.append(ChatButton('Назад', 'rus', 'menu', named=True))
        edit_message(user.user_id, message_id,
                          self.get_string('desc').translate('rus'), reply_markup=form_keyboard(*buttons))


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