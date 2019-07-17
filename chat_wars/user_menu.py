from bot_utils.keyboards import UserButton
from bot_utils.bot_methods import answer_callback_query
from fight.abilities import ability_dict
from chat_wars.chat_main import get_user
from chat_wars.chat_menu import MenuPage, MenuAction, CloseMenu
import sys, inspect


class UserAction(MenuAction):
    def __init__(self, user, user_id, call=None):
        MenuAction.__init__(self, user, user_id, call=call)
        self.user = user
        self.button_type = UserButton

    def button_to_page(self, name=None):
        return self.button_type(self.get_name() if name is None else name, 'rus', self.name, named=True)


class UserPage(MenuPage):
    def __init__(self, user, user_id, call=None):
        MenuAction.__init__(self, user, user_id, call=call)
        self.user = user
        self.button_type = UserButton

    def button_to_page(self, name=None):
        return self.button_type(self.get_name() if name is None else name, 'rus', self.name, named=True)


class UserMainMenu(UserPage):
    name = 'main'
    rus_name = 'Главное Меню'

    def get_menu_string(self):
        return 'Управление персонажем\n' \
               'Текущий опыт: {}/{}\n'.format(self.user.experience, self.user.get_experience_to_lvl())

    def form_actions(self):
        self.children_actions = [
            UserSettings(self.user, self.user_id),
            CloseMenu(self.user, self.user_id)
        ]
        if self.user.get_possible_abilities_amount():
            self.children_actions.append(LVLUP(self.user, self.user_id))


class LVLUP(UserPage):
    name = 'lvlup'
    rus_name = 'Уровень'
    parent_menu = UserMainMenu

    def get_menu_string(self):
        return 'Выберите новую способность:'

    def form_actions(self):
        self.children_actions = []
        for ability in possible_abilities:
            self.children_actions.append(UserAbilityMenu(self.user, self.user_id, ability=ability()))


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
        user_action_dict[action](user, user_id, call).func()

# --------------------------- Прокачка -------------------------- #


class UserAbilityMenu(UserPage):
    name = 'ability-menu'
    rus_name = 'Цель'
    parent_menu = UserMainMenu

    def __init__(self, user, user_id, call=None, ability=None):
        UserPage.__init__(self, user, user_id, call=call)
        if ability is None:
            self.ability = ability_dict[(call.data.split('_')[-1])]()
        else:
            self.ability = ability
        self.ability_name = self.ability.name_lang_tuple().translate('rus')

    def form_actions(self):
        self.children_actions = [UserGetAbility(self.user, self.user_id, ability=self.ability)]

    def get_menu_string(self):
        return 'Способность {}\n---------------------\n{}'.format(self.ability_name, self.ability.lang_tuple('desc').
                                                                  translate('rus'))

    def button_to_page(self, name=None):
        return UserButton(self.ability_name, 'rus', self.name, self.ability.name, named=True)


class UserGetAbility(UserAction):
    name = 'get-ability'
    rus_name = 'Способности'

    def __init__(self, user, user_id, call=None, ability=None):
        UserAction.__init__(self, user, user_id, call=call)
        if ability is None:
            self.ability = ability_dict[(call.data.split('_')[-1])]()
        else:
            self.ability = ability

    def act(self):
        available_abilities = self.user.get_possible_abilities_amount()
        if available_abilities:
            if not any(self.ability.name == ability['name'] for ability in self.user.get_abilities()):
                self.user.add_ability(self.ability)
                answer_callback_query(self.call, 'Вы приобретаете способность "{}"'.format(self.ability.name_lang_tuple().translate('rus')))
            else:
                answer_callback_query(self.call, 'У вас уже есть эта способность!'.format(self.ability.name_lang_tuple().translate('rus')))

        else:
            answer_callback_query(self.call, 'что-то пошло не так')

    def button_to_page(self, name=None):
        return UserButton('Взять', 'rus', self.name, self.ability.name, named=True)



# --------------------------- классы -------------------------- #

possible_abilities = [ability_dict['dodge']]
user_action_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}