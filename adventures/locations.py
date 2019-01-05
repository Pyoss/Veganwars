from adventures import map_engine
from locales import emoji_utils
from fight import fight_main, ai, items, units, armors, standart_actions
import locales.localization
from bot_utils import bot_methods, keyboards
import random
import inspect
import sys
import engine
import threading
import time


class OpenLocation(map_engine.Location):

    def move_permission(self, movement, call):
        return self.available()

    def available(self):
        return True


class PlaceHolder(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = str(self.complexity)


class PlaceHolder2(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = '_'


class End(OpenLocation):
    name = 'end'
    emote = '⚔'

    def __init__(self, x, y, dungeon, map_tuple, special='0'):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)


class DeadEnd(OpenLocation):
    def __init__(self, x, y, dungeon, map_tuple):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        self.emote = 'X'


class CrossRoad(OpenLocation):
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

    def __init__(self, x, y, dungeon, map_tuple, special='0', loot=list()):
        map_engine.Location.__init__(self, x, y, dungeon, map_tuple)
        mobs = map_engine.get_enemy(self.complexity, dungeon.map.enemy_dict)
        self.mobs = map_engine.MobPack(*mobs)
        self.loot = engine.Container()
        if self.mobs is not None:
            main_mob = max(mobs, key=lambda mob: units.units_dict[mob].danger)
            self.emote = units.units_dict[main_mob].emote

    def on_enter(self):
        if not self.visited and self.dungeon.map.entrance != self:
            for member in self.dungeon.party.members:
                member.occupied = True
            self.dungeon.delete_map()

            class DungFight:
                def __init__(dung):
                    results = self.dungeon.run_fight(self.dungeon.party.join_fight(), self.mobs.join_fight())
                    self.process_results(results)
            thread = threading.Thread(target=DungFight)
            thread.start()
        else:
            self.dungeon.update_map()

    def process_results(self, results):
        if not any(unit_dict['name'] == self.dungeon.party.leader.unit_dict['name'] for unit_dict in results['winners']):
                bot_methods.send_message(self.dungeon.party.chat_id, 'Вы проиграли!')
                self.dungeon.end_dungeon(defeat=True)
        else:
            for member in self.dungeon.party.members:
                member.occupied = False
                member.unit_dict = [unit_dict for unit_dict in results['winners']
                                    if unit_dict['name'] == member.unit_dict['name']][0]
                member.inventory.update()
            loot = results['loot'] + self.loot
            self.dungeon.party.distribute_loot(loot)
            self.dungeon.update_map()


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
                print(item)
                victim.inventory.remove(item)
                self.dungeon.party.send_message('Вы потеряли ' + str(standart_actions.get_name(item[0]['name'], 'rus')))
            else:
                pass
        self.dungeon.update_map(new=True)



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


location_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None}




