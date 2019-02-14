from bot_utils.keyboards import ChatButton, form_keyboard
from bot_utils.bot_methods import send_message, edit_message, delete_message
from fight.standart_actions import object_dict, get_name
from chat_wars.buildings import building_dict
from chat_wars.chat_main import get_chat, get_user
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
    name = 'close'
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

    def get_parent_menu(self):
        return self.parent_menu(self.chat, self.user_id)

    def get_menu_keyboard(self):
        buttons = [action.button_to_page() for action in self.children_actions]
        if self.parent_menu is not None:
            buttons.append(self.get_parent_menu().button_to_page(name='Назад'))
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
            AttackMenu(self.chat, self.user_id),
            ArsenalMenu(self.chat, self.user_id),
            BuildingListMenu(self.chat, self.user_id),
            CloseMenu(self.chat, self.user_id)
        ]


# -------------------------------------- ВЕТКА АРСЕНАЛА
class ArsenalMenu(MenuPage):
    name = 'arsenal'
    rus_name = 'Арсенал'
    parent_menu = MainMenu

    def form_actions(self):
        self.children_actions = [CraftMenu(self.chat, self.user_id)]

    def get_menu_string(self):
        return 'Арсенал чата {}'.format(self.chat.name)


class CraftMenu(MenuPage):
    name = 'craft'
    rus_name = 'Крафт'
    parent_menu = ArsenalMenu

    def form_actions(self):
        self.children_actions = []
        receipts = self.chat.get_receipts()
        for key in receipts.keys():
            self.children_actions.append(ReceiptMenu(self.chat, self.user_id, item_name=key))

    def get_menu_string(self):
        return 'Крафт чата {}'.format(self.chat.name)


class ReceiptMenu(MenuPage):
    name = 'receipt'
    rus_name = 'Рецепт'
    parent_menu = CraftMenu

    def __init__(self, chat, user_id, call=None, item_name=None):
        MenuPage.__init__(self, chat, user_id, call=call)
        if item_name is None:
            self.item_name = call.data.split('_')[-1]
        else:
            self.item_name = item_name

    def form_actions(self):
        self.children_actions = [CraftItemAction(self.chat, self.user_id)]

    def get_item_object(self):
        return building_dict[self.item_name]

    def get_name(self):
        return get_name(self.get_item_object().name, 'rus')

    def get_menu_string(self):
        return self.get_name()

    def button_to_page(self, name=None):
        return ChatButton(self.get_name() if name is None else name, 'rus', self.name, self.item_name, named=True)


class CraftItemAction(ChatAction):
    name = 'craft_item'
    rus_name = 'Создать'


# -------------------------------------- ВЕТКА НАПАДЕНИЯ
class AttackMenu(MenuPage):
    name = 'attack-list'
    rus_name = 'Атака'
    parent_menu = MainMenu

    def form_actions(self):
        self.children_actions = []
        chats = self.chat.get_target_chats()
        for chat in chats:
            self.children_actions.append(TargetMenu(self.chat, self.user_id, target_chat=chat))

    def get_menu_string(self):
        return 'Выберите чат для атаки.'


class TargetMenu(MenuPage):
    name = 'target-menu'
    rus_name = 'Цель'
    parent_menu = AttackMenu

    def __init__(self, chat, user_id, call=None, target_chat=None):
        MenuPage.__init__(self, chat, user_id, call=call)
        if target_chat is None:
            self.target_chat = get_chat(call.data.split('_')[-1])
        else:
            self.target_chat = target_chat

    def form_actions(self):
        self.children_actions = [AttackTargetAction(self.chat, self.user_id)]

    def get_menu_string(self):
        return 'Вы можете напасть на чат {}'.format(self.target_chat.name)

    def button_to_page(self, name=None):
        return ChatButton(self.target_chat.name, 'rus', self.name, self.target_chat.chat_id, named=True)


class AttackTargetAction(ChatAction):
    name = 'attack'
    rus_name = 'Напасть'


# -------------------------------------- ВЕТКА ПОСТРОЕК
class BuildingListMenu(MenuPage):
    name = 'buildings'
    rus_name = 'Постройки'
    parent_menu = MainMenu

    def get_menu_string(self):
        return 'Постройки чата {}'.format(self.chat.name)

    def form_actions(self):
        self.children_actions = []
        buildings = self.chat.available_buildings()
        for building in buildings:
            self.children_actions.append(BuildingMenu(self.chat, self.user_id, building=building))


class BuildingMenu(MenuPage):
    name = 'building-menu'
    rus_name = 'Постройка'
    parent_menu = BuildingListMenu

    def __init__(self, chat, user_id, call=None, building=None):
        MenuPage.__init__(self, chat, user_id, call=call)
        if building is None:
            self.building = building_dict[call.data.split('_')[-1]]()
        else:
            self.building = building_dict[building]()

    def form_actions(self):
        self.children_actions = [CreateBuildingAction(self.chat, self.user_id)]

    def get_menu_string(self):
        return 'Меню постройки {}'.format(self.building.get_string('name').translate('rus'))

    def button_to_page(self, name=None):
        return ChatButton(self.building.get_string('name'), 'rus', self.name, self.building.name, named=True)


class CreateBuildingAction(ChatAction):
    name = 'build'
    rus_name = 'Построить'


class ManageHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    @staticmethod
    def handle(call):
        call_data = call.data.split('_')
        user_id = call.from_user.id
        user = get_user(user_id)
        chat = user.chat
        action = call_data[1]
        chat_action_dict[action](chat, user_id, call).func()

chat_action_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}