from bot_utils.keyboards import ChatButton, form_keyboard
from bot_utils.bot_methods import send_message, edit_message, delete_message
from fight.standart_actions import object_dict, get_name
import sys, inspect


class ChatAction:
    name = None
    rus_name = None
    acting = True

    def __init__(self, chat, user_id, call=None):
        self.chat = chat
        self.user_id = user_id
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
        return ChatButton(self.get_name() if name is None else name, 'rus', self.name, named=True)

    def get_name(self):
        return self.rus_name


class CloseMenu(ChatAction):
    name = 'close_menu'
    rus_name = 'Закрыть'

    def act(self):
        message_id = self.call.message.message_id
        delete_message(self.call.message.chat.id, message_id)



class MenuPage(ChatAction):
    name = None
    rus_name = None
    parent_menu = None
    acting = False

    def __init__(self, chat, user_id, call=None):
        ChatAction.__init__(self, chat, user_id, call)
        self.chat = chat
        self.children_actions = None

    def form_actions(self):
        pass

    def get_menu_string(self):
        return None

    def get_menu_keyboard(self):
        buttons = [action(self.chat, self.user_id).button_to_page() for action in self.children_actions]
        if self.parent_menu is not None:
            buttons.append(self.parent_menu(self.chat, self.user_id).button_to_page(name='Назад'))
        return form_keyboard(*buttons)

    def send_page(self):
        self.form_actions()
        text = self.get_menu_string()
        if self.call is None:
            send_message(self.user_id, text, reply_markup=self.get_menu_keyboard())
        else:
            edit_message(self.user_id, self.call.message.message_id, text, reply_markup=self.get_menu_keyboard())


class MainMenu(MenuPage):
    name = 'main'
    rus_name = 'Главное Меню'

    def get_menu_string(self):
        return 'Управление чатом {}'.format(self.chat.name)

    def form_actions(self):
        self.children_actions = [
            Attack,
            Arsenal,
            Buildings,
            CloseMenu
        ]


class Arsenal(MenuPage):
    name = 'arsenal'
    rus_name = 'Арсенал'


class Attack(MenuPage):
    name = 'attack'
    rus_name = 'Атака'


class Buildings(MenuPage):
    name = 'buildings'
    rus_name = 'Постройки'


class Craft(MenuPage):
    name = 'craft'
    rus_name = 'Крафт'
    parent_menu = Arsenal

    def form_actions(self):
        receipts = self.chat.get_receipts()
        for key in receipts.keys():
            ActionBuilder(get_name(key, 'rus'), ReceiptPage, )

class ReceiptPage(MenuPage):
    name = 'receipt'
    rus_name = 'Рецепт'

    def __init__(self, chat, user_id, call=None, item_name=None):
        MenuPage.__init__(self, chat, user_id, call=call)
        if item_name is None:
            self.item_name = call.data.split('_')[-1]
        else:
            self.item_name = item_name

    def get_item_object(self):
        return object_dict[self.item_name]

    def get_name(self):
        return get_name(self.get_item_object().name, 'rus')

chat_action_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}