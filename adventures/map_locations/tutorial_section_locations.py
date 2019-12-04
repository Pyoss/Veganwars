from adventures import locations
import file_manager


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
        if not self.open and movement.end_location != self:
            self.answer_callback_query(call, 'Вы не можете двигаться дальше, пока не откроете клетку.', alert=True)
            return False
        return True

    def get_idle_buttons(self):
        buttons = []
        if not self.looked:
            buttons.append(('0', self.look_around))
        elif not self.key_taken:
            buttons.append(('1', self.take_key))
        return buttons

    def look_around(self):
        pass

    def take_key(self):
        pass
