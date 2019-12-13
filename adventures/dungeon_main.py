# Сохраняет матрицу в виде словая
from adventures import locations, map_engine
from bot_utils import bot_methods, keyboards
from fight import abilities, standart_actions, units
from locales.localization import LangTuple
from locales.emoji_utils import emote_dict
from bot_utils.keyboards import form_keyboard
import dynamic_dicts
import time
import threading
import random
import engine


class MapHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        bot_methods.err(call.data)
        call_data = call.data.split('_')
        action = call_data[2]
        try:
            party = dynamic_dicts.dungeons[call.message.chat.id].party
            member = party.member_dict[call.from_user.id]
        except KeyError:
            return False
        # Перемещение группы
        if action == 'move':
            party.move_handler(call)
        # Действия с инвентарем
        elif action == 'item':
            member.inventory.handler(call)
        elif action == 'menu':
            member.menu_handler(call)
        elif action == 'location':
            party.current_location.handler(call)


class Party:
    def __init__(self, player_dict, chat_id, dungeon_id):
        # Текущая локация
        self.current_location = None
        self.id = chat_id
        # Чат, куда будет посылаться информация по игре
        self.dungeon = dynamic_dicts.dungeons[dungeon_id]
        self.members = [Member(key, value['unit_dict'], dungeon=dynamic_dicts.dungeons[dungeon_id]) for key, value in player_dict.items()]
        self.leader = self.members[0]
        self.member_dict = {member.chat_id: member for member in self.members}
        self.experience = 0
        self.collected_receipts = engine.ChatContainer()
        self.time = 0

    # Перемещение группы

    def move_handler(self, call):
        call_data = call.data.split('_')
        x, y = call_data[3].split('-')
        location = dynamic_dicts.dungeons[call.message.chat.id].map.get_location(x, y)
        map_engine.PartyMovement(self, self.current_location, location).execute(call)

    def collect_receipt(self, name, amount, alarm=True):
        if alarm:
            name = standart_actions.get_name(name, 'rus')
            self.send_message('Вы находите рецепт на {}({})'.format(name, amount))
        self.collected_receipts.put(name, value=amount)

    def move(self, location, new_map=False, exhaust=True, events=True):
        if self.current_location is not None:
            self.current_location.leave_location()
        if exhaust:
            self.exhaust()
        if events and False:
            if self.wait_for_event(func=location.enter_location, kwargs={'party': self, 'new_map': new_map}):
                pass
        else:
            location.enter_location(self, new_map=new_map)

    def wait_for_event(self, func, kwargs=None):
        event = engine.get_random_with_chances(self.dungeon.get_event_list())
        event(self.dungeon, 10).start(func=func, kwargs=kwargs)

    def exhaust(self):
        self.time += 1
        for member in self.members:
            member.advance()

    # Игроки пытаются переместится в локацию. Показывает ошибку либо перемещает игроков.
    def ask_move(self, location, call):
        if location == self.current_location:
            self.member_dict[call.from_user.id].member_menu_start()
        elif not self.current_location.is_close(location):
            bot_methods.answer_callback_query(call, 'Слишком далеко.', alert=False)
        elif call.from_user.id != self.leader.chat_id:
            bot_methods.answer_callback_query(call, 'Вы не лидер группы!', alert=False)
        elif self.occupied():
            bot_methods.answer_callback_query(call, 'Ваша группа занята!', alert=False)
        else:
            return True
        return False

    def for_all(self, func):
        for member in self.members:
            func(member)

    def send_message(self, *args, reply_markup_func=None, image=None, leader_reply=True, short_member_ui=False):

        def form_message(*rgs, sh_m_ui=False, memb=None):
            if sh_m_ui:
                rgs = [*rgs, LangTuple('dungeon_short-member', 'name', format_dict=units.units_dict[memb['unit_name']].get_dungeon_format_dict(memb))]
            msg = '\n'.join([arg.translate(self.leader.lang) for arg in rgs])
            return msg
        #if image is not None:
        #    image = open(image, 'rb')
        self.leader.send_message(form_message(*args, sh_m_ui=short_member_ui, memb=self.leader),
                                 reply_markup=reply_markup_func(self.leader) if reply_markup_func is not None else None,
                                 image=image)
        for member in self.members:
            if member != self.leader:
                member.send_message(form_message(*args, sh_m_ui=short_member_ui, memb=member),
                                    reply_markup=reply_markup_func(member) if reply_markup_func is not None else None if
                                    not leader_reply else None, image=image)

    def edit_message(self, text, reply_markup=None):
        for member in self.members:
            member.edit_message(text, reply_markup=reply_markup)

    # Нахождение локаций, которые находятся в поле зрения.

    def join_fight(self):
        team_dict = {member.team_dict_item()[0]: member.team_dict_item()[1] for member in self.members}
        team_dict['marker'] = 'party'
        return team_dict

    def occupied(self):
        if any([member.occupied for member in self.members]):
            for member in self.members:
                bot_methods.err('Занятость {}: {}'.format(member.name, member.occupied))
            return True
        return False

    def distribute_loot(self, loot_container):
        loot_receivers = list(self.members)
        random.shuffle(loot_receivers)
        if not loot_container.empty():
            player_containers = loot_container.random_split(len(loot_receivers))
            loot_list = dict(zip(loot_receivers, player_containers))
            for member in loot_receivers:
                message = LangTuple('dungeon', 'loot').translate(member.lang)
                if not loot_list[member].empty():
                    item_list = loot_list[member].to_string(member.lang)
                    message += '\n' + LangTuple('dungeon',
                                                'found', format_dict={'name': member.name,
                                                                      'item': item_list}). \
                        translate(member.lang) if loot_list[member] else \
                        '\n' + LangTuple('dungeon', 'full-inv', format_dict={'name': member}). \
                            translate(member.lang)
                    self.member_dict[member.chat_id].inventory += loot_list[member]
                bot_methods.send_message(member.chat_id, message)

    def distribute_experience(self, user_list):
        solo_experience = int(self.experience/len(user_list))
        for user in user_list:
            user.add_experience(solo_experience)


