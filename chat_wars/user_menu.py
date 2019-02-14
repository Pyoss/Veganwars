from bot_utils.keyboards import UserButton, form_keyboard
from bot_utils.bot_methods import send_message, edit_message, delete_message
from fight.standart_actions import object_dict, get_name
from chat_wars.buildings import building_dict
from chat_wars.chat_main import get_chat, get_user
import sys, inspect


class UserAction:
    name = None
    rus_name = None
    acting = True

    def __init__(self, user, call=None):
        self.user = user
        self.call = call

    def func(self):
        if self.acting:
            self.act()
        else:
            self.send_page()

    def act(self):
        pass

    def send_page(self):
        pass

    def button_to_page(self, name=None):
        return UserButton(self.get_name() if name is None else name, 'rus', self.name, named=True)

    def get_name(self):
        return self.rus_name


class CloseMenu(UserAction):
    name = 'close'
    rus_name = 'Закрыть'

    def act(self):
        message_id = self.call.message.message_id
        delete_message(self.call.message.chat.id, message_id)


class UserPage(UserAction):
    name = None
    rus_name = None
    parent_menu = None
    acting = False

    def __init__(self, user, call=None):
        UserAction.__init__(self, user, call)
        self.children_actions = None

    def form_actions(self):
        pass

    def get_menu_string(self):
        return None

    def get_parent_menu(self):
        return self.parent_menu(self.user)

    def get_menu_keyboard(self):
        buttons = [action.button_to_page() for action in self.children_actions]
        if self.parent_menu is not None:
            buttons.append(self.get_parent_menu().button_to_page(name='Назад'))
        return form_keyboard(*buttons)

    def send_page(self):
        self.form_actions()
        text = self.get_menu_string()
        if self.call is None:
            send_message(self.user.user_id, text, reply_markup=self.get_menu_keyboard())
        else:
            edit_message(self.user.user_id, self.call.message.message_id, text, reply_markup=self.get_menu_keyboard())


class UserMainMenu(UserPage):
    name = 'main'
    rus_name = 'Главное Меню'

    def get_menu_string(self):
        return 'Управление персонажем'

    def form_actions(self):
        self.children_actions = [
            UserSettings(self.user),
            CloseMenu(self.user)
        ]


class UserSettings(UserPage):
    name = 'settings'
    rus_name = 'Настройки'

    def get_menu_string(self):
        return 'Настройки'

    def form_actions(self):
        self.children_actions = []


class UserHandler:

    name = None

    def __init__(self, handler):
        self.handler = handler

    @staticmethod
    def handle(call):
        call_data = call.data.split('_')
        user_id = call.from_user.id
        user = get_user(user_id)
        action = call_data[1]
        user_action_dict[action](user, call).func()


user_action_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}