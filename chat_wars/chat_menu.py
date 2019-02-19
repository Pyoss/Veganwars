from bot_utils.keyboards import ChatButton, UserButton, form_keyboard
from bot_utils.bot_methods import send_message, edit_message, delete_message, answer_callback_query
from fight.standart_actions import object_dict, get_name
from chat_wars.buildings import building_dict
from chat_wars.chat_main import get_chat, get_user
from locales.emoji_utils import emote_dict
import sys, inspect


class MenuAction:
    name = None
    rus_name = None
    acting = True

    def __init__(self, menu_object, user_id, call=None):
        self.menu_object = menu_object
        self.call = call
        self.user_id = user_id
        self.button_type = None

    def refuse(self, refuse_text):
        answer_callback_query(self.call, refuse_text)

    def func(self):
        available_result = self.available()
        if not available_result[0]:
            return self.refuse(available_result[1])
        if self.acting:
            self.act()
        else:
            self.send_page()

    def act(self):
        pass

    def available(self):
        return True, True

    def send_page(self):
        pass

    def button_to_page(self, name=None):
        return self.button_type(self.get_name() if name is None else name, 'rus', self.name, named=True)

    def get_name(self):
        return self.rus_name


class MenuPage(MenuAction):
    parent_menu = None
    acting = False

    def __init__(self, chat, user_id, call=None):
        MenuAction.__init__(self, chat, user_id, call)
        self.children_actions = None

    def form_actions(self):
        pass

    def get_menu_string(self):
        return None

    def get_parent_menu(self):
        return self.parent_menu(self.menu_object, self.user_id)

    def get_menu_keyboard(self):
        buttons = [action.button_to_page() for action in self.children_actions]
        if self.parent_menu is not None:
            buttons.append(self.get_parent_menu().button_to_page(name='Назад'))
        return form_keyboard(*buttons)

    def send_page(self):
        self.form_actions()
        text = self.get_menu_string()
        print(self.user_id)
        if self.call is None:
            send_message(self.user_id, text, reply_markup=self.get_menu_keyboard())
        else:
            edit_message(self.user_id, self.call.message.message_id, text, reply_markup=self.get_menu_keyboard())


class CloseMenu(MenuAction):
    name = 'close'
    rus_name = 'Закрыть'

    def __init__(self, menu_object, user_id, call=None):
        MenuAction.__init__(self, menu_object, user_id, call=call)
        self.button_type = UserButton

    def act(self):
        message_id = self.call.message.message_id
        delete_message(self.call.message.chat.id, message_id)


class ChatAction(MenuAction):

    def __init__(self, chat, user_id, call=None):
        MenuAction.__init__(self, chat, user_id, call=call)
        self.chat = chat
        self.button_type = ChatButton


class ChatMenuPage(MenuPage):

    def __init__(self, chat, user_id, call=None):
        MenuAction.__init__(self, chat, user_id, call=call)
        self.chat = chat
        self.button_type = ChatButton


class MainMenu(ChatMenuPage):
    name = 'main'
    rus_name = 'Главное Меню'

    def get_menu_string(self):
        return 'Управление чатом {}\n' \
               'Количество ресурсов: {}\n' \
               'Дневной доход: {}'.format(self.chat.name, self.chat.resources, self.chat.get_income())

    def form_actions(self):
        self.children_actions = [
            AttackMenu(self.chat, self.user_id),
            ArsenalMenu(self.chat, self.user_id),
            BuildingListMenu(self.chat, self.user_id),
            CloseMenu(self.chat, self.user_id)
        ]


# -------------------------------------- ВЕТКА АРСЕНАЛА
class ArsenalMenu(ChatMenuPage):
    name = 'arsenal'
    rus_name = 'Арсенал'
    parent_menu = MainMenu

    def form_actions(self):
        self.children_actions = [CraftMenu(self.chat, self.user_id)]

    def get_menu_string(self):
        return 'Арсенал чата {}'.format(self.chat.name)


class CraftMenu(ChatMenuPage):
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


class ReceiptMenu(ChatMenuPage):
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
class AttackMenu(ChatMenuPage):
    name = 'attack-list'
    rus_name = 'Атака'
    parent_menu = MainMenu

    def __init__(self, chat, user_id, call=None):
        ChatMenuPage.__init__(self, chat, user_id, call=call)
        from chat_wars.chat_war import current_war
        self.current_war = current_war

    def form_actions(self):
        self.children_actions = []
        chats = self.chat.get_target_chats()
        for chat in chats:
            self.children_actions.append(TargetMenu(self.chat, self.user_id, target_chat=chat))

    def get_menu_string(self):
        return 'Выберите чат для атаки.'

    def available(self):
        if self.current_war.stage != 'siege' and self.current_war.stage != 'attack':
            return False, 'В данный момент нападение на другой чат недоступно.'
        return True, True

    def get_name(self):
        if self.current_war.stage == 'siege':
            return 'Осада'
        elif self.current_war.stage == 'attack':
            return 'Атака'
        else:
            return emote_dict['locked_em'] + ' Атака'


