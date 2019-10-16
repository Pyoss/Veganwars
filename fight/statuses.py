#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions
from locales import emoji_utils, localization
import engine
import random
import inspect, sys
from bot_utils import keyboards
# 1-20 До эффектов, 21-40 - эффекты, 41-60 результаты
# 31-40 - неблокирующийся урон


class Status(standart_actions.GameObject):
    core_types = ['status']
    db_string = 'statuses'
    effect = True
    passive = False
    action_order = 5
    action_type = []

    def to_dict(self):
        return False

    def __init__(self, unit, acting=False, **kwargs):
        standart_actions.GameObject.__init__(self, unit)
        self.additional_buttons_actions = None
        self.kwargs = kwargs
        self.handle_dict = {}
        if unit is not None and self.name not in unit.statuses:
            unit.statuses[self.name] = self
            print('Инициирован статус {} для {}...'.format(self.name, unit.name))
            if acting:
                self.act()
        elif unit is not None:
            self.reapply(unit.statuses[self.name])

    def create_status_button(self, button_name, lang_tuple):
        button = keyboards.FightButton(lang_tuple, self.unit, 'status-action', self.name, button_name)
        return button

    def add_additional_buttons(self):

        # Добавление дополнительных действий, доступных при наличии статуса
        buttons = []
        if self.additional_buttons_actions is not None:
            for action_tpl in self.additional_buttons_actions:
                button = action_tpl[0]
                action = action_tpl[1]
                lang_tuple = action_tpl[2]
                buttons.append((3, self.create_status_button(button, lang_tuple)))
                self.handle_dict[button] = action
        return buttons

    def handle(self, call_data):
        self.handle_dict[call_data[-1]]()

    def act(self, action=None):
        if not self.passive:
            self.unit.fight.edit_queue(self)

    def available(self):
        return False

    def reapply(self, parent):
        pass

    def finish(self):
        print('Удаляется статус {} для {}...'.format(self.name, self.unit.name))
        try:
            del self.unit.statuses[self.name]
        except KeyError:
            pass

    def menu_string(self):
        return False

    def map_string(self):
        return False


class CustomStatus(Status):
    action_type = []

    def __init__(self, unit, order, delay, func, args=None, name=None, permanent=False, acting=False,
                 additional_buttons_actions=None, emoji=None):
        self.name = 'custom-' + str(id(self)) if name is None else name
        self.args = [] if args is None else args
        self.order = order
        self.delay = delay
        self.func = func
        self.unit = unit
        self.emote = emoji

        Status.__init__(self, unit, acting=acting)
        self.additional_buttons_actions = additional_buttons_actions
        if permanent:
            self.types.append('permanent')

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.func(*self.args)
            self.finish()

    def reapply(self, parent):
        self.unit.statuses[self.name] = self

    def menu_string(self):
        return False if self.emote is None else self.emote


class CustomPassive(Status):
    order = 60

    def __init__(self, unit, types=None, name=None, delay=1, **kwargs):
        self.name = 'custom_' + str(id(self)) if name is None else name
        Status.__init__(self, unit, acting=True,  **kwargs)
        self.delay = delay
        self.types = [] if types is None else types

    def act(self, action=None):
        if action is not None:
            func = self.kwargs['func']
            option = self.kwargs['option']
            func(action, option)
        else:
            self.unit.fight.edit_queue(self)

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.finish()


class PermaStatus(CustomStatus):
    def activate(self, action=None):
        self.delay -= 1
        self.func(*self.args)
        if self.delay <= 0:
            self.finish()


class OnHitStatus(Status):
    core_types = ['status', 'on_hit']
    db_string = 'statuses'
    order = 60

    def __init__(self, unit, delay=1, acting=False):
        self.delay = delay
        Status.__init__(self, unit, acting=acting)

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.finish()


class BeforeHit(Status):
    core_types = ['status', 'before_hit']
    db_string = 'statuses'
    order = 60

    def __init__(self, unit, delay=1, acting=False):
        self.delay = delay
        Status.__init__(self, unit, acting=acting)

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.finish()


