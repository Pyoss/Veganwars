from adventures import map_engine
from locales.localization import LangTuple
from bot_utils.keyboards import DungeonButton, form_keyboard
from bot_utils import bot_methods
import json
import engine
import threading
from fight import units


class DungeonEvents:
    name = None
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    image_file = './files/images/backgrounds/dark_forest_1.jpg'
    standard_mobs = True

    def __init__(self, dungeon, complexity):
        self.table_row = 'events_' + self.name
        self.dungeon = dungeon
        self.special = '0'
        self.mobs = None
        self.mob_team = None
        self.mob_image = None
        self.complexity = complexity
        self.get_mobs()
        self.entrance_location = None
        self.continue_func = None
        self.kwargs = None
        self.loot = engine.Container()

    def start(self, func, kwargs=None):
        self.dungeon.delete_map()
        self.kwargs = kwargs
        self.continue_func = func

    def event_fight(self, first_turn=None):
        for member in self.dungeon.party.members:
            member.occupied = True
        results = self.dungeon.run_fight(self.dungeon.party.join_fight(), self.mob_team, first_turn=first_turn)
        self.process_fight_results(results)

    def fight(self, first_turn=None):
        for member in self.dungeon.party.members:
            member.occupied = True
        thread = threading.Thread(target=self.event_fight, kwargs={'first_turn': first_turn})
        thread.start()

    def get_mobs(self):
        if self.standard_mobs:
            mobs = map_engine.get_enemy(self.complexity, self.dungeon.map.enemy_list)
            self.mobs = map_engine.MobPack(*mobs, complexity=self.complexity)
            self.mob_team = self.mobs.team_dict

    def get_button_list(self):
        return [('Назад', 'map')]

    def get_action_keyboard(self, member):
        buttons = self.get_button_list()
        buttons = [(self.get_button_tuples(member.lang)[str(button[0])], button[1]) for button in buttons]
        keyboard = form_keyboard(*[self.create_button(button[0], member, 'location', button[1],
                                                      named=True) for button in buttons])
        return keyboard

    def new_message(self, db_string, image=None, keyboard_func=True, short_member_ui=False):
        if keyboard_func:
            keyboard_func = self.get_action_keyboard
        self.dungeon.party.send_message(self.get_lang_tuple(db_string), image=image, reply_markup_func=keyboard_func,
                                        short_member_ui=short_member_ui)

    def reset_message(self, db_string, image=None, keyboard_func=True, short_member_ui=False):
        if keyboard_func:
            keyboard_func = self.get_action_keyboard
        for member in self.dungeon.party.members:
            member.delete_message()
        self.dungeon.party.send_message(self.get_lang_tuple(db_string), image=image, reply_markup_func=keyboard_func,
                                        short_member_ui=short_member_ui)

    def process_fight_results(self, results):
        bot_methods.err('Processing fight results...')
        if not any(unit_dict['name'] == self.dungeon.party.leader.unit_dict['name'] for unit_dict in results['winners']):

                def get_exit_keyboard(mmbr):
                    keyboard = form_keyboard(DungeonButton('Покинуть карту', mmbr, 'menu', 'defeat', named=True))
                    return keyboard

                self.dungeon.party.send_message('Вы проиграли!', reply_markup_func=get_exit_keyboard)
        else:
            for member in self.dungeon.party.members:
                member.occupied = False
                member.unit_dict = [unit_dict for unit_dict in results['winners']
                                    if unit_dict['name'] == member.unit_dict['name']][0]
                member.inventory.update()
            loot = results['loot'] + self.loot
            experience = sum([units.units_dict[mob].experience for mob in self.mobs.mob_units if self.mobs is not None])
            self.dungeon.party.experience += experience
            self.dungeon.party.distribute_loot(loot)
            self.victory()

    def victory(self):
        bot_methods.err(str(self.continue_func))
        self.continue_func(**self.kwargs)

    def get_button_tuples(self, lang):
        button_tuples = json.loads(LangTuple(self.table_row, 'buttons').translate(lang))
        return button_tuples

    def get_greet_tuple(self):
        return LangTuple(self.table_row, 'greeting')

    def get_lang_tuple(self, string):
        return LangTuple(self.table_row, string)

    def handler(self, call):
        bot_methods.err(call.data)
        data = call.data.split('_')
        action = data[3]
        if action == 'map':
            bot_methods.bot.edit_message_reply_markup(chat_id=call.from_user.id, message_id=call.message.message_id)
            for member in self.dungeon.party.members:
                member.occupied = False
        self.dungeon.update_map(new=True)

    def create_button(self, name_or_lang_tuple, member, *args, named=False):
        return DungeonButton(name_or_lang_tuple, member, *args, named=named)


class GoblinChaser(DungeonEvents):
    name = 'forest_goblin_totem_chasers'
    image = 'AgADAgADSaoxGxm_CUioZK0h2y0xQzlpXw8ABNGUQWMolIOL0_MFAAEC'
    image_file = './files/images/backgrounds/dark_forest_1.jpg'

    def start(self, func, kwargs=None):
        DungeonEvents.start(self, func, kwargs=kwargs)
        self.new_message('greeting', keyboard_func=False)
        self.fight()



