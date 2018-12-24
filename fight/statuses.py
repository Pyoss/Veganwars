#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions
from locales import emoji_utils
import random
# 1-20 До эффектов, 21-40 - эффекты, 41-60 результаты
# 31-40 - неблокирующийся урон


class Status(standart_actions.GameObject):
    core_types = ['status']
    db_string = 'statuses'
    effect = True

    def __init__(self, unit, acting=False):
        standart_actions.GameObject.__init__(self, unit)
        if self.name not in unit.statuses:
            unit.statuses[self.name] = self
            if acting:
                self.act()
        else:
            self.reapply(unit.statuses[self.name])

    def act(self):
        self.unit.fight.edit_queue(self)

    def available(self):
        return False

    def reapply(self, parent):
        pass

    def finish(self):
        del self.unit.statuses[self.name]

    def menu_string(self):
        return False


class CustomStatus(Status):

    def __init__(self, unit, order, delay, func, args=None, name=None, permanent=False, acting=False):
        self.name = 'custom_' + str(id(self)) if name is None else name
        self.args = [] if args is None else args
        self.order = order
        self.delay = delay
        self.func = func
        Status.__init__(self, unit, acting=acting)
        if permanent:
            self.types.append('permanent')

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.func(*self.args)
            self.finish()

    def reapply(self, parent):
        self.unit.statuses[self.name] = self


class PermaStatus(CustomStatus):
    def activate(self, action=None):
        self.delay -= 1
        self.func(*self.args)
        if self.delay <= 0:
            self.finish()


class Buff:
    def __init__(self, unit, attr, value, length):
        self.value = value
        self.attr = attr
        self.unit = unit
        setattr(self.unit, self.attr, getattr(self.unit, self.attr) + self.value)
        self.unit.boost_attribute(attr, value)
        CustomStatus(unit, delay=length-1, func=self.stop_buff, order=60, acting=True)

    def stop_buff(self):
        setattr(self.unit, self.attr, getattr(self.unit, self.attr) - self.value)
        self.unit.boosted_attributes[self.attr] -= self.value


class Bleeding(Status):
    name = 'bleeding'
    order = 21

    def __init__(self, unit, strength=4):
        if 'alive' in unit.types:
            self.strength = strength
            Status.__init__(self, unit)

    def reapply(self, parent):
        parent.strength += self.strength

    def activate(self, action=None):
        if 'idle' in self.unit.action:
            self.strength -= 3
        else:
            self.strength += 2

        if self.strength >= 9:
            self.unit.hp_delta -= 1
            self.string('damage', format_dict={'actor': self.unit.name})
            self.finish()
        elif self.strength <= 0:
            self.string('end', format_dict={'actor': self.unit.name})
            self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['bleeding_em'] + str(self.strength)


class Poison(Status):
    name = 'poison'
    order = 21

    def __init__(self, unit, strength=1):
        self.strength = strength
        Status.__init__(self, unit)
        if self.name not in unit.statuses:
            unit.statuses[self.name] = self

    def reapply(self, parent):
        parent.strength += 1

    def activate(self, action=None):
        self.unit.waste_energy(self.strength)
        self.string('use', format_dict={'actor': self.unit.name, 'strength': self.strength})
        self.strength -= 1
        if self.strength == 0:
            self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['poisoned_em'] + str(self.strength)


class Burning(Status):
    name = 'burning'
    order = 21

    def __init__(self, actor, stacks=1):
        self.stacks = stacks
        self.turns = 3
        Status.__init__(self, actor, acting=True)

    def reapply(self, parent):
        parent.stacks += self.stacks
        parent.turns = 3

    def activate(self, action=None):
        if 'skip' in self.unit.action:
            self.string('end', format_dict={'actor': self.unit.name})
            self.finish()
        else:
            self.turns -= 1
            self.unit.dmg_received += self.stacks
            self.string('damage', format_dict={'actor': self.unit.name, 'damage_dealt': self.stacks})
            if self.turns == 0:
                self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['fire_em'] + str(self.stacks)


class AFK(Status):
    name = 'afk'
    order = 21

    def __init__(self, actor, stacks=1):
        self.stacks = stacks
        Status.__init__(self, actor, acting=True)

    def reapply(self, parent, stacks=1):
        parent.stacks += stacks

    def activate(self, action=None):
        if self.stacks > 3:
            self.unit.fight.edit_queue(standart_actions.Suicide(self.unit, self.unit.fight))

    def menu_string(self):
        return emoji_utils.emote_dict['afk_em'] + str(self.stacks)


class Stun(Status):
    name = 'stun'
    order = 60
    effect = False

    def __init__(self, actor, turns=1):
        self.turns = turns
        if 'stun' not in actor.disabled:
            actor.disabled.append('stun')
            Status.__init__(self, actor)

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        self.turns -= 1
        if self.turns == 0:
            self.string('end', format_dict={'actor': self.unit.name})
            self.unit.disabled.remove('stun')
            self.finish()


class Crippled(Status):
    name = 'cripple'
    order = 40

    def __init__(self, unit):
        Status.__init__(self, unit)
        self.max_toughness = 0
        if hasattr(unit, 'toughness'):
            self.max_toughness = unit.toughness
        unit.change_attribute('toughness', -1)
        self.strength = 1
        if not hasattr(unit, 'toughness'):
            unit.change_attribute('wounds', -1)

    def reapply(self, parent):
        if not hasattr(parent.unit, 'toughness'):
            parent.unit.change_attribute('wounds', -1)
        elif parent.max_toughness - parent.unit.toughness < 4 and parent.unit.toughness > 1:
            parent.unit.change_attribute('toughness', -1)
            parent.strength += 1

    def menu_string(self):
        return emoji_utils.emote_dict['crippled_em'] + str(self.strength)

    def activate(self, action=None):
        pass


class Victim(Status):
    name = 'victim'
    order = 40

    def __init__(self, actor, turns=1):
        self.turns = turns
        actor.disabled = True
        Status.__init__(self, actor)

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        self.turns -= 1
        if self.turns == 0:
            self.actor.dmg_received = self.actor.dmg_received * 2
            self.finish()


class Confused(Status):
    name = 'confused'
    order = 40

    def __init__(self, actor, turns=2):
        self.turns = turns
        self.minus = 4
        if actor.recovery_energy - self.minus < 1:
            self.minus = actor.recovery_energy - 1
        actor.recovery_energy -= self.minus
        Status.__init__(self, actor)

    def reapply(self, parent):
        parent.turns += self.turns

    def activate(self, action=None):
        self.turns -= 1
        if self.turns == 0:
            self.actor.recovery_energy += self.minus
            self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['confused_em'] + str(self.turns)