class ReceiveHitStatus(Status):
    core_types = ['status', 'receive_hit']
    db_string = 'statuses'
    order = 60

    def __init__(self, unit, delay=1, acting=False):
        self.delay = delay
        Status.__init__(self, unit, acting=acting)

    def activate(self, action=None):
        self.delay -= 1
        if self.delay <= 0:
            self.finish()


class ReceiveSpellStatus(ReceiveHitStatus):
    core_types = ['status', 'receive_spell']


class Running(OnHitStatus):
    name = 'running'

    def act(self, action=None):
        if action is not None:
            if action.weapon.melee and action.dmg_done > 0 and any(ability.name == 'charge'
                                                                   for ability in self.unit.abilities):
                action.dmg_done += 1
                if 'two-handed' in self.unit.weapon.types:
                    action.dmg_done += 1
                action.to_emotes(emoji_utils.emote_dict['exclaim_em'])
        else:
            self.unit.fight.edit_queue(self)

    def menu_string(self):
        return emoji_utils.emote_dict['running_em']


class Retreating(BeforeHit):
    name = 'retreating'
    core_types = ['status', 'before_hit', 'on_hit']

    def __init__(self, unit, delay=1, acting=False):
        BeforeHit.__init__(self, unit, delay=1, acting=False)
        self.switch = False

    def act(self, action=None):
        if action is not None:
            if not action.weapon.melee:
                if not self.switch:
                    self.unit.range_accuracy -= 6
                    self.switch = True
                else:
                    self.unit.range_accuracy += 6
                    self.switch = False

        else:
            self.unit.fight.edit_queue(self)

    def menu_string(self):
        return emoji_utils.emote_dict['retreating_em']


class Flying(ReceiveHitStatus):
    name = 'flying'

    def act(self, action=None):
        if action is not None:
            if action.weapon.melee and action.dmg_done > 0:
                action.dmg_done = 0
        else:
            self.unit.fight.edit_queue(self)

    def menu_string(self):
        return '💨'


class Buff:
    name = None

    def __init__(self, unit, attr, value, length, emoji=None):
        self.value = value
        self.attr = attr
        self.unit = unit
        setattr(self.unit, self.attr, getattr(self.unit, self.attr) + self.value)
        self.unit.boost_attribute(attr, value)
        CustomStatus(unit, delay=length, func=self.stop_buff, order=59, acting=True,
                     name='buff_{}_{}'.format(attr, engine.rand_id()), emoji=emoji)

    def stop_buff(self):
        setattr(self.unit, self.attr, getattr(self.unit, self.attr) - self.value)
        self.unit.boosted_attributes[self.attr] -= self.value


class Bleeding(Status):
    name = 'bleeding'
    order = 22

    def __init__(self, unit, strength=5):
        if 'alive' in unit.types:
            self.strength = strength
            Status.__init__(self, unit)

    def reapply(self, parent):
        parent.strength += self.strength

    def activate(self, action=None):
        if self.name not in self.unit.statuses:
            return False
        if 'idle' in self.unit.action:
            self.strength -= 3
        else:
            self.strength += 3

        if self.strength >= 9:
            self.unit.hp_delta -= 1
            self.string('damage', format_dict={'actor': self.unit.name})
            self.finish()
        elif self.strength <= 0:
            self.string('end', format_dict={'actor': self.unit.name})
            self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['bleeding_em'] + str(self.strength)


