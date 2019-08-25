#!/usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from locales import localization, emoji_utils

types = telebot.types
LangTuple = localization.LangTuple


class Button(types.InlineKeyboardButton):
    name = None

    def __init__(self, text, callback_data=None):
        types.InlineKeyboardButton.__init__(self, text, url=None, callback_data=callback_data,
                                            switch_inline_query=None,
                                            switch_inline_query_current_chat=None,
                                            callback_game=None, pay=None)


class FightButton(Button):
    def __init__(self, text, unit, *args, special='', named=False, ready=True, cd=None):
        if not isinstance(text, str):
            text = text.translate(unit.controller.lang)
        else:
            text = LangTuple('buttons' if not len(special) else special,
                             text).translate(unit.controller.lang) if not named else text
        if not ready:
            text = emoji_utils.emote_dict['restrict_em'] + ' ' + text
            if cd is not None:
                cd = str(cd)
                text = text + ' (' + cd + ')'
        callback = '_'.join(('fgt', str(unit), str(unit.fight), *args))
        Button.__init__(self, text, callback)

    def available(self):
        return True

    def add_available(self):
        return True


class ChatButton(Button):
    def __init__(self, chat, text, lang, *args, special='', named=False, emoji=None):
        if not isinstance(text, str):
            text = text.translate(lang)
        else:
            text = LangTuple('buttons' if not len(special) else special,
                             text).translate(lang) if not named else text
        if emoji is not None:
            text = emoji + ' ' + text
        callback = '_'.join(('mngt', str(chat.chat_id), *args))
        Button.__init__(self, text, callback)

    def available(self):
        return True

    def add_available(self):
        return True


class UserButton(Button):
    def __init__(self, text, lang, *args, special='', named=False, emoji=None):
        if not isinstance(text, str):
            text = text.translate(lang)
        else:
            text = LangTuple('buttons' if not len(special) else special,
                             text).translate(lang) if not named else text
        if emoji is not None:
            text = emoji + ' ' + text
        callback = '_'.join(('user', *args))
        Button.__init__(self, text, callback)

    def available(self):
        return True

    def add_available(self):
        return True


class DungeonButton(Button):
    def __init__(self, text, member, *args, special='', named=False):
        dungeon = member.dungeon
        text = LangTuple('buttons' if not len(special) else special,
                         text).translate(member.lang) if not named else text
        if not isinstance(text, str):
            text = text.translate(member.lang)
        callback = '_'.join(('map', str(dungeon), *args))
        Button.__init__(self, text, callback)


class BuildButton(Button):
    def __init__(self, text, unit, *args):
        game = unit.game
        callback = '_'.join(('build', str(game), *args))
        Button.__init__(self, text, callback)


class NameButton(Button):
    def __init__(self, text, unit, *args):
        fight = unit.fight
        callback = '_'.join(('fgt', str(unit), str(fight), *args))
        if isinstance(text, localization.LangTuple):
            text = text.translate(unit.controller.lang)
        Button.__init__(self, text, callback)


class AttackButton(NameButton):
    def __init__(self, unit, target):
        NameButton.__init__(self, target.name, unit, 'attack', str(target))


class WeaponButton(FightButton):
    def __init__(self, unit, weapon):
        self.unit = unit
        self.weapon = weapon
        FightButton.__init__(self, 'button', unit, 'weapon', self.weapon.name,
                             special='_'.join(['weapon', weapon.name]))

    def available(self):
        if not self.weapon.available() or self.unit.energy < 1:
            return False
        return True


class MeleeReloadButton(FightButton):
    def __init__(self, unit):
        FightButton.__init__(self, 'melee_reload', unit, 'melee-reload')


class RangeReloadButton(FightButton):
    def __init__(self, unit):
        FightButton.__init__(self, 'ranged_reload', unit, 'ranged-reload')


class SkipButton(FightButton):
    name = 'skip'

    def __init__(self, unit):
        FightButton.__init__(self, 'skip', unit, 'skip')


class SuicideButton(FightButton):
    def __init__(self, unit):
        FightButton.__init__(self, 'suicide', unit, 'suicide')


class MoveForward(FightButton):
    name = 'move'

    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'move', unit, 'move')

    def available(self):
        if self.unit.melee_targets or not self.unit.weapon.melee or self.unit.weapon.range_option or self.unit.rooted:
            return False
        return True

    def add_available(self):
        if self.unit.melee_targets == self.unit.targets() or self.unit.rooted:
            return False
        return True


class PutOutButton(FightButton):
    name = 'put-out'

    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'put-out', unit, 'put-out')

    def available(self):
        if 'burning' in self.unit.statuses.keys():
            return True
        return False

    def add_available(self):
        if 'burning' in self.unit.statuses.keys():
            return True
        return False


