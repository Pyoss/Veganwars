#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bot_utils import keyboards, bot_methods
from locales import localization, emoji_utils
import inspect
import sys
import engine
import dynamic_dicts

object_dict = {}
action_dict = {}


class ActionHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        try:
            fight = dynamic_dicts.fight_dict[call_data[2]]
            unit = fight.units_dict[int(call_data[1])]
        except KeyError:
            return self.handler.game_error(call)
        if unit.controller.message_id == call.message.message_id and unit.active:
            action = action_dict[call_data[3]](unit, fight, info=call_data, call=call)
            availability = action.available()
            if not availability:
                error_text = action.error_text()
                self.handler.error(error_text, call)
                return False
            unit.active = False
            action.act()
        else:
            bot_methods.err('Ошибка обработки запроса к ActionHandler. Controller_id={}, message_id={}, unit_active={}'.
                  format(unit.controller.chat_id, call.message.message_id, unit.active))
            return self.handler.actor_error(call)

# 1-20 До эффектов, 21-40 - эффекты, 41-60 результаты. Некоторые правила:
# здоровье не изменять после 41,
# здоровье не прибавлять после 39,
# предметы не использовать раньше 2,
# перезарядка и отдых: 3
# подойти: 10
# отойти: 1

# act срабатывает по нажатию кнопки
# activate срабатывает во время раунда


class Action:
    name = None
    types = []
    order = 5
    full = True
    action_type = []

    def __init__(self, unit, fight, info=None, call=None):
        self.unit = unit
        self.fight = fight
        self.info = info
        self.call = call
        self.full = True
        self.str = ''

    def act(self):
        self.fight.action_queue.append(self)
        for action_type in self.action_type:
            self.unit.action.append(action_type)
        if self.full:
            self.unit.controller.end_turn()

    def to_queue(self):
        pass

    def activate(self):
        pass

    def available(self):
        return True


class UnitAction:
    name = 'blank'

    def __init__(self, name, func, button_name, action_type=list(), types=list(),
                 full=True, order=5):
        self.button_name = button_name
        self.name = name
        self.full = full
        self.order = order
        self.types = types
        self.action_type = action_type

        class NewAction(Action):
            name = self.name
            self.button_name = button_name
            action_type = self.action_type
            order = self.order
            full = self.full
            types = self.types

            def activate(new_action):
                func(new_action)

        action_dict[name] = NewAction


class EffectString(Action):
    full = False

    def __init__(self, fight, order, lang_tuple):
        Action.__init__(self, None, fight)
        self.order = 20 + order
        self.lang_tuple = lang_tuple

    def activate(self):
        self.fight.string_tuple.append(self.lang_tuple)


class MenuAction(Action):
    full = False

    def act(self):
        self.unit.active = True
        self.activate()

    def activate(self):
        pass