class Undying(Status):
    name = 'undying'
    order = 39

    def __init__(self, unit):
        Status.__init__(self, unit)
        self.ready_turn = 0
        self.cd = 4

    def activate(self, action=None):
        hp_delta = self.unit.hp_delta - (bool(self.unit.dmg_received) + self.unit.dmg_received // self.unit.toughness)
        if hp_delta <= -self.unit.hp and self.ready_turn <= self.unit.fight.turn:
            self.unit.hp_delta += 1 - hp_delta - self.unit.hp
            standart_actions.Custom(self.string, 'use', unit=self.unit, format_dict={'actor': self.unit.name})
            self.ready_turn = self.unit.fight.turn + self.cd

    def menu_string(self):
        return emoji_utils.emote_dict['undying_em'] if self.ready_turn <= self.unit.fight.turn else None


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


class Casting(Status):
    name = 'casting'
    order = 60

    def __init__(self, unit, spell_id, delay=1):
        Status.__init__(self, unit, acting=True)
        self.spell_id = spell_id
        self.delay = delay
        self.unit.disabled.append(self.name)

    def activate(self, action=None):
        if len(self.unit.disabled) > 1 or len(self.unit.disarmed) > 0:
            self.finish()
        self.delay -= 1
        if self.delay <= 0:
            self.finish()

    def finish(self):
        if 'casting' in self.unit.disabled:
            self.unit.disabled.remove(self.name)
        Status.finish(self)


class Burning(Status):
    name = 'burning'
    order = 21

    def __init__(self, actor, stacks=1):
        self.stacks = stacks
        Status.__init__(self, actor, acting=True)

    def reapply(self, parent):
        parent.stacks += self.stacks

    def activate(self, action=None):
        if 'skip' in self.unit.action:
            self.string('end', format_dict={'actor': self.unit.name})
            self.finish()
        else:
            if 'chilled' in self.unit.statuses:
                if self.unit.statuses['chilled'].stacks < self.stacks:
                    self.stacks -= self.unit.statuses['chilled'].stacks
                    self.unit.statuses['chilled'].finish()
                else:
                    self.unit.statuses['chilled'].stacks -= self.stacks
                    self.finish()
                    return False
            if self.stacks:
                self.unit.receive_damage(self.stacks)
                self.string('damage', format_dict={'actor': self.unit.name, 'damage_dealt': self.stacks})
                self.unit.death_lang_tuple = {'source': self,
                                              'target': self.unit}
            self.stacks -= 1
            if self.stacks < 1:
                self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['fire_em'] + str(self.stacks)


class Chilled(Status):
    name = 'chilled'
    order = 21

    def __init__(self, actor, stacks=1):
        if 'frozen' not in actor.statuses:
            self.stacks = stacks
            Status.__init__(self, actor, acting=True)

    def reapply(self, parent):
        parent.stacks += self.stacks

    def activate(self, action=None):
        if 'burning' in self.unit.statuses:
            if self.unit.statuses['burning'].stacks < self.stacks:
                self.stacks -= self.unit.statuses['burning'].stacks
                self.unit.statuses['burning'].finish()
            else:
                self.unit.statuses['burning'].stacks -= self.stacks
                self.finish()
                return False
        self.unit.waste_energy(self.stacks)
        if self.unit.energy - self.unit.wasted_energy < 0:
            self.finish()
            freeze = Frozen(self.unit)
            freeze.string('use', format_dict={'actor': self.unit.name})
        elif self.stacks:
            self.string('damage', format_dict={'actor': self.unit.name, 'energy_lost': self.stacks})
        self.stacks -= 1
        if self.stacks < 1:
            self.finish()

    def menu_string(self):
        return emoji_utils.emote_dict['ice_em'] + str(self.stacks)


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
            standart_actions.Custom(self.string, 'use', order=30, unit=self.unit, format_dict={'actor': self.unit.name})

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        self.turns -= 1
        if self.turns == 0:
            self.string('end', format_dict={'actor': self.unit.name})
            self.unit.disabled.remove('stun')
            self.finish()


class Prone(Status):
    name = 'prone'
    order = 60
    action_order = 20
    effect = False

    def __init__(self, actor):
        if 'animal' not in actor.types:
            return
        if 'prone' not in actor.disarmed:
            actor.disarmed.append('prone')
        if 'prone' not in actor.rooted:
            Status.__init__(self, actor)
            actor.rooted.append('prone')
            setattr(actor, 'evasion', getattr(actor, 'evasion') - 5)
            self.unit.boost_attribute('evasion', - 5)
            self.additional_buttons_actions = [('free', self.finish,
                                                localization.LangTuple('buttons', 'get_up'))]
            self.handle_dict['free'] = self.finish
            standart_actions.Custom(self.string, 'use', order=30, unit=self.unit, format_dict={'actor': self.unit.name})

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        pass

    def finish(self):
        setattr(self.unit, 'evasion', getattr(self.unit, 'evasion') + 5)
        self.unit.boosted_attributes['evasion'] += 5
        self.unit.string('get_up', format_dict={'actor': self.unit.name})
        self.unit.disarmed.remove('prone')
        self.unit.rooted.remove('prone')
        Status.finish(self)

    def menu_string(self):
        return emoji_utils.emote_dict['prone_em']


class Stealthed(Status):
    name = 'stealthed'
    order = 40
    effect = False

    def __init__(self, actor):
        self.effectiveness = random.choice([4, 8, 12]) - actor.speed_penalty()
        Status.__init__(self, actor, acting=False)
        Buff(self.unit, 'evasion', self.effectiveness, 2)

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        self.finish()

    def menu_string(self):
        return '👁‍🗨' + str(self.effectiveness)


class LostWeapon(Status):
    name = 'weapon-loss'
    order = 60
    action_order = 20
    effect = False

    def __init__(self, actor):
        Status.__init__(self, actor)
        self.unit.lost_weapon = self.unit.weapon
        self.unit.weapon = self.unit.default_weapon
        self.additional_buttons_actions = [('pick-up', self.finish,
                                            localization.LangTuple('statuses_weapon-loss', 'damage'))]
        self.handle_dict['pick-up'] = self.finish
        standart_actions.Custom(self.string, 'use', order=30, unit=self.unit, format_dict={'actor': self.unit.name})

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        pass

    def finish(self):
        self.unit.weapon = self.unit.lost_weapon
        self.string('end', format_dict={'actor': self.unit.name})
        Status.finish(self)

    def menu_string(self):
        return emoji_utils.emote_dict['weapon_loss_em']


class Frozen(Status):
    name = 'frozen'
    order = 60
    effect = False

    def __init__(self, actor, turns=1):
        self.turns = turns
        if 'frozen' not in actor.disabled:
            actor.disabled.append('frozen')
            Status.__init__(self, actor)

    def reapply(self, parent):
        pass

    def activate(self, action=None):
        self.turns -= 1
        if self.turns == 0:
            self.string('end', format_dict={'actor': self.unit.name})
            self.unit.disabled.remove('frozen')
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
        elif parent.unit.toughness > 2:
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


class Exhausted(Status):
    name = 'exhausted'

    def __init__(self, actor=None, obj_dict=None):
        Status.__init__(self, actor)
        if actor is not None:
            setattr(self.unit, 'max_energy', getattr(self.unit, 'max_energy',) - 1)
            setattr(self.unit, 'melee_accuracy', getattr(self.unit, 'melee_accuracy',) - 1)
            setattr(self.unit, 'range_accuracy', getattr(self.unit, 'range_accuracy',) - 1)
            self.unit.boost_attribute('max_energy', -1)
            self.unit.boost_attribute('melee_accuracy', -1)
            self.unit.boost_attribute('range_accuracy', -1)

    def to_dict(self):
        return standart_actions.GameObject.to_dict(self)

    def menu_string(self):
        return '😩'

    def map_string(self):
        return '[Устал]'

    def activate(self, action=None):
        pass


class Wounded(Status):
    name = 'wounded'

    def __init__(self, actor=None, obj_dict=None):
        Status.__init__(self, actor)
        if actor is not None:
            setattr(self.unit, 'toughness', 1)

    def to_dict(self):
        return standart_actions.GameObject.to_dict(self)

    def menu_string(self):
        return '🤕'

    def map_string(self):
        return '[Ранен]'

    def activate(self, action=None):
        pass


statuses_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None}


for k, v in statuses_dict.items():
    standart_actions.object_dict[k] = v