class Member:
    def __init__(self, chat_id, unit_dict, dungeon, lang='rus'):
        self.lang = lang
        self.chat_id = chat_id
        self.message_id = None
        self.menu = None
        self.name = unit_dict['name']
        self.dungeon = dungeon
        self.unit_dict = unit_dict
        self.inventory = Inventory(self)
        self.experience = 0
        self.occupied = False
        self.exhaustion = 0
        self.max_exhaustion = 20

    def send_message(self, text, reply_markup=None, image=None):
        if image is None:
            self.message_id = bot_methods.send_message(self.chat_id, text, reply_markup=reply_markup).message_id
        else:
            self.message_id = bot_methods.send_image(image, self.chat_id, text, reply_markup=reply_markup).message_id
        return self.message_id

    def alert(self, text, call, alert = False):
        bot_methods.answer_callback_query(call, text, alert=alert)

    def edit_message(self, text, reply_markup=None):
        return bot_methods.edit_message(self.chat_id, self.message_id,
                                        text, reply_markup=reply_markup)

    def update_map(self, new=False):
        text = self.member_string()
        if not new:
            self.edit_message(text=text,  reply_markup=self.dungeon.generate_map_keyboard())
        else:
            self.send_message(text=text,  reply_markup=self.dungeon.generate_map_keyboard())

    def delete_message(self):
        bot_methods.delete_message(self.chat_id, self.message_id)

    def member_string(self):
        inventory = self.inventory.get_inventory_string(self.lang)
        inventory_fill = LangTuple('utils', 'empty') if not inventory else LangTuple('utils', 'inventory')
        return LangTuple('unit_' + self['unit_name'], 'dungeon_menu',
                         format_dict=units.units_dict[self['unit_name']].get_dungeon_format_dict(self,
                                                                                                 inventory,
                                                                                                 inventory_fill)).translate(self.lang)

    def menu_keyboard(self):
        buttons = list()

        buttons.append(keyboards.DungeonButton('Инвентарь', self, 'menu', 'inventory', named=True))
        buttons.append(keyboards.DungeonButton('На карту', self, 'menu', 'map', named=True))
        buttons.append(keyboards.DungeonButton('Покинуть карту', self, 'menu', 'leave', named=True))
        if len(self.dungeon.party.members) > 1:
            buttons.append(keyboards.DungeonButton('Обмен', self, 'menu', 'give', named=True))

        idle_buttons = self.dungeon.party.current_location.get_button_list()['idle']
        idle_buttons = [(self.dungeon.party.current_location.get_button_tuples(self.lang)[str(button[0])],
                         str(button[0])) for button in idle_buttons]
        for button in idle_buttons:
            buttons.append(keyboards.DungeonButton(button[0], self, 'location', str(button[1]), named=True))
        keyboard = form_keyboard(*buttons)
        return keyboard

    def member_menu(self):
        text = self.member_string()
        keyboard = self.menu_keyboard()
        self.edit_message(text, reply_markup=keyboard)

    def member_menu_start(self):
        self.menu = Menu(text=self.member_string(), keyboard=self.menu_keyboard(), member=self)

    def add_item(self, item, call=None):
        return self.inventory.put(item)

    def remove_item(self, item_id):
        item = self.inventory[item_id]
        self.inventory.remove(item_id)
        return item[0]

    def equip_weapon(self, weapon_id, call):
        weapon = self.remove_item(weapon_id)
        if weapon:
            self['weapon'] = weapon
            return True
        else:
            return False

    def strip_weapon(self, weapon_id, call):
        if self.add_item(self['weapon'], call=call):
            self['weapon'] = None
            return True
        return False

    def equip_armor(self, armor_id, call):
        armor = self.remove_item(armor_id)
        if armor:
            self['armor'].append(armor)
            return True
        else:
            return False

    def strip_armor(self, armor_id, call):
        if any(armor for armor in self['armor'] if armor['id'] == armor_id):
            if self.add_item(self.inventory[armor_id], call=call):
                self['armor'].remove(next(armor for armor in self['armor'] if armor['id'] == armor_id))
                return True
        return False

    def use_item(self, item_id, call):
        item = self.inventory[item_id]
        item = standart_actions.object_dict[item[0]['name']](self, obj_dict=item[0])
        item.map_act(call, item_id)

    def menu_handler(self, call):
        call_data = call.data.split('_')
        action = call_data[3]
        if action == 'inventory':
            self.inventory.inventory_menu()
        elif action == 'give':
            self.inventory.inventory_menu(give=True)
        elif action == 'main':
            self.member_menu()
        elif action == 'map':
            self.menu.kill()
        elif action == 'leave':
            if self.chat_id == self.dungeon.party.leader.chat_id:
                self.dungeon.end_dungeon()
        elif action == 'defeat':
            if self.chat_id == self.dungeon.party.leader.chat_id:
                self.dungeon.end_dungeon(defeat=True)

    def team_dict_item(self):
        return self.chat_id, self.unit_dict

    def get_party_members_to_give(self, item_id, item_name):
        item_name = self.inventory.get_string(item_id, self.lang)
        text = 'Выберите, кому вы отдатите {}'.format(item_name)
        self.edit_message(text, reply_markup=self.get_buttons_members_to_give(item_id))

    def get_buttons_members_to_give(self, item_id):
        buttons = []
        members = self.dungeon.party.member_dict
        for key in members:
            if key != self.chat_id:
                call_data = item_id
                buttons.append(keyboards.DungeonButton(members[key].name,
                                                       self,
                                                       'item',
                                                       'give',
                                                       str(call_data),
                                                       str(key),
                                                       named=True))
        buttons.append(keyboards.DungeonButton('Закрыть', self, 'menu', 'main', named=True))
        keyboard = form_keyboard(*buttons)
        return keyboard

    def advance(self):

        self.exhaustion += 1
        if self.exhaustion >= self.max_exhaustion and not any(status['name'] == 'exhausted' for status in self['statuses']):
            bot_methods.send_message(self.chat_id, 'Вы чувствуете себя ужасно усталым.')
            self['statuses'].append(standart_actions.object_dict['exhausted']().to_dict())

    def __getitem__(self, item):
        return self.unit_dict[item]

    def __setitem__(self, key, value):
        self.unit_dict[key] = value