class BaseAttack(Action):
    action_type = ['attack']

    def __init__(self, unit, fight, info=None, order=5, call=None, stringed=True):
        Action.__init__(self, unit, fight, info=info)
        self.order = order
        self.weapon = self.unit.weapon
        self.call = call
        self.stringed = stringed
        if info is not None:
            self.unit.target = self.fight[info[-1]]
        self.dmg_done = 0
        self.dmg_blocked = 0
        self.special_emotes = []
        self.target = None
        self.armored = None
        self.attack_tuple = None
        self.blockable = True

    def to_emotes(self, emote):
        if emote not in self.special_emotes:
            self.special_emotes.append(emote)

    def attack(self, waste=None, dmg=None, special=False):
        self.weapon.before_hit(self)
        self.unit.activate_abilities('before_hit', action=self)
        # Вычисление нанесенного урона и трата энергии
        self.dmg_done = self.weapon.get_damage(self.target) if dmg is None else dmg
        if waste is None:
            self.unit.waste_energy(self.weapon.energy_cost)
        else:
            self.unit.waste_energy(waste)
        # Применение способностей и особых свойств оружия
        if not dmg and self.dmg_done != 0:
            self.dmg_done += self.unit.damage
        self.unit.on_hit(self)
        if special:
            self.weapon.modify_attack(self)
        self.target.receive_hit(self)
        self.weapon.on_hit(self)

    def on_attack(self):
        self.target.receive_damage(self.dmg_done)

    def string(self, hit_string):
        if self.armored is None:
            action = 'hit' if self.dmg_done > 0 else 'miss'
            if self.target == self.unit:
                action += '_self'
            if hit_string != '':
                action = hit_string + '_' + action
            attack_dict = {'actor': self.unit.name, 'target': self.target.name,
                           'damage': self.dmg_done if not self.special_emotes else str(self.dmg_done) +
                           ''.join(self.special_emotes)}
            self.attack_tuple = localization.LangTuple(self.weapon.table_row, action, attack_dict)
            self.fight.string_tuple.row(self.attack_tuple)
            self.target.death_lang_tuple = {'source': self.weapon,
                                            'target': self.unit.name}
        else:
            self.armor_string()

    def armor_string(self):
        action = 'armor'
        attack_dict = {'actor': self.unit.name, 'target': self.target.name,
                       'armor_name': localization.LangTuple('armor' + '_' + self.armored.name, 'name')}
        attack_tuple = localization.LangTuple(self.weapon.table_row, action, attack_dict)
        self.fight.string_tuple.row(attack_tuple)

    def activate(self, target=None, weapon=None):
        # Определение цели
        self.target = self.unit.target if target is None else target
        self.weapon = weapon if weapon is not None else self.weapon
        self.attack()
        self.on_attack()


class SpecialAttack(BaseAttack):
    def __init__(self, unit, fight, info, order, energy_cost=0):
        BaseAttack.__init__(self, fight=fight, unit=unit, info=info, order=order)
        self.energy_cost = energy_cost
        self.action_type = self.weapon.special_types

    def activate(self, target=None, weapon=None):
        # Определение цели
        self.target = self.unit.target
        self.attack(special=True)
        self.on_attack()
        # Добавление описания в строку отчета
        self.string('special')


class Suicide(Action):
    name = 'suicide'

    def __init__(self, unit, fight, info=None, order=10, call=None):
        Action.__init__(self, unit, fight, info=info)
        self.order = order
        self.call = call

    def activate(self):
        self.unit.hp_delta -= 100
        self.fight.string_tuple.row(localization.LangTuple('fight', 'suicide', {'actor': self.unit.name}))


class Attack(BaseAttack):
    name = 'attack'

    def activate(self, target=None, weapon=None, waste=None, dmg=None):
        self.weapon = weapon if weapon is not None else self.weapon
        # Определение цели
        self.target = self.unit.target if target is None else target
        self.attack(waste=waste, dmg=dmg)
        self.on_attack()
        # Добавление описания в строку отчета
        if self.stringed:
            self.string(self.str)
        return self.dmg_done


class Skip(Action):
    name = 'skip'
    action_type = ['idle', 'skip']

    def activate(self):
        # Добавление строки пропуска
        self.fight.string_tuple += localization.LangTuple('fight', 'skip', {'actor': self.unit.name})


class PutOutFire(Action):
    name = 'put-out'
    action_type = ['tech']
    order = 1

    def available(self):
        if 'burning' in self.unit.statuses.keys():
            return True
        return False

    def activate(self):
        self.unit.action.append('skip')


class MoveForward(Action):
    name = 'move'
    action_type = ['move', 'forward']
    order = 10

    def activate(self):
        self.fight.string_tuple += localization.LangTuple('fight', 'move', {'actor': self.unit.name})
        self.unit.move_forward()

    def available(self):
        if self.unit.rooted:
            return False
        return True


class MoveBack(Action):
    name = 'move-back'
    action_type = ['move', 'back']
    order = 7

    def activate(self):
        self.fight.string_tuple += localization.LangTuple('fight', 'move_back', {'actor': self.unit.name})
        self.unit.move_back()

    def available(self):
        if self.unit.rooted:
            print('rooted')
            return False
        return True


class Reload(Action):
    action_type = ['idle', 'reload']
    order = 3

    def activate(self):
        return self.unit.recovery()


