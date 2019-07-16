from adventures import map_engine
from locales import emoji_utils, localization
from fight import fight_main, ai, items, units, armors, standart_actions
import locales.localization
from image_generator import create_dungeon_image
from bot_utils import bot_methods, keyboards
import random
import inspect
import sys
import engine
import threading
import time

victory_image = 'D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\\victory.jpg'


class OpenLocation(map_engine.Location):

    def move_permission(self, movement, call):
        return self.available()

    def available(self):
        return True

    def get_emote(self):
        return self.default_emote


class PlaceHolder(OpenLocation):
    name = 'default_corridor'


class PlaceHolderPos(OpenLocation):
    name = 'default_corridor_positive'
    impact = 'positive'
    impact_integer = 10
    image = 'AgADAgAD7aoxG86k0UvHW9xX2r__8LxVUw8ABCxD1LsgKx-3bS4EAAEC'

    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '+' + str(self.complexity)


class PlaceHolderNeg(OpenLocation):
    name = 'default_corridor_negative'
    impact = 'negative'
    impact_integer = 10

    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '-' + str(self.complexity)


class End(OpenLocation):
    name = 'default_end'
    emote = '⚔'
    image = 'AgADAgADvKoxG2wBsUvh5y6JbSyZmUNqXw8ABHPt9rOstNKjRZ8FAAEC'

    def __init__(self, x, y, dungeon, map_tuple, special='0'):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)


class DeadEnd(OpenLocation):
    name = 'default_branch_end'

    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = 'X'


class CrossRoad(OpenLocation):
    name = 'default_crossroad'
    emote = emoji_utils.emote_dict['crossroad_em']

    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '+'