class Inventory(engine.Container):
    def __init__(self, member):
        engine.Container.__init__(self)
        self.max_size = 6
        self.member = member
        self.base_dict = member['inventory']

    def handler(self, call):
        call_data = call.data.split('_')
        action = call_data[3]
        if self.member.menu is None:
            return False
        elif self.member.menu.message_id != call.message.message_id:
            return False
        if action == 'action':
            item_id = call_data[4]
            item_name = call_data[5]
            self.get_item_menu(item_id, item_name)
        elif action == 'givelist':
            item_id = call_data[4]
            item_name = call_data[5]
            self.member.get_party_members_to_give(item_id, item_name)
        elif action == 'give':
            item_id = call_data[4]
            member_id = int(call_data[5])
            member = self.member.dungeon.party.member_dict[member_id]
            item = self[item_id]
            self.remove(item[0])
            member.inventory.put(item[0])
            self.update_menu()
        elif action == 'menu':
            self.update_menu()
        elif action == 'throw':
            item_id = call_data[4]
            item = self[item_id]
            self.member.dungeon.party.current_location.throwed(item[0]['name'])
            self.remove(item_id)
            self.update_menu()
        elif action == 'equip':
            item_id = call_data[4]
            item_name = call_data[5]
            if 'weapon' in self.get_item_object(item_name=item_name, item_id=item_id).core_types:
                if self.member['weapon'] is None:
                    self.member.equip_weapon(item_id, call)
            elif 'armor' in self.get_item_object(item_name=item_name, item_id=item_id).core_types:
                self.member.equip_armor(item_id, call)
            self.update_menu()
        elif action == 'strip':
            item_id = call_data[4]
            item_name = call_data[5]
            if 'weapon' in self.get_item_object(item_id, item_name).core_types:
                if self.member['weapon']['name'] == item_name:
                    self.member.strip_weapon(item_id, call)
            elif 'armor' in self[item_id]['core_types']:
                self.member.strip_armor(item_id, call)
            self.update_menu()
        elif action == 'use':
            item_id = call_data[4]
            self.member.use_item(item_id, call)
            self.update_menu()

    def __iter__(self):
        items_list = self.items()
        return items_list.__iter__()

    def append(self, item):
        items_list = self.member['inventory']
        items_list.append(item)

    def inventory_items(self):
        items_list = [item_dict for item_dict in self.member['inventory']]
        return items_list

    def items(self, without_equipped=False):
        items_list = []
        if not without_equipped:
            if self.member['weapon'] is not None:
                if 'natural' not in standart_actions.object_dict[self.member['weapon']['name']].types:
                    items_list.append((self.member['weapon'], 'weapon'))
            for armor in self.member['armor']:
                items_list.append((armor, 'armor'))
        items_list = [*items_list, *[(self.member['inventory'][key][0], key) for key in self.member['inventory'].keys()]]
        return items_list

    def item_names(self):
        return [item['name'] for item in self.items()]

    def get_item_tuple(self, item):
        return standart_actions.object_dict[item]().get_table_row()

    def get_item_name(self, item, lang):
        if isinstance(item, str):
            return LangTuple(self.get_item_tuple(item), 'name').translate(lang)
        elif isinstance(item, dict):
            return LangTuple(self.get_item_tuple(item['name']), 'name').translate(lang)
        else:
            name = LangTuple(self.get_item_tuple(item[0]['name']), 'name').translate(lang)
            if 'improved' in item[0].keys():
                if item[0]['improved'] > 0:
                    name += ' +' + str(item['improved'])
            return name

    def get_inventory_string(self, lang):
        return self.to_string(lang)

    def get_equipment_string(self, lang):
        equipment_list = []
        if self.member['weapon'] is not None:
            equipment_list.append(
                emote_dict['weapon_em'] + self.get_item_name(self.member['weapon'], lang))
        for item in self.member['armor']:
            equipment_list.append(emote_dict['shield_em'] + self.get_item_name(item, lang))
        return ', '.join(equipment_list) if equipment_list else ' --- '

    def inventory_buttons(self):
        buttons = []
        for item in self:
            item_name = self.get_item_name(item, self.member.lang)
            call_data = item[1]
            if item[1] == 'weapon':
                item_name = emote_dict['weapon_em'] + item_name
            elif item[1] == 'armor':
                item_name = emote_dict['shield_em'] + item_name
            else:
                item_name = self.get_string(call_data, self.member.lang)
            buttons.append(keyboards.DungeonButton(item_name,
                                                   self.member,
                                                   'item',
                                                   'action',
                                                   str(call_data),
                                                   item[0]['name'],
                                                   named=item_name))
        buttons.append(keyboards.DungeonButton('Закрыть', self.member, 'menu', 'main', named=True))
        return buttons

    def give_buttons(self):
        buttons = []
        for item in self.items(without_equipped=True):
            call_data = item[1]
            item_name = self.get_string(call_data, self.member.lang)
            buttons.append(keyboards.DungeonButton(item_name,
                                                   self.member,
                                                   'item',
                                                   'givelist',
                                                   str(call_data),
                                                   item[0]['name'],
                                                   named=item_name))
        buttons.append(keyboards.DungeonButton('Закрыть', self.member, 'menu', 'main', named=True))
        return buttons

    def inventory_menu(self, give=False):
        buttons = self.inventory_buttons() if not give else self.give_buttons()
        keyboard = form_keyboard(*buttons)
        self.member.edit_message(text='Инвентарь' if not give else 'Выберите предмет для передачи.', reply_markup=keyboard)

    def update_menu(self):
        buttons = self.inventory_buttons()
        keyboard = form_keyboard(*buttons)
        self.member.edit_message(LangTuple('utils_inventory', 'name').translate(self.member.lang),
                                 reply_markup=keyboard)
        self.member.menu.update()

    def __change__(self, item, value):
        engine.Container.__change__(self, item, value)
        self.update_to_member()

    def update(self):
        self.base_dict = self.member['inventory']

    def update_to_member(self):
        self.member['inventory'] = self.base_dict

    def get_item_actions(self, item, item_id):
        actions = []
        core_types = item.core_types
        actions.append(['Использовать', 'use'])
        if 'weapon' in core_types:
            if item_id != 'weapon':
                actions.append(['Надеть', 'equip'])
                actions.append(['Выбросить', 'throw'])
            else:
                actions.append(['Снять', 'strip'])
        elif 'armor' in core_types:
            if item_id != 'armor':
                actions.append(['Надеть', 'equip'])
                actions.append(['Выбросить', 'throw'])
            else:
                actions.append(['Снять', 'strip'])
        else:
            actions.append(['Выбросить', 'throw'])
        return actions

    def get_item_menu(self, item_id, item_name):
        buttons = []
        item = self.get_item_object(item_id, item_name=item_name)
        table_row = item.table_row
        actions = self.get_item_actions(item, item_id)
        for action in actions:
            buttons.append(keyboards.DungeonButton(action[0], self.member, 'item', action[1],
                                                   item_id, item_name, named=True))
        buttons.append(keyboards.DungeonButton('Назад', self.member, 'item', 'menu', named=True))
        keyboard = keyboards.form_keyboard(*buttons)
        text = LangTuple(table_row, 'name').translate(self.member.lang) + '\n' \
               + LangTuple(table_row, 'desc').translate(self.member.lang)
        self.member.edit_message(text, reply_markup=keyboard)
        self.member.menu.update()

    def is_empty(self):
        if not self.base_dict:
            return True
        return False