class MeleeReload(Reload):
    name = 'melee-reload'

    def activate(self):
        energy = Reload.activate(self)
        self.fight.string_tuple += localization.LangTuple('fight',
                                                          'melee_reload', {'actor': self.unit.name, 'energy': energy})


class RangedReload(Reload):
    name = 'ranged-reload'

    def activate(self):
        energy = Reload.activate(self)
        self.fight.string_tuple += localization.LangTuple('fight',
                                                          'ranged_reload', {'actor': self.unit.name, 'energy': energy})


class WeaponActions(MenuAction):
    name = 'weapon'
    types = ['keyboard']

    def act(self):
        if 'option' not in self.unit.weapon.types or len(self.unit.weapon.targets()) != 1:
            self.unit.active = True
        self.activate()

    def activate(self):
        weapon = self.unit.weapon
        weapon.get_action()


class SpecialWeaponAction(Action):
    name = 'special'

    def __init__(self, unit, fight, info, call=None):
        Action.__init__(self, unit, fight, info, call=call)
        self.target = fight[info[-1]] if len(info) > 4 else None
        self.action_type = self.unit.weapon.special_types
        self.order = self.unit.weapon.order
        self.weapon = self.unit.weapon

    def activate(self):
        weapon = self.unit.weapon
        weapon.start_special_action(self.info, types=self.types)

    def available(self):
        return self.unit.weapon.special_available(target=self.target)

    def error_text(self):
        return self.unit.weapon.error_text()


class SpecialWeaponOption(MenuAction):
    name = 'wpspecial'

    def __init__(self, unit, fight, info, call=None):
        Action.__init__(self, unit, fight, info, call=call)
        self.types = self.unit.weapon.special_types
        self.order = self.unit.weapon.order

    def activate(self):
        weapon = self.unit.weapon
        weapon.start_special_action(self.info)


class ListAbilities(MenuAction):
    name = 'ability-list'
    types = ['keyboard']

    def activate(self):
        keyboard = keyboards.form_keyboard(*[ability.button() for ability
                                             in self.unit.abilities],
                                           keyboards.MenuButton(self.unit, 'back'))
        self.unit.controller.edit_message(localization.LangTuple('utils', 'abilities'), reply_markup=keyboard)


class Ability(Action):
    name = 'ability'
    full = False
    action_type = ['ability']

    def __init__(self, unit, fight, info=None, call=None, ability_name=None):
        self.call = call
        Action.__init__(self, unit, fight, info=info)
        ability_name = info[4] if ability_name is None else ability_name
        self.ability = next(ability for ability in unit.abilities if ability.name == ability_name)
        self.order = self.ability.order
        self.types = ['ability', *self.ability.types]

    def act(self):
        self.unit.action = [*self.unit.action, *self.types]
        self.ability.act(self)

    def activate(self):
        self.ability.activate(self)

    def available(self):
        return self.ability.available()

    def error_text(self):
        return self.ability.error_text()


class ListItems(MenuAction):
    name = 'item-list'
    types = ['keyboard']

    def activate(self):
        keyboard = keyboards.form_keyboard(*keyboards.get_item_buttons(self.unit),
                                           keyboards.MenuButton(self.unit, 'back'))
        self.unit.controller.edit_message(localization.LangTuple('utils', 'items'), reply_markup=keyboard)


class StatusAction(Action):
    name = 'status-action'
    full = True

    def __init__(self, unit, fight, info=None, call=None, status_name=None):
        Action.__init__(self, unit, fight, info=info, call=call)
        status_name = info[4] if status_name is None else status_name
        self.status = self.unit.statuses[status_name]
        self.order = self.status.action_order
        self.types = self.status.action_type

    def act(self):
        self.unit.action = [*self.unit.action, *self.types]
        Action.act(self)

    def activate(self):
        self.status.handle(self.call.data.split('_') if self.call is not None else self.info)


class Item(Action):
    name = 'item'
    full = False
    action_type = ['item']

    def __init__(self, unit, fight, info=None, call=None, item_name=None):
        self.call = call
        Action.__init__(self, unit, fight, info=info)
        item_name = info[4] if item_name is None else item_name
        self.item = next(item for item in unit.items if item.name == item_name)
        self.order = self.item.order
        self.types = ['item', *self.item.types]

    def act(self):
        self.unit.action = [*self.unit.action, *self.types]
        self.item.act(self)

    def activate(self):
        self.item.activate(self)


