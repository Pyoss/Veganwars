#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import abilities, weapons
from locales import localization


class BuildHandler:
    name = None

    def __init__(self, handler):
        self.handler = handler

    def handle(self, call):
        call_data = call.data.split('_')
        try:
            fight = self.handler.game_dict[call_data[1]].fight
            if fight is None:
                self.handler.game_error()
                return False
            actor = fight.actors_dict[call.from_user.id]
        except KeyError:
            return self.handler.game_error(call)
        if actor.message_id == call.message.message_id and actor.active:
            if call_data[2] != 'info':
                actor.active = False
            add_build(actor, fight, info=call_data, call=call)
        else:
            print(actor.message_id)
            print(call.message.message_id)
            print(actor.active)
            return self.handler.actor_error(call)


def add_build(actor, fight, info, call=None):
    object_type = info[2]
    if object_type == 'abilities':
        abilities.ability_dict[info[3]](actor).to_build(info)
    elif object_type == 'weapon':
        if info[3] == 'cancel':
            actor.done = True
            actor.edit_message(localization.LangTuple('build', 'weapon_chosen'))
        else:
            actor.get_weapon(weapons.weapon_dict[info[3]](actor))
            actor.edit_message(localization.LangTuple('build', 'weapon_chosen'))
            actor.done = True
    elif object_type == 'info':
        if info[3] == 'abilities':
            abilities.ability_dict[info[4]](actor).pop_info(call)
        elif info[3] == 'weapon':
            weapons.weapon_dict[info[4]](actor).pop_info(call)

