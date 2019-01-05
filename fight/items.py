#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions, statuses, armors
import sys
import inspect
import random
import engine


class __InstantItem(standart_actions.InstantObject):
    core_types = ['item', 'fight']
    db_string = 'items'

    def act(self, action):
        if self.one_time:
            self.unit.items.remove(self)
        standart_actions.InstantObject.act(self, action)


class __OptionItem(standart_actions.SpecialObject):
    core_types = ['item', 'option', 'fight']
    db_string = 'items'

    def act(self, action):
        if len(action.info) > 4:
            if self.one_time:
                self.unit.items.remove(self)
        standart_actions.SpecialObject.act(self, action)


class MapItem(standart_actions.GameObject):
    core_types = ['item', 'map']
    db_string = 'items'

    def map_act(self, call):
        pass

    def map_available(self, call):
        pass


class TargetItem(standart_actions.TargetObject):
    core_types = ['item', 'target', 'fight']
    db_string = 'items'

    def act(self, action):
        if len(action.info) > 5:
            if self.one_time:
                self.unit.items.remove(self)
        standart_actions.TargetObject.act(self, action)


# -------------------------   Ресурсы мобов   --------------------------


class Resource(standart_actions.GameObject):
    core_types = ['item', 'resource']
    db_string = 'resources'
    resources = 5


class OldBone(Resource):
    name = 'old_bone'


class GoblinEar(Resource):
    name = 'goblin_ear'


class ZombieTooth(Resource):
    name = 'zombie_tooth'


class WormSkin(Resource):
    name = 'worm_skin'


class Bomb(__InstantItem):
    name = 'bomb'
    types = ['explosive', 'aoe']

    def activate(self, action):
        self.unit.wasted_energy += 2
        targets = [target for target in self.unit.targets() if 'dodge' not in target.action]
        damage = random.randint(2, 3)
        if not targets:
            self.string('fail', format_dict={'actor': self.unit.name})
        elif len(targets) == 1:
            self.string('special', format_dict={'actor': self.unit.name, 'target': targets[0].name, 'damage': damage})
            targets[0].receive_damage(damage)
        else:
            targets = random.sample(set(targets), 2)
            for target in targets:
                target.receive_damage(damage)
            self.string('use', format_dict={'actor': self.unit.name, 'target_0': targets[0].name,
                                            'target_1': targets[1].name, 'damage': damage})

    def available(self):
        if self.unit.energy > 1:
            return True
        return False


class ThrowingKnife(TargetItem):
    name = 'throwknife'
    types = ['blade']

    def targets(self):
        return self.unit.targets()

    def activate(self, action):
        energy = self.unit.energy if self.unit.energy < 7 else 6
        modifier = self.unit.range_accuracy - action.target.evasion + energy + 5
        damage = engine.damage_roll(1, modifier)
        if damage:
            action.target.receive_damage(1)
            statuses.Bleeding(action.target)
            if 'alive' in action.target.types:
                self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
            else:
                self.string('special', format_dict={'actor': self.unit.name, 'target': action.target.name})
        else:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name})
        self.unit.wasted_energy += 2

    def available(self):
        if self.unit.energy > 1:
            return True
        return False


class Adrenalin(__InstantItem):
    name = 'adrenalin'
    types = ['drug']
    order = 2
    full = False

    def activate(self, action):
        self.unit.energy += 3
        self.string('use', format_dict={'actor': self.unit.name})


class Bandages(TargetItem):
    core_types = ['item', 'map', 'fight', 'target']
    name = 'bandages'
    full = True

    def map_act(self, call):
        member = self.unit
        if self.map_available(call):
            if member.unit_dict['max_hp'] > member.unit_dict['hp']:
                member.unit_dict['hp'] += 1
                if member.unit_dict['hp'] < 3:
                    member.unit_dict['hp'] += 1
                member.alert('Вы вылечились', call)
                member.inventory.remove(self.id)
            else:
                member.alert('Вы не можете лечиться', call)

    def map_available(self, call):
        if 'hp' in self.unit.unit_dict.keys() and 'max_hp' in self.unit.unit_dict.keys():
            return True
        return False

    def targets(self):
        return [unit for unit in self.unit.team.units if unit.alive() and 'bleeding' in unit.statuses or
                unit.alive() and unit.hp < unit.max_hp]

    def activate(self, action):
        if action.target == self.unit:
            self.string('special', format_dict={'actor': self.unit.name, 'target': action.target.name})
        else:
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
        try:
            del action.target.statuses['bleeding']
        except:
            pass
        action.target.change_hp(1)


class Stimulator(TargetItem):
    name = 'stimulator'
    types = ['drug']
    order = 2
    full = False
    effect = False

    def targets(self):
        return [unit for unit in self.unit.team.units if unit.alive() and 'alive' in unit.types]

    def activate(self, action):
        if action.target == self.unit:
            self.string('special', format_dict={'actor': self.unit.name, 'target': action.target.name})
        else:
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
        action.target.change_hp(2)
        action.target.boost_attribute('hp', 2)
        statuses.CustomStatus(unit=action.target, delay=2, func=self.wear_off, order=39)
        statuses.CustomStatus(unit=action.target, delay=3, func=self.wear_off, order=39)
        self.unit = action.target

    def wear_off(self):
        self.string('end', format_dict={'actor': self.unit.name})
        self.unit.boosted_attributes['hp'] -= 1
        if self.unit.hp > 1:
            self.unit.hp_delta -= 1


