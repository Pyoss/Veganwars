import engine
from fight.standart_actions import to_object
from adventures import locations
import file_manager
from locales.localization import LangTuple


class TutorialEntrance(locations.OpenLocation):
    image = file_manager.my_path + '/files/images/backgrounds/tutorial_cage.jpg'
    name = 'tutorial_entrance'

    def __init__(self, x, y, dungeon, map_tuple):
        locations.OpenLocation.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '-'
        self.open = False
        self.looked = False

    def get_emote(self):
        # return '-' + str(self.complexity)
        return ' '

    def move_permission(self, movement, call):
        if not movement.end_location.available():
            self.answer_callback_query(call, "Это символ стены: Пройти тут невозможно.")
        elif not self.open and movement.end_location != self:
            self.answer_callback_query(call, 'Вы не можете двигаться дальше, пока не откроете клетку.', alert=True)
            return False
        return True

    # Функция, запускающаяся при входе в комнату. Именно сюда планируется пихать события.
    def enter(self):
        lang_tuple = self.get_greet_tuple()
        self.dungeon.party.send_message(lang_tuple, image=self.image, leader_reply=True,
                                        short_member_ui=True, reply_markup_func=self.get_action_keyboard)

        self.dungeon.party.send_message('<ℹ️Снизу Вы видите меню карты с комнатами. '
                                        '👥 обозначает локацию, где находится '
                                        'Ваша группа. Нажмите на иконку 👥 для просмотра действий, доступных в данной '
                                        'локации. Для перемещения группы нажмите на одну из соседних локаций.>')

        if not self.action_expected:
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.update_map(new=True)

    def get_idle_buttons(self):
        buttons = []
        if not self.looked:
            buttons.append(('0', self.look_around))
        return buttons

    def thrown(self, name):
        if name == 'tutorial_key':
            self.looked = False

    def look_around(self, call):
        self.reset_message('text_1')
        self.looked = True
        for member in self.dungeon.party.members:
            member.message_id = None
            member.add_item('tutorial_key')
        self.dungeon.party.member_dict[call.from_user.id].member_menu_start()


class TutorialSecondLoc(locations.OpenLocation):
    image = file_manager.my_path + '/files/images/backgrounds/tutorial_cage.jpg'
    name = 'tutorial_secondloc'

    def __init__(self, x, y, dungeon, map_tuple):
        locations.OpenLocation.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '-'
        self.containers_dict['box'] = engine.Container(name_lang_tuple=self.get_lang_tuple('text_3'))
        self.containers_dict['box'].put(to_object('bandages'))
        self.last_attempt = 1

    def enter(self):
        if not self.visited:
            lang_tuple = self.get_greet_tuple()
            self.dungeon.party.send_message(lang_tuple, image=self.image, leader_reply=True,
                                            short_member_ui=True, reply_markup_func=self.get_action_keyboard)
            self.dungeon.party.send_message('<ℹ️У вашего персонажа есть жизни, энергия, усталость, '
                                            'и скрытые параметры, зависящие от экипировки и уровня.>')
        if not self.action_expected:
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.update_map(new=True)

    def get_emote(self):
        # return '-' + str(self.complexity)
        if not self.visited:
            return '❓'
        else:
            return ' '

    def get_idle_buttons(self):
        buttons = []
        buttons.append(('0', self.search_box))
        return buttons

    def fill_box(self, attempt_number):
        self.containers_dict['box'].put(to_object('bandages'))*2    
        if attempt_number == 2:
            self.containers_dict['box'].put(to_object("spear"))
        elif attempt_number == 3:
            self.containers_dict['box'].put(to_object("shield"))

    def search_box(self, call):
        if self.last_attempt != self.dungeon.map.goblin_attempt:
            self.last_attempt = self.dungeon.map.goblin_attempt
            self.fill_box(self.dungeon.map.goblin_attempt)
        self.open_container('box', member=self.dungeon.party.member_dict[call.from_user.id])


class TutorialEnemyLoc(locations.OpenLocation):
    name = 'tutorial_enemy'
    impact = 'negative'
    impact_integer = 1
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    image_file = file_manager.my_path + '/files/images/backgrounds/tutorial_cage.jpg'
    standard_mobs = True

    def __init__(self, x, y, dungeon, map_tuple):
        locations.OpenLocation.__init__(self, x, y, dungeon, map_tuple)

    def get_greet_tuple(self):
        if self.dungeon.map.goblin_attempt:
            return LangTuple(self.table_row, 'greeting')
        else:
            return LangTuple(self.table_row, 'text_1')

    def get_emote(self):
        # return '-' + str(self.complexity)
        if not self.visited:
            return '❓'
        elif not self.cleared:
            return '👹'
        else:
            return ''

    def get_encounter_button(self):
        buttons = []
        if not self.cleared:
            buttons.append(('0', self.go_away))
            buttons.append(('1', self.start_fight))
        return buttons

    def start_fight(self, call, **kwargs):
        self.erase_keyboard(call)
        locations.OpenLocation.fight(self, attempt=self.dungeon.map.goblin_attempt, **kwargs)

    def go_away(self, call):
        self.reset_message('text_6', image=self.mob_image, keyboard_func=False)
        for member in self.dungeon.party.members:
            member.occupied = False
        self.dungeon.party.move(self.entrance_location, new_message=True, exhaust=False, events=False)

    def enter(self):
        lang_tuple = self.get_greet_tuple()
        actions_keyboard = self.get_action_keyboard
        image = self.mob_image
        self.dungeon.party.send_message(lang_tuple, image=image,
                                        reply_markup_func=actions_keyboard, leader_reply=True, short_member_ui=True)

    def victory(self):
        self.cleared = True
        self.reset_message('text_3', image=self.image)
        self.dungeon.map.exit_opened = True
        self.dungeon.update_map(new=True)

    def defeat(self):
        self.dungeon.map.goblin_attempt += 1
        self.reset_message('text_5', keyboard_func=False)
        for member in self.dungeon.party.members:
            member.occupied = False
        self.dungeon.party.move(self.entrance_location, new_message=True, exhaust=False, events=False)