class Armor(Action):
    name = 'armor'
    full = False
    action_type = ['armor']

    def __init__(self, unit, fight, info=None, call=None, armor_name=None):
        self.call = call
        Action.__init__(self, unit, fight, info=info)
        armor_name = info[4] if armor_name is None else armor_name
        self.armor = next(armor for armor in unit.armor if armor.name == armor_name)
        self.order = self.armor.order
        self.types = ['item', *self.armor.types]

    def act(self):
        self.unit.action = [*self.unit.action, *self.types]
        self.armor.act(self)

    def activate(self):
        self.armor.activate(self)


class AdditionalKeyboard(MenuAction):
    name = 'add-keyboard'
    types = ['keyboard']

    def activate(self):
        keyboard = keyboards.form_additional_keyboard(self.unit)
        self.unit.controller.edit_message(self.unit.menu_string(),
                                reply_markup=keyboard)


class GetInfo(MenuAction):
    name = 'info'
    types = ['keyboard']

    def activate(self):
        bot_methods.answer_callback_query(call=self.call,
                                          text=self.unit.info_string(lang=self.unit.controller.lang).translate(self.unit.controller.lang),
                                          alert=True)


class MainMenu(MenuAction):
    name = 'menu'
    types = ['keyboard']

    def activate(self):
        keyboard = keyboards.form_turn_keyboard(self.unit)
        self.unit.controller.edit_message(self.unit.menu_string(),
                                reply_markup=keyboard)


