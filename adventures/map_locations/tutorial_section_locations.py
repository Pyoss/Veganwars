from adventures import locations
import file_manager
from bot_utils import bot_methods


class TutorialEntrance(locations.OpenLocation):
    image = file_manager.my_path + '/files/images/backgrounds/tutorial_cage.jpg'
    name = 'tutorial_entrance'

    def __init__(self, x, y, dungeon, map_tuple):
        locations.OpenLocation.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '-'
        self.open = False
        self.looked = False
        self.key_taken = False

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

        self.dungeon.party.send_message('<ℹ️Снизу Вы видите меню карты с комнатами. 👥 обозначает локацию, где находится '
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
        elif not self.key_taken:
            buttons.append(('1', self.take_key))
        return buttons

    def throwed(self, name):
        if name == 'tutorial_key':
            self.looked = False
            self.key_taken = False

    def look_around(self, call):
        self.reset_message('text_1')
        self.looked = True
        for member in self.dungeon.party.members:
            member.message_id = None
        self.dungeon.party.member_dict[call.from_user.id].member_menu_start()

    def take_key(self, call):
        self.reset_message('text_2')
        self.key_taken = True
        for member in self.dungeon.party.members:
            member.message_id = None
            member.add_item('tutorial_key')
            bot_methods.send_message(member.chat_id,
                '<Вы подняли ключ. Поднятые предметы появляются у вас в инвентаре.>')

        self.dungeon.party.member_dict[call.from_user.id].member_menu_start()