class Menu:
    def __init__(self, member, text, keyboard, new=False):
        self.member = member
        self.new = new
        if not new and self.member.message_id is not None:
            self.member.edit_message(text,
                                     reply_markup=keyboard)
            self.message_id = self.member.message_id
        else:

            self.message_id = self.member.send_message(text,
                                     reply_markup=keyboard)

        self.member.occupied = True
        self.timer_max = 60
        self.time_now = 0
        timer = threading.Thread(target=self.exist_timer)
        timer.start()

    def exist_timer(self):
        time.sleep(5)
        self.time_now += 5
        if self.time_now == self.timer_max:
            self.kill()

    def update(self):
        self.time_now = 0

    def kill(self):
        self.member.update_map()
        self.member.menu = None
        self.member.occupied = False


class AbilityChoice:
    def __init__(self, member, ability_list):
        self.member = member
        self.ability_list = ability_list

    def run(self):
        self.member.occupied = True
        buttons = []
        for ability in self.ability_list:
            buttons.append(keyboards.DungeonButton('name', self, 'lvl', ability,
                                                   special=abilities.ability_dict[ability](None).get_table_row(), ))
        buttons.append(keyboards.DungeonButton('Назад', self, 'lvl', 'back', named=True))
        keyboard = keyboards.form_keyboard(*buttons)
        self.member.send_message('Выберите новую способность', reply_markup=keyboard)


def save_dungeon_map(dungeon):
    dungeon_dict = {}
    for key in dungeon.location_matrix:
        dungeon_dict[key] = dungeon.location_matrix[key].str()
    return dungeon_dict


def load_dungeon_map(dungeon, dungeon_dict):
    for key in dungeon_dict:
        info = dungeon_dict[key].split('_')
        dungeon.location_matrix[key] = locations.location_dict[info[0](special=info[1])]
        if info[2] == 'visited':
            dungeon.location_matrix[key].visited = True