class TargetMenu(ChatMenuPage):
    name = 'target-menu'
    rus_name = 'Цель'
    parent_menu = AttackMenu

    def __init__(self, chat, user_id, call=None, target_chat=None):
        ChatMenuPage.__init__(self, chat, user_id, call=call)
        if target_chat is None:
            self.target_chat = get_chat(call.data.split('_')[-1])
        else:
            self.target_chat = target_chat

    def form_actions(self):
        self.children_actions = [AttackTargetAction(self.chat, self.user_id, target_chat=self.target_chat)]

    def get_menu_string(self):
        return 'Вы можете напасть на чат {}\n' \
               'Цена атаки - {}\n' \
               'Возможный заработок - {}'.format(self.target_chat.name, self.chat.get_attack_price(self.target_chat),
                                                 self.target_chat.get_prize())

    def button_to_page(self, name=None):
        return ChatButton(self.target_chat.name, 'rus', self.name, self.target_chat.chat_id, named=True)


class AttackTargetAction(ChatAction):
    name = 'attack'
    rus_name = 'Напасть'

    def __init__(self, chat, user_id, call=None, target_chat=None):
        ChatAction.__init__(self, chat, user_id, call=call)
        if target_chat is None:
            self.target_chat = get_chat(call.data.split('_')[-1])
        else:
            self.target_chat = target_chat
        from chat_wars.chat_war import current_war
        self.current_war = current_war

    def available(self):
        if self.current_war.stage != 'siege' and self.current_war.stage != 'attack':
            return False, 'В данный момент нападение на другой чат недоступно.'
        elif self.current_war.stage == 'siege' and self.current_war.attacked_chat.get(self.chat.chat_id, False) and\
                        self.current_war.attacked_chat[self.chat.chat_id][1] >= self.chat.get_maximum_attacks():
            return False, 'Ваш чат не может больше атаковать сегодня.'
        elif self.current_war.attacked_chat.get(self.chat.chat_id, False) and\
                        self.target_chat.chat_id in self.current_war.attacked_chat[self.chat.chat_id][0]:
            return False, 'Вы уже нападали на этот чат!'
        elif self.chat.resources < self.chat.get_attack_price(self.target_chat):
            return False, 'У вас недостаточно средств для атаки.'
        elif self.current_war.stage == 'siege' and self.target_chat.chat_id in self.chat.get_current_war_data()['chats_besieged']:
            return False, 'Вы уже осадили этот чат!'
        elif self.current_war.stage == 'attack' and self.chat.chat_id in self.target_chat.get_current_war_data()['attacked_by_chats']:
            return False, 'Вы уже победили этот чат!'
        return True, True

    def button_to_page(self, name=None):
        return ChatButton('Напасть', 'rus', self.name, self.target_chat.chat_id, named=True)

    def act(self):
        if self.current_war.stage == 'siege':
            self.chat.add_resources(-self.chat.get_attack_price(self.target_chat))
            answer_callback_query(self.call,
                                  'Вы платите {} ресурсов за атаку.'.format(self.chat.get_attack_price(self.target_chat)),
                                  alert=False)
        self.chat.attack_chat(self.call, self.target_chat)


class SiegeTargetAction(ChatAction):
    name = 'besiege'
    rus_name = 'Напасть'

    def __init__(self, chat, user_id, call=None):
        ChatAction.__init__(self, chat, user_id, call=call)
        self.target_chat = get_chat(call.data.split('_')[-2])
        self.current_war_id = call.data.split('_')[-1]
        from chat_wars.chat_war import current_war
        self.current_war = current_war

    def act(self):
        if self.current_war.id != self.current_war_id:
            self.refuse('Ошибка! Вы пытаетесь воспользоваться неактуальной кнопкой!')
            delete_message(call=self.call)
        elif str(self.chat.chat_id) in self.chat.get_current_war_data()['chats_besieged']:
            self.refuse('Ошибка! Вы уже осадили этот чат!')
            delete_message(call=self.call)
        else:
            self.chat.win_siege(self.target_chat.chat_id)
            delete_message(call=self.call)


class MarauderTargetAction(ChatAction):
    name = 'marauder'
    rus_name = 'Напасть'

    def __init__(self, chat, user_id, call=None):
        ChatAction.__init__(self, chat, user_id, call=call)
        self.target_chat = get_chat(call.data.split('_')[-2])
        self.current_war_id = call.data.split('_')[-1]
        from chat_wars.chat_war import current_war
        self.current_war = current_war

    def act(self):
        if self.current_war.id != self.current_war_id:
            self.refuse('Ошибка! Вы пытаетесь воспользоваться неактуальной кнопкой!')
            delete_message(call=self.call)

        elif self.chat.chat_id in self.target_chat.get_current_war_data()['attacked_by_chats']:
            self.refuse('Ошибка! Вы уже атаковали этот чат!')
            delete_message(call=self.call)
        else:
            self.chat.marauder(self.target_chat.chat_id)
            delete_message(call=self.call)


# -------------------------------------- ВЕТКА ПОСТРОЕК

class BuildingListMenu(ChatMenuPage):
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


class BuildingMenu(ChatMenuPage):
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
        if not chat.is_admin(user_id):
            answer_callback_query(call, 'Вы не админ в этом чате!')
            return False
        chat_action_dict[action](chat, user_id, call).func()

chat_action_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}