class MoveBack(FightButton):
    name = 'move_back'

    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'move_back', unit, 'move-back')

    def add_available(self):
        if not self.unit.melee_targets or self.unit.rooted:
            return False
        return True

    def available(self):
        if self.unit.melee_targets or not self.unit.weapon.melee or self.unit.weapon.range_option or self.unit.rooted:
            return False
        return True


class MenuButton(FightButton):
    def __init__(self, unit, name):
        FightButton.__init__(self, name, unit, 'menu')


class AdditionalKeyboard(FightButton):
    def __init__(self, unit):
        self.unit = unit
        additional_actions = [(available_action[0],
                               available_action[1]) for available_action in unit.get_additional_actions()
                               if available_action[1].add_available()]
        urgent = False
        for status in self.unit.statuses.values():
            if status.additional_buttons_actions is not None:
                urgent = True
                buttons = status.add_additional_buttons()
                for tpl in buttons:
                    additional_actions.append(tpl)
        if any(additional_action[1].name not in self.unit.standart_additional for additional_action in additional_actions):
            urgent = True
        FightButton.__init__(self, 'additional_keyboard' if not urgent else '!_additional_keyboard',
                             unit,
                             'add-keyboard')


class Info(FightButton):
    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'info', unit, 'info')


class OptionObject(FightButton):
    def __init__(self, game_object, option, name):
        self.unit = game_object.unit
        FightButton.__init__(self, name, self.unit, game_object.types[0],
                             game_object.name, str(option), named=True)


class ObjectButton(FightButton):
    def __init__(self, game_object):
        self.unit = game_object.unit
        cd = None
        ready = True
        if not game_object.ready():
            cd = str(game_object.ready_turn - game_object.unit.fight.turn)
        if not game_object.available():
            ready = False
        FightButton.__init__(self, game_object.name_lang_tuple(), self.unit, game_object.types[0],
                             game_object.name, ready=ready, cd=cd)


class ListAbilities(FightButton):
    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'abilities', unit, 'ability-list')


class ListItems(FightButton):
    def __init__(self, unit):
        self.unit = unit
        FightButton.__init__(self, 'items', unit, 'item-list')


def form_keyboard(*args, row_width=2):
    keyboard = types.InlineKeyboardMarkup(row_width=row_width)
    keyboard.add(*args)
    return keyboard


def form_turn_keyboard(unit):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    # buttons = ((1, WeaponButton(unit, unit.weapon)), (1, MoveForward(unit)), (1, unit.weapon.reload_button()),
    #           (3, AdditionalKeyboard(unit)), *form_second_row(unit))
    buttons = (*[(available_action[0], available_action[1]) for available_action in unit.available_actions()],
               *form_second_row(unit))
    for i in range(1, 4):
        button_list = [button[1] for button in buttons if button[1].available() and button[0] == i]
        if button_list:
            keyboard.add(*button_list)
    return keyboard


def form_additional_keyboard(unit):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = (*[(available_action[0], available_action[1]) for available_action in unit.get_additional_actions()],

               (4, MenuButton(unit, 'back')))
    for status in unit.statuses.values():
        print(status)
        if status.additional_buttons_actions is not None:
            buttons = [*buttons, *status.add_additional_buttons()]
    for i in range(1, 5):
        button_list = [button[1] for button in buttons if button[1].add_available() and button[0] == i]
        if button_list:
            keyboard.add(*button_list)
    return keyboard


def get_item_buttons(unit):
    item_list = [*[item for item in unit.items if item.available()],
                 *[armor for armor in unit.armor if armor.available()]]
    item_buttons = [item.button() for item in item_list]
    i = 0
    while item_buttons:
        name = item_buttons[i].text
        x = len([button for button in item_buttons if button.text == name])
        if x > 1:
            item_buttons[i].text = name + ' (' + str(x) + ')'
            item_buttons = [button for button in item_buttons if button.text != name]
        i += 1
        if len(item_buttons) <= i:
            break
    return item_buttons


def form_second_row(unit):
    ability_list = [ability for ability in unit.abilities if ability.active]
    if len(get_item_buttons(unit)) + len(ability_list) < 3:
        button_list = [*get_item_buttons(unit), *[ability.button() for ability in ability_list]]
    else:
        item_buttons = get_item_buttons(unit) if len(get_item_buttons(unit)) < 2 else [ListItems(unit)]
        ability_buttons = [ability.button() for ability in ability_list] if len(ability_list) < 2 \
            else [ListAbilities(unit)]
        button_list = [*item_buttons, *ability_buttons]
    button_list = [(2, button) for button in button_list]
    return button_list


def join_keyboard(game):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    button_1 = types.InlineKeyboardButton(url='https://telegram.me/vwarsbot?start=join_{}'.format(game.chat_id),
                                          text=LangTuple('utils', 'join').translate(game.lang))
    button_2 = types.InlineKeyboardButton(callback_data='switch',
                                          text=LangTuple('utils', 'switch').translate(game.lang))
    keyboard.add(button_1, button_2)
    return keyboard