class Resources(standart_actions.GameObject):
    name = 'resources'
    types = ['stack']


class Chitin(TargetItem):
    name = 'chitin'
    types = ['drug']
    order = 2
    full = False

    def __init__(self, unit=None, obj_dict=None):
        TargetItem.__init__(self, unit=unit, obj_dict=obj_dict)
        self.armor = None

    def activate(self, action):
        if action.target == self.unit:
            self.string('use', format_dict={'actor': self.unit.name})
        else:
            self.string('special', format_dict={'actor': self.unit.name, 'target': action.target.name})
        self.unit = action.target
        statuses.PermaStatus(unit=action.target, delay=2, func=self.protect, order=39, name='chitin_protect')
        statuses.CustomStatus(unit=action.target, delay=2, func=self.wear_off, order=41, name='chitin_delay')

    def wear_off(self):
        self.string('end', format_dict={'actor': self.unit.name})
        statuses.Stun(self.unit)

    def protect(self):
        if self.unit.dmg_received:
            prevented_damage = 2 if self.unit.dmg_received > 1 else 1
            self.unit.dmg_received -= prevented_damage
            self.string('fail', format_dict={'actor': self.unit.name, 'prevented_damage': prevented_damage})

    def targets(self):
        return [*[unit for unit in self.unit.team.units], *self.unit.melee_targets]


class Psycho(__InstantItem):
    name = 'psycho'
    types = ['drug']
    order = 2
    full = False

    def activate(self, action):
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.Buff(unit=self.unit, attr='damage', length=2, value=3)
        statuses.CustomStatus(unit=self.unit, delay=1, func=self.wear_off, order=40, name='psycho_delay')

    def wear_off(self):
        self.string('end', format_dict={'actor': self.unit.name})
        self.unit.hp_delta -= 1


class Jet(__InstantItem):
    name = 'jet'
    types = ['drug']
    order = 2
    full = False

    def activate(self, action):
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.CustomStatus(unit=self.unit, delay=2, func=self.wear_off, order=41)

    def wear_off(self):
        self.string('end', format_dict={'actor': self.unit.name})
        self.unit.energy = self.unit.max_energy


class Shield(TargetItem):
    name = 'shield'
    order = 21
    full = True

    def targets(self):
        return self.actor.team.actors

    def activate(self, action):
        if action.target == self.actor:
            self.string('special', format_dict={'actor': self.actor.name, 'target': action.target.name})
        else:
            self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name})
        self.actor = action.target
        self.actor.fight.edit_queue(standart_actions.Custom(self.wear_off, order=40, actor=self.actor))

    def wear_off(self):
        self.actor.dmg_received = 0


class FlashBomb(TargetItem):
    name = 'flashbomb'
    order = 2
    full = True

    def targets(self):
        return self.actor.targets()

    def activate(self, action):
        self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name})
        action.target.energy -= 6


class Molotov(__InstantItem):
    name = 'molotov'
    order = 5
    full = True

    def activate(self, action):
        targets = self.unit.targets()
        if len(targets) == 1:
            self.string('special', format_dict={'actor': self.unit.name, 'targets': targets[0].name})
        else:
            targets = random.sample(targets, 2)
            self.string('use', format_dict={'actor': self.unit.name,
                                            'target_0': targets[0].name,
                                            'target_1': targets[1].name})
        for target in targets:
            statuses.Burning(target)


class SmokeBomb(__InstantItem):
    name = 'smokebomb'
    order = 0
    full = True

    def activate(self, action):
        self.string('use', format_dict={'actor': self.actor.name})
        for actor in self.actor.fight.actors:
            statuses.Buff(actor, 'range_accuracy', -6, 2)
            statuses.Buff(actor, 'melee_accuracy', -4, 2)


class Mine(__OptionItem):
    name = 'mine'
    types = ['explosive', 'aoe']
    full = True

    def activate(self, action):
        delay = int(action.info[-1])
        statuses.CustomStatus(self.actor, 5, delay, self.blow_up, permanent=True)
        self.string('special', format_dict={'actor': self.actor.name})

    def blow_up(self):
        targets = [target for target in self.actor.targets()]
        damage = 3
        if len(targets) == 1:
            self.string('fail', format_dict={'actor': self.actor.name, 'target': targets[0].name, 'damage': damage})
            targets[0].receive_damage(damage)
        else:
            targets = random.sample(set(targets), 2)
            for target in targets:
                target.receive_damage(damage)
            self.string('use', format_dict={'actor': self.actor.name, 'target_0': targets[0].name,
                                            'target_1': targets[1].name, 'damage': damage})

    def options(self):
        return [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')]


class Dynamite(__OptionItem):
    name = 'dynamite'
    types = ['explosive', 'aoe', 'unique']
    full = False

    def activate(self, action):
        delay = int(action.info[-1])
        statuses.CustomStatus(self.actor, 5, delay, self.blow_up, permanent=True)
        self.string('special', format_dict={'actor': self.actor.name})

    def blow_up(self):
        targets = [target for target in self.actor.fight.alive_actors()]
        damage = 5
        for target in targets:
            target.receive_damage(damage)
        self.string('use', format_dict={'actor': self.actor.name, 'damage': damage})

    def options(self):
        return [('2', '2'), ('3', '3'), ('4', '4')]


items_dict = {value.name: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.name is not None}
items_list = {value for key, value in items_dict.items() if 'unique' not in value.types}
for k, v in items_dict.items():
    standart_actions.object_dict[k] = v