class Entrance(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '-'

    def greet_party(self):
        pass


class Smith(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = emoji_utils.emote_dict['smith_em']
        self.visited_emote = emoji_utils.emote_dict['smith_em']
        self.greet_msg = 'Тут возможно улучшить оружие или броню.'
        self.used_units = []

    def buttons(self, member):
        button = dict()
        button['name'] = 'Кузница'
        button['act'] = 'choice'
        return [button] if member.chat_id not in self.used_units else list()

    def handler(self, call):
        member = self.dungeon.party.member_dict[call.from_user.id]
        data = call.data.split('_')
        action = data[3]
        if action == 'choice':
            self.send_choice(member)
        if action == 'improve':
            self.improve(call, member, data[-1])

    def send_choice(self, member):
        text = 'Выберите предмет, который хотите улучшить'
        buttons = []
        valid_items = [item for item in member['inventory'] if 'improved' in item.keys()]
        if 'improved' in member['weapon']:
            valid_items.append(member['weapon'])
        for item in valid_items:
            if not item['improved']:
                buttons.append(keyboards.DungeonButton(member.inventory.get_item_name(item, member.lang), member,
                                                       'location',
                                                       'improve',
                                                       item['id'], named=True))
        buttons.append(keyboards.DungeonButton('Закрыть', member, 'menu', 'main', named=True))
        keyboard = keyboards.form_keyboard(*buttons)
        member.edit_message(text, reply_markup=keyboard)

    def improve(self, call, member, item_id):
        if member.chat_id not in self.used_units:
            member.inventory[item_id]['improved'] += 2
            member.alert('Вы улучшили предмет', call)
            self.used_units.append(member.chat_id)
            member.member_menu()


class FireBlocked(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = 'ts'
        self.entrance_loc = None

    def move_permission(self, movement, call):
        if self.entrance_loc is None:
            self.entrance_loc = movement.start_location
            return True
        elif movement.end_location != self.entrance_loc and movement.end_location != self:
            if not any('torch' in member.inventory.items() for member in movement.party.members):
                bot_methods.answer_callback_query(call, 'У вас нет факела, чтобы пройти дальше', alert=True)
                return False
        return True


class MobLocation(OpenLocation):
    name = 'mobs'
    emote = '!!!'
    image = './files/images/backgrounds/default.jpg'
    impact = 'negative'
    impact_integer = 10
    standard_mobs = True


class LoseLoot(OpenLocation):
    name = 'lose_loot'
    emote = emoji_utils.emote_dict['loose_loot_em']
    greet_msg = 'Вас обдирает налоговая.'

    def on_enter(self):
        if not self.visited:
            victims = [member for member in self.dungeon.party.members if not member.inventory.is_empty()]
            if victims:
                victim = random.choice(victims)
                item = random.choice(victim.inventory.items())
                victim.inventory.remove(item)
                self.dungeon.party.send_message(victim.name + ' потерял ' + str(standart_actions.get_name(item[0]['name'], 'rus')))
            else:
                pass
            self.dungeon.update_map(new=True)
        else:
            self.dungeon.update_map()


class LootRoom(OpenLocation):
    greet_msg = 'текст-комнаты-с-лутом'
    image = 'AgADAgADCqoxG5L9kUtxN8Z8SC03ibyeOQ8ABCxbztph9fIoZfIAAgI'

    def __init__(self, x, y, dungeon, map_tuple, special='0'):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = emoji_utils.emote_dict['kaaba_em']

    def on_enter(self):
        if not self.visited:
            self.dungeon.delete_map()
            found_loot = [standart_actions.object_dict[item]().to_dict() for item in self.dungeon.map.low_loot]
            self.dungeon.party.distribute_loot(*random.choices(found_loot, k=2))
        self.dungeon.update_map()


class ForestPos(OpenLocation):
    name = 'forest_location_pos'
    impact = 'positive'
    impact_integer = 10
    image = 'AgADAgAD_KoxG1CdAAFIm-eZ0wit0YWKalMPAATfxBW7BgpJ7CxdBAABAg'

    def get_emote(self):
        return '+' + str(self.complexity)


class ForestNeg(OpenLocation):
    name = 'forest_location_neg'
    impact = 'negative'
    impact_integer = 1
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    standard_mobs = True

    def get_emote(self):
        return '-' + str(self.complexity)

    def get_button_list(self):
        if self.state == 'entrance':
            return [('Осмотреться', 'scout'),
                    ('Пройти', 'rush')]
        elif self.state == 'scouted':
            return [('Выйти', 'map')]
        elif self.state == 'rushed':
            return [('Выйти', 'map')]

    def handler(self, call):
        bot_methods.err(call.data)
        data = call.data.split('_')
        action = data[3]
        if action == 'map':
            bot_methods.bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.update_map(new=True)
        elif action == 'scout':
            self.state = 'scouted'
            self.reset_message(self.image, 'text_1')
        elif action == 'rush':
            self.state = 'rushed'
            image = create_dungeon_image('D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\dark_forest.jpg', self.mobs.get_image_tuples())
            self.reset_message(image, 'text_2', keyboard_func=None)
            self.fight()
        elif action == 'victory':
            self.state = 'scouted'
            self.reset_message(self.image, 'text_1')


class ForestGob(OpenLocation):
    name = 'forest_goblin_trap'
    impact = 'negative'
    impact_integer = 1
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    image_file = './files/images/backgrounds/dark_forest_1.jpg'
    standard_mobs = True

    def get_emote(self):
        # return '-' + str(self.complexity)
        if not self.visited:
            return '❓'
        elif not self.cleared:
            return '👹'
        else:
            return ''

    def get_button_list(self):
        if self.state == 'entrance':
            return [(0, 'scout'),
                    (1, 'rush')]
        elif self.state == 'scouted':
            return [(2, 'attack'),
                    (3, 'back')]
        elif self.state == 'rushed' or self.state == 'attacked':
            return [(4, 'map')]

    def handler(self, call):
        bot_methods.err(call.data)
        data = call.data.split('_')
        action = data[3]
        if action == 'map':
            bot_methods.bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.update_map(new=True)
        elif action == 'scout':
            self.state = 'scouted'
            self.dungeon.party.exhaust()
            self.reset_message('text_1', image=self.mob_image, short_member_ui=True)
        elif action == 'rush':
            self.state = 'rushed'
            self.reset_message('text_2', image=self.mob_image, keyboard_func=None)
            self.fight(first_turn='mobs')
        elif action == 'attack':
            self.state = 'attacked'
            self.reset_message('text_5', image=self.mob_image, keyboard_func=None)
            self.fight()
        elif action == 'back':
            self.reset_message('text_6', image=self.mob_image, keyboard_func=None)
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.party.move(self.entrance_location, new_map=True, advance=False)

    def get_greet_tuple(self):
        if self.state == 'scouted':
            return localization.LangTuple(self.table_row, 'text_4')
        else:
            return localization.LangTuple(self.table_row, 'greeting')

    def enter(self):
        lang_tuple = self.get_greet_tuple()
        actions_keyboard = self.get_action_keyboard
        if self.state == 'scouted':
            image = self.mob_image
        else:
            image = self.image
        self.dungeon.party.send_message(lang_tuple, image=image,
                                        reply_markup_func=actions_keyboard, leader_reply=True, short_member_ui=True)

    def victory(self):
        self.cleared = True
        self.reset_message('text_3', image=self.image)


class ForestGobTotem(OpenLocation):
    name = 'forest_goblin_totem'
    impact = 'negative'
    impact_integer = 1
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    standard_mobs = True

    def get_emote(self):
        return '-' + str(self.complexity)

    def get_button_list(self):
        if self.state == 'entrance':
            return [('Подкрасться', 'sneak'),
                    ('Напасть', 'attack')]
        elif self.state == 'sneaked':
            return [('Напасть', 'sneak_attack'),
                    ('Пройти дальше', 'leave')]

    def handler(self, call):
        bot_methods.err(call.data)
        data = call.data.split('_')
        action = data[3]
        if action == 'map':
            bot_methods.bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
            for member in self.dungeon.party.members:
                member.occupied = False
            self.dungeon.update_map(new=True)
        elif action == 'sneak':
            if engine.roll_chance(50):
                self.state = 'sneaked'
                for member in self.dungeon.party.members:
                    member.delete_message()
                self.dungeon.party.send_message(self.get_lang_tuple('text_1'), image=self.image, reply_markup=self.get_action_keyboard())
            else:
                self.state = 'attacked'
                for member in self.dungeon.party.members:
                    member.delete_message()
                image = create_dungeon_image('./files/images/backgrounds/dark_forest.jpg', self.mobs.get_image_tuples())
                self.fight(first_turn='mobs')
        elif action == 'leave':
            for member in self.dungeon.party.members:
                member.delete_message()
                member.occupied = False
            self.dungeon.party.send_message(self.get_lang_tuple('text_3'), image=self.image)
            self.dungeon.update_map(new=True)
        elif action == 'attack':
            self.state = 'attacked'
            for member in self.dungeon.party.members:
                member.delete_message()
            image = create_dungeon_image('D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\dark_forest.jpg', self.mobs.get_image_tuples())
            self.dungeon.party.send_message(self.get_lang_tuple('text_2'), image=image)
            self.fight()
        elif action == 'sneak_attack':
            self.state = 'attacked'
            for member in self.dungeon.party.members:
                member.delete_message()
            image = create_dungeon_image('D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\dark_forest.jpg', self.mobs.get_image_tuples())
            self.dungeon.party.send_message(self.get_lang_tuple('text_2'), image=image)
            self.fight(first_turn='party')

    def first_enter(self):
        lang_tuple = self.get_greet_tuple()
        actions_keyboard = self.get_action_keyboard()
        self.dungeon.party.send_message(lang_tuple, image=self.image,
                                        reply_markup=actions_keyboard, leader_reply=True, short_member_ui=True)

    def get_victory_keyboard(self):
        self.state = 'totem_available'
        buttons = [('Взять тотем', 'take_totem'),
                   ('Оставить тотем', 'leave_totem')]

        keyboard = keyboards.form_keyboard(*[self.create_button(button[0], self.dungeon.party.leader, 'location', button[1],
                                                      named=True) for button in buttons])
        return keyboard

    def victory_message(self):
        self.dungeon.party.send_message(self.get_lang_tuple('text_5'), image=self.image,
                                        reply_markup=self.get_victory_keyboard())

    def cleared(self):
        return True if self.state == 'attacked' else False


class ForestNeutral(OpenLocation):
    name = 'forest_location_1'
    image = 'AgADAgADn6wxGytaCEhyBGic_6aBclpCXw8ABLniKliC04kevu8FAAEC'

    def get_emote(self):
        return str(self.complexity)


class ForestCrossroad(OpenLocation):
    name = 'forest_location_crossroad'
    default_emote = '+'
    image = 'AgADAgAD-6oxG1CdAAFI2GZDbBzm44CLzlEPAARvoCdcvexbtehgBAABAg'


class ForestEnd(OpenLocation):
    name = 'forest_location_end'
    default_emote = emoji_utils.emote_dict['weapon_em']
    image = 'AgADAgADnqwxGytaCEhjZz7aMaAsSRZYXw8ABHsRj_W360BSrOsFAAEC'


location_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None}