class Custom:
    name = None
    types = []
    order = 0
    full = False
    effect = False

    def __init__(self, func, *args, order=5, to_queue=True, unit=None, types=None, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.order = order
        self.unit = unit
        self.action_type = [] if types is None else types
        if to_queue:
            self.unit.fight.edit_queue(self)

    def act(self):
        self.unit.fight.action_queue.append(self)

    def activate(self):
        self.func(*self.args, **self.kwargs)

    def to_queue(self):
        pass


class AddString(Custom):

    def __init__(self, lang_tuple, order, unit):
        self.lang_tuple = lang_tuple
        self.unit = unit
        self.order = order
        Custom.__init__(self, self.to_string, order=self.order, unit=self.unit)

    def to_string(self):
        if self.effect:
            self.unit.fight.string_tuple.effect()
        self.unit.fight.string_tuple.row(self.lang_tuple)


# Объекты для способностей и предметов
class GameObject:
    name = None
    order = 5
    cd = 0
    weight = 0
    active = True
    full = True
    core_types = []
    types = []
    db_string = ''
    keyboard_button = keyboards.ObjectButton
    effect = False
    one_time = True
    action_type = []
    price = 100
    default_energy_cost = 0
    emote = emoji_utils.emote_dict['question_em']

    def __init__(self, unit=None, obj_dict=None):
        self.unit = unit
        self.table_row = None
        self.get_table_row()
        self.types = [*self.core_types, *self.types]
        self.ready_turn = 0
        self.energy_cost = self.get_energy_cost()
        self.id = str(engine.rand_id())
        if obj_dict is not None:
            self.from_dict(obj_dict)

    def get_energy_cost(self):
        return self.default_energy_cost

    def from_dict(self, obj_dict):
        for key, value in obj_dict.items():
            setattr(self, key, value)

    def to_dict(self):
        this_dict = {
            'name': self.name
        }
        return this_dict

    def get_table_row(self):
        self.table_row = '_'.join([self.db_string, self.name])
        return self.table_row

    def pop_info(self, call):
        bot_methods.answer_callback_query(call=call,
                                          text=localization.LangTuple(self.table_row,
                                                                      'info').translate(self.unit.controller.lang))

    def activate(self, action):
        self.on_cd()

    def name_lang_tuple(self):
        return localization.LangTuple(self.table_row, 'name')

    def lang_tuple(self, string_row):
        return localization.LangTuple(self.table_row, string_row)

    def available(self):
        return True

    def error_text(self):
        return ''

    def string(self, string_code, format_dict=None, order=0):
        format_dict = {} if None else format_dict
        lang_tuple = localization.LangTuple(self.table_row, string_code, format_dict=format_dict)
        if not order:
            self.unit.fight.string_tuple.row(lang_tuple)
        else:
            AddString(lang_tuple=lang_tuple, unit=self.unit, order=order)

    def button(self):
        return self.keyboard_button(self)

    def ask_action(self):
        self.unit.controller.end_turn() if self.full else self.unit.get_action(edit=True)

    def start_act(self):
        pass

    def suit(self):
        if 'unique' in self.types:
            return False
        if 'not_range' in self.types and not self.unit.weapon.melee:
            return False
        elif 'not_melee' in self.types and self.unit.weapon.melee:
            return False
        elif 'not_solo' in self.types and len(self.unit.team.actors) < 2:
            return False
        elif self.name in [ability.name for ability in self.unit.abilities]:
            return False
        else:
            return True

    def on_cd(self):
        self.ready_turn = self.unit.fight.turn + self.unit.speed_penalty() + self.cd

    def ready(self):
        if self.unit.fight.turn < self.ready_turn:
            return False
        elif not self.active:
            return False
        return True

    def ask_start_option(self):
        pass

    def build_act(self):
        pass

    def apply_start_option(self, info):
        pass

    def dungeon_use(self):
        pass

    def try_placement(self, unit_dict):
        if 'item' in self.core_types and len(unit_dict['inventory']) > 2:
            return False
        return True


def get_name(name, lang):
    return object_dict[name]().name_lang_tuple().translate(lang)


def get_class(name):
    return object_dict[name]


class InstantObject(GameObject):

    def act(self, action):
        self.unit.fight.action_queue.append(action)
        for action_type in action.action_type:
            self.unit.action.append(action_type)
        self.ask_action()


class TargetObject(GameObject):

    def target_keyboard(self):
        return keyboards.form_keyboard(*[keyboards.OptionObject(self,
                                                                name=(unit.name if isinstance(unit.name, str)
                                                                      else unit.name.str(self.unit.controller.lang)),
                                                                option=unit) for unit in self.targets()],
                                       keyboards.MenuButton(self.unit, 'back'))

    def targets(self):
        return []

    def act(self, action):
        if len(action.info) > 5:
            self.act_options(action)
            for action_type in action.action_type:
                self.unit.action.append(action_type)
            self.on_cd()
            if self.energy_cost > 0:
                self.unit.waste_energy(self.energy_cost)
            self.ask_action()
        else:
            self.ask_options()

    def act_options(self, action):
        action.target = self.unit.fight[action.info[-1]]
        self.unit.fight.action_queue.append(action)

    def ask_options(self):
        self.unit.active = True
        keyboard = self.target_keyboard()
        self.unit.controller.edit_message(localization.LangTuple(self.table_row, 'options'), reply_markup=keyboard)


class SpecialObject(GameObject):
    def target_keyboard(self, action=None, row_width=2):
        return keyboards.form_keyboard(*self.options_keyboard(action=action),
                                       keyboards.MenuButton(self.unit, 'back'), row_width=row_width)

    def options(self):
        return []

    def options_keyboard(self, action=None):
        return [keyboards.OptionObject(self, name=option[0], option=option[1]) for option in self.options()]

    def act(self, action):
        if len(action.info) > 4:
            self.act_options(action)
            for action_type in action.action_type:
                self.unit.action.append(action_type)
            self.on_cd()
            if self.energy_cost > 0:
                self.unit.waste_energy(self.energy_cost)
            self.ask_action()
        else:
            self.ask_options()

    def act_options(self, action):
        self.unit.fight.action_queue.append(action)

    def ask_options(self):
        self.unit.active = True
        keyboard = self.target_keyboard()
        self.unit.edit_message(localization.LangTuple(self.table_row, 'options'), reply_markup=keyboard)

act_dict = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
action_dict = {**action_dict, **{v.name: v for k, v in act_dict.items()}}
