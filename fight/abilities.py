#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions, statuses, items, weapons
from locales import emoji_utils, localization
from bot_utils import keyboards
import random
import engine
import inspect
import sys


class Ability(standart_actions.GameObject):
    core_types = ['ability']
    db_string = 'abilities'
    prerequisites = {}

    def __init__(self, unit=None, obj_dict=None):
        standart_actions.GameObject.__init__(self, unit=unit, obj_dict=obj_dict)
        self.lvl = obj_dict.get('lvl', 1) if obj_dict is not None else 1

    def to_dict(self):
        this_dict = standart_actions.GameObject.to_dict(self)
        this_dict['lvl'] = self.lvl
        return this_dict

    def user_available(self, user):
        user_abilities = user.get_abilities()
        if self.prerequisites:
            for key in self.prerequisites:
                if not any(ability['name'] == key and ability['lvl'] == self.prerequisites[key] for ability in user_abilities):
                    return False
        return True

    def to_user(self, user):
        user_abilities = user.get_abilities()
        user_abilities.append(self.to_dict())
        user.set_abilities(user_abilities)

    def error_text(self):
        if not self.ready():
            return 'Способность еще не готова'

    def available(self):
        if not self.ready():
            return False
        return True


class InstantAbility(standart_actions.InstantObject, Ability):
    core_types = ['ability', 'instant']
    db_string = 'abilities'


class TargetAbility(standart_actions.TargetObject, Ability):
    core_types = ['ability', 'target']
    db_string = 'abilities'


class OptionAbility(standart_actions.SpecialObject, Ability):
    core_types = ['ability', 'option']
    db_string = 'abilities'


class StartAbility(Ability):
    core_types = ['ability', 'start']
    active = False

    def start_act(self):
        pass


class BuildAbility(Ability):
    core_types = ['ability', 'build']
    active = False

    def build_act(self):
        pass


class Passive(Ability):
    core_types = ['ability', 'passive']
    active = False

    def act(self, action=None):
        self.unit.fight.action_queue.append(self)


class OnHit(Ability):
    core_types = ['ability', 'on_hit']
    active = False

    def act(self, action):
        pass


class ReceiveHit(Ability):
    core_types = ['ability', 'receive_hit']
    active = False

    def act(self, action):
        pass


# Способность Уворот: повышает шанс увернуться от атаки. Увеличивает параметр "evasion"
#  в начале хода и уменьшает в конце
class Dodge(InstantAbility):
    name = 'dodge'
    types = ['dodge']
    order = 1
    cd = 2

    def activate(self, action):
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.Buff(self.unit, 'evasion', 6, 1)

    def available(self):
        if not self.ready():
            return False
        if 'running' in self.unit.statuses:
            return False
        if self.unit.rooted:
            return False
        return True

    def error_text(self):
        if not self.ready():
            return 'Способность еще не готова'
        if 'running' in self.unit.statuses:
            return 'Вы не можете уворачиваться после движения'
        if self.unit.rooted:
            print(self.unit.rooted)
            return 'Вы обездвижены'


class SpellCaster(OptionAbility):
    name = 'spellcast'
    types = ['spell']
    order = 0
    start_sigils = [emoji_utils.emote_dict['self_em'], emoji_utils.emote_dict['strength_em'], emoji_utils.emote_dict['palm_em']]
    buff_sigils = [emoji_utils.emote_dict['wind_em'], emoji_utils.emote_dict['earth_em'], emoji_utils.emote_dict['random_em']]
    end_sigils = [emoji_utils.emote_dict['spark_em'], emoji_utils.emote_dict['ice_em'], emoji_utils.emote_dict['ignite_em']]

    def act(self, action):
        if self.check_final(action.info):
            spell_tuple = tuple(action.info[-1].split('-'))
            from fight import spells
            if spell_tuple in spells.spell_dict and len(action.info) < 7:
                if spells.spell_dict[spell_tuple].targetable:
                    self.ask_target(action.info[-1])
                    return True

            self.act_options(action)
            for action_type in action.action_type:
                self.unit.action.append(action_type)
            self.on_cd()
            self.ask_action()
        else:
            self.ask_options(action)

    def ask_target(self, spell_tuple):
        self.unit.active = True
        string = 'Выберите цель.'
        targets = [*self.unit.targets(), *self.unit.get_allies()]
        buttons = []
        for target in targets:
            buttons.append(keyboards.FightButton((target.name if isinstance(target.name, str)
                                                                      else target.name.str(self.unit.controller.lang)),
                                                 self.unit,
                                                 self.types[0],
                                 self.name, str(target), spell_tuple, named=True))
        buttons.append(keyboards.MenuButton(self.unit, 'back'))
        keyboard = keyboards.form_keyboard(*buttons)
        self.unit.controller.edit_message(string, reply_markup=keyboard)

    def activate(self, action):
        spell_list = tuple(action.info[-1].split('-'))
        from fight import spells
        if spell_list in spells.spell_dict:
            spells.spell_dict[spell_list](self.unit).activate(action)
        else:
            self.fail()

    def fail(self):
        self.string('fail', format_dict={'actor':self.unit.name})

    def check_final(self, info):
        spell_list = info[-1].split('-')
        if spell_list[-1] in self.end_sigils or len(spell_list) > 2:
            return True
        return False

    @staticmethod
    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def options(self):
        sigils = [*self.start_sigils, *self.buff_sigils, *self.end_sigils]
        sigils = list(self.chunks(sigils, 3))
        end_sigils = []
        for i in range(len(sigils[0])):
            end_sigils = [*end_sigils, *[sigil[i] for sigil in sigils]]
        return [(x, x) for x in end_sigils]

    def options_keyboard(self, action=None):
        if action.info[-1] == 'spellcast':
            return OptionAbility.options_keyboard(self, action=action)
        else:
            current_spells = action.info[-1].split('-')
            return [keyboards.OptionObject(self, name=option[0], option='-'.join([*current_spells, option[1]])) for option in self.options()]

    def ask_options(self, action=None):
        self.unit.active = True
        keyboard = self.target_keyboard(action, row_width=3)
        current_spells = action.info[-1].split('-')
        current_spells = ['-'] if current_spells == ['spellcast'] else current_spells
        self.unit.controller.edit_message(localization.LangTuple(self.table_row, 'options', format_dict={'spells':' '.join(current_spells)}),
                               reply_markup=keyboard)

    def available(self):
        if self.unit.energy > 1:
            return True
        return False

    def error_text(self):
        if self.unit.energy < 1:
            return 'У вас недостаточно энергии'




################################# НИЖЕ НИЧЕГО НЕ ПРОВЕРЕНО #######################################
# Способность Садист: прибавляет энергию, если у текущей цели отнялись жизни.
class Sadist(Passive):
    name = 'sadist'
    order = 41

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.hp = 0

    def act(self, action=None):
        standart_actions.Custom(self.set_hp, order=40, actor=self.actor)
        self.actor.fight.action_queue.append(self)

    def activate(self, action=None):
        if self.hp > 0:
            if self.hp > self.actor.target.hp:
                if self.actor.wasted_energy > 0:
                    self.actor.wasted_energy -= 1
                else:
                    self.actor.energy += 1
                self.string('use', format_dict={'actor': self.actor.name})
        self.hp = 0

    def set_hp(self):
        if self.actor.target is not None:
            self.hp = self.actor.target.hp


# Способность Гипноз: меняет текущую цель указанного игрока на одного из противников использующего.
class Hypnotize(TargetAbility):
    name = 'hypnotize'
    order = 1
    cd = 4

    def targets(self):
        return self.actor.targets()

    def activate(self, action):
        if action.target.target is not None:
            new_target = random.choice(self.actor.targets())
            action.target.target = new_target
            self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name,
                                            'new_target': new_target.name})
        else:
            self.string('fail', format_dict={'actor': self.actor.name, 'target': action.target.name})
        self.actor.wasted_energy += 3

    def available(self):
        return True if self.actor.energy >= 3 else False


# Способность Бицепс: Добавляет 25% вероятность нанести удвоенный урон при стандартной атаке
class Muscle(OnHit):
    name = 'muscle'
    types = ['not_range']

    def act(self, action):
        if engine.roll_chance(25) and action.weapon.melee:
            action.dmg_done *= 2
            action.to_emotes(emoji_utils.emote_dict['exclaim_em'])


# Способность Двужильность: жизни и стойкость в начале игры увеличены.
class Sturdy(StartAbility):
    types = ['build']
    name = 'sturdy'

    def build_act(self):
        self.actor.hp += 1
        self.actor.max_hp += 1
        self.actor.toughness += 3


# Способность Неторопливый: максимальная энергия увеличена, а скорость ее восстановления - уменьшена.
class Slow(StartAbility):
    name = 'slow'

    def start_act(self):
        self.actor.energy += 2
        self.actor.max_energy += 2
        self.actor.recovery_energy -= 2


# Способность Неторопливый: максимальная энергия увеличена, а скорость ее восстановления - уменьшена.
class Fat(StartAbility):
    name = 'fat'

    def start_act(self):
        self.actor.add_energy(-1)

    def build_act(self):
        self.actor.max_hp += 2
        self.actor.hp += 2


# Способность Запасливый: На 2 предмета больше в начале игры. Не можете уворачиваться.
class Items(BuildAbility):
    name = 'items'

    def build_act(self):
        item = random.sample(set([item for item in items.items_list if not any(item == it for it in self.actor.items)]),
                             2)
        for i in item:
            self.actor.items.append(i(self.actor))
        for ability in self.actor.abilities:
            if ability.name == 'dodge':
                self.actor.abilities.remove(ability)


# Способность Подрывник: Вы получаете динамит. Этот предмет не тратит хода, и наносит 5 урона всем
# игрокам через несколько ходов.
class Demoman(StartAbility):
    name = 'demoman'

    def build_act(self):
        self.actor.items.append(items.Dynamite(self.actor))


# Способность Прицел: увеличивает точность дальнего оружия на 2.
class Target(StartAbility):
    name = 'target'
    types = ['not_melee']

    def start_act(self):
        self.unit.range_accuracy += 2


# Способность Бронежилет: с 30% вероятностью снижает на 1 получаемые повреждения от атак.
class West(StartAbility):
    name = 'west'

    def start_act(self):
        self.actor.armor[self.name] = (1, 30)


class Revenge(Passive):
    name = 'revenge'
    types = ['not_solo']
    order = 41

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.dead_teammates = []

    def activate(self, action=None):
        if not self.actor.alive():
            return False
        for actor in self.actor.team.actors:
            if not actor.alive() and actor not in self.dead_teammates:
                self.string('use', format_dict={'actor': self.actor.name, 'dead': actor.name})
                self.actor.hp += 1
                self.actor.damage += 2
                self.dead_teammates.append(actor)


# Способность Пироман: увеличивает наносимый урон на один за каждого горящего человека в бою.
class Pyromaniac(Passive):
    name = 'pyromaniac'
    order = 41

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.bonus_damage = 0

    def activate(self, action=None):
        global_stacks = sum([actor.statuses['burning'].stacks
                             for actor in self.actor.fight.actors if 'burning' in actor.statuses and actor.alive()])
        self.bonus_damage = global_stacks
        if self.bonus_damage:
            self.string('use', format_dict={'actor': self.actor.name, 'bonus_damage': self.bonus_damage})
            self.actor.damage += self.bonus_damage
            statuses.CustomStatus(self.actor, delay=1, func=self.delete_bonus, order=40, name='pyromaniac_delay')

    def delete_bonus(self):
        self.actor.damage -= self.bonus_damage
        self.bonus_damage = 0


# Способность Наркоман: Точность уменьшена.
# При использовании любых препаратов точность и наносимый урон увеличивается на 1.
class Junkie(Passive):
    name = 'junkie'
    types = ['start']
    order = 1

    def start_act(self):
        self.actor.melee_accuracy -= 1
        self.actor.range_accuracy -= 1

    def build_act(self):
        self.actor.items.append(random.choice([item for item in [value for key, value in items.items_dict.items()
                                                                 if 'drug' in value.types]])(self.actor))

    def activate(self, action=None):
        if any('drug' in action.types for action in self.actor.actions()):
            self.activate_bonus()

    def activate_bonus(self):
        statuses.Buff(self.actor, 'melee_accuracy', 2, 1)
        statuses.Buff(self.actor, 'range_accuracy', 2, 1)
        statuses.Buff(self.actor, 'damage', 1, 1)
        self.string('use', format_dict={'actor': self.actor.name})


# Способность Вор: Вы можете попытаться забрать используемый противником предмет.
class Thief(TargetAbility):
    name = 'thief'
    order = 1
    cd = 1

    def targets(self):
        return self.actor.targets()

    def activate(self, action):
        items_to_steal = [action for action in action.target.actions() if 'item' in action.types]
        if items_to_steal:
            stopped_action = random.choice(items_to_steal)
            self.actor.fight.action_queue.action_list.remove(stopped_action)
            item = stopped_action.item
            self.actor.items.append(item)
            item.actor = self.actor
            self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name,
                                            'item': item.name_lang_tuple()})
        else:
            self.string('fail', format_dict={'actor': self.actor.name, 'target': action.target.name})
        self.actor.waste_energy(1)

    def available(self):
        return True if self.actor.energy >= 1 else False


# Способность Вор: Вы можете попытаться забрать используемый противником предмет.
class Thrower(TargetAbility):
    name = 'thrower'
    cd = 3
    order = 0

    def __init__(self, actor):
        TargetAbility.__init__(self, actor)
        self.energy = 2
        self.stun_chance = 35

    def targets(self):
        return self.actor.targets()

    def act_options(self, action):
        TargetAbility.act_options(self, action)
        self.actor.target = action.target

    def activate(self, action):
        class ThrowAttack(standart_actions.BaseAttack):
            def __init__(new):
                standart_actions.BaseAttack.__init__(new, self.actor, self.actor.fight, None)
                new.target = self.actor.target

            def activate(new):
                new.weapon = self.actor.weapon
                # Определение цели
                new.attack()
                new.on_attack()
                # Добавление описания в строку отчета
                new.string('')
                self.actor.lose_weapon()

            def string(new, hit_string):
                atk_action = 'use' if new.dmg_done > 0 else 'fail'
                if hit_string != '':
                    atk_action = hit_string + '_' + atk_action
                attack_dict = {'actor': self.actor.name, 'target': new.target.name,
                               'damage': new.dmg_done if not new.special_emotes else str(new.dmg_done) +
                               ''.join(new.special_emotes),
                               'weapon': localization.LangTuple(new.weapon.table_row,
                                                                'name' if not new.weapon.melee else 'with_name')}
                attack_tuple = localization.LangTuple(self.table_row, atk_action, attack_dict)
                new.fight.string_tuple.row(attack_tuple)

            def attack(new):
                # Вычисление нанесенного урона и трата энергии
                new.dmg_done = self.actor.weapon.get_damage(new.target)\
                    if self.actor.weapon.melee else weapons.Weapon(self.actor).get_damage(new.target)
                new.actor.waste_energy(self.energy)
                # Применение способностей и особых свойств оружия
                new.dmg_done += new.actor.damage + 1 if new.dmg_done else 0
                if self.actor.weapon.melee:
                    self.actor.on_hit(new)
                    self.actor.weapon.on_hit(new)
                new.target.receive_hit(new)

            def on_attack(new):
                standart_actions.BaseAttack.on_attack(new)
                if engine.roll_chance(self.stun_chance) and new.dmg_done:
                    new.to_emotes(emoji_utils.emote_dict['stun_em'])
                    statuses.Stun(new.target)

        self.actor.fight.edit_queue(ThrowAttack())

    def available(self):
        return True if 'natural' not in self.actor.weapon.types and self.actor.energy > 3\
                       or not self.actor.weapon.melee else False


# Способность Зомби: После получения смертельного урона замораживает хдоровье на 1 и планирует смерть через 2 хода.
class Zombie(Passive):
    name = 'zombie'
    order = 41

    def __init__(self, actor):
        self.activated = False
        self.stopped = False
        Passive.__init__(self, actor)

    def activate(self, action=None):
        if self.actor.hp <= 0 and not self.stopped:
            self.actor.hp = 1
            if not self.activated:
                self.activated = True
                self.string('use', format_dict={'actor': self.actor.name})
                statuses.CustomStatus(actor=self.actor, delay=2, order=40, func=self.stop)

    def stop(self):
        self.stopped = True
        self.actor.hp_delta -= 10


# Способность Берсерк: Ваша начальная энергия уменьшается на 2.
#  Вы получаете дополнительную энергию за каждую недостающую жизнь.
#  Вы наносите бонусный урон, пока у вас остается только 1 жизнь.
class Berserk(Passive):
    name = 'berserk'
    types = ['start', 'on_hit']
    order = 42

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.bonus_damage = False
        self.bonus_energy = 0

    def start_act(self):
        self.actor.add_energy(-2)

    def act(self, action=None):
        if action is None:
            Passive.act(self, action=action)
        else:
            if action.dmg_done and self.bonus_damage:
                action.dmg_done += 2
                action.to_emotes(emoji_utils.emote_dict['exclaim_em'])

    def activate(self, action=None):
        # Определяет разницу между максимальным и текущим хп. bonus_energy - число этой разницы
        bonus_energy = self.actor.max_hp - self.actor.hp
        if bonus_energy > self.bonus_energy:
            # Если прошлый бонус меньше этого - добавляет строку с разницей бонусов и увеличивает количество энергии
            # и максимум запаса энергии.
            plus = bonus_energy - self.bonus_energy
            self.string('use', format_dict={'actor': self.actor.name, 'plus': plus})
            self.actor.add_energy(plus)

        elif bonus_energy < self.bonus_energy:
            # Если прошлый бонус больше этого - уменьшает только максимум запаса энергии
            minus = self.bonus_energy - bonus_energy
            self.actor.max_energy -= minus
            self.actor.recovery_energy -= minus
        self.bonus_energy = bonus_energy

        # Увеличивает урон на 2 при одной жизни.
        if self.actor.hp == 1:
            if not self.bonus_damage:
                self.bonus_damage = True
                self.string('special', format_dict={'actor': self.actor.name})
        elif self.bonus_damage:
            self.bonus_damage = False


class IgniteTorch(InstantAbility):
    name = 'ignite-torch'
    types = ['tech']
    order = 1

    def available(self):
        if self.actor.weapon.__class__.name == 'torch':
            if not self.actor.weapon.burning:
                return True
        return False

    def activate(self, action):
        self.actor.weapon.burning = True
        self.actor.weapon.start_fire_turn = self.actor.fight.turn
        self.actor.weapon.string('special_hit', format_dict={'actor': self.actor.name})


class WeaponMaster(InstantAbility):
    name = 'weapon-master'
    types = ['optional_start']
    full = False

    def __init__(self, actor):
        self.turn_used = 0
        InstantAbility.__init__(self, actor)

    def ask_start_option(self):
        buttons = []
        weapon_list = [weapon for weapon in weapons.weapon_list if 'unique' not in weapon.types]
        weapon_list = random.sample(set(weapon_list), 3)
        for w in weapon_list:
            buttons.append(keyboards.AbilityChoice(self, self.actor, option=w.name,
                                                   name=localization.LangTuple('_'.join(['weapon', w.name]), 'name')
                                                   .translate(self.actor.lang)))
        keyboard = keyboards.form_keyboard(*buttons)
        self.actor.active = True
        self.actor.edit_message(localization.LangTuple('abilities_weapon-master', 'options'), reply_markup=keyboard)

    def apply_start_option(self, info):
        weapon_name = info[-1]
        weapon = weapons.weapon_dict[weapon_name](self.actor)
        self.actor.weapons.append(weapon)

    def act(self, action):
        self.actor.change_weapon()
        self.turn_used = self.actor.fight.turn
        standart_actions.Custom(self.to_string, actor=self.actor, order=0)
        self.ask_action()

    def to_string(self):
        self.string('use', format_dict={'actor': self.actor.name,
                                        'weapon': localization.LangTuple('weapon_' + self.actor.weapon.name,
                                                                         'with_name')})

    def available(self):
        if self.actor.fight.turn != self.turn_used:
            return True
        return False


class Arsenal(StartAbility):
    name = 'arsenal'
    types = ['optional_start']

    def ask_start_option(self):
        buttons = []
        weapon_list = [weapon for weapon in weapons.weapon_list if 'arsenal' in weapon.types]
        for w in weapon_list:
            buttons.append(keyboards.AbilityChoice(self, self.actor, option=w.name,
                                                   name=localization.LangTuple('_'.join(['weapon', w.name]), 'name')
                                                   .translate(self.actor.lang)))
            buttons.append(keyboards.WeaponInfo(w, self.actor))
        keyboard = keyboards.form_keyboard(*buttons)
        self.actor.active = True
        self.actor.edit_message(localization.LangTuple('abilities_arsenal', 'options'), reply_markup=keyboard)

    def apply_start_option(self, info):
        weapon_name = info[-1]
        weapon = weapons.weapon_dict[weapon_name](self.actor)
        self.actor.weapons = self.actor.weapons[1:]
        self.actor.weapons.append(weapon)
        self.actor.weapon = weapon
        self.actor.items = self.actor.items[2:]


class Munchkin(Passive):
    name = 'munchkin'
    types = ['start', 'unique']
    order = 0

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.i = 0

    def start_act(self):
        self.actor.max_energy -= 1
        self.actor.energy -= 1

    def activate(self, action=None):
        self.i += 1
        if self.i == 3:
            x = random.choice(range(1, 4))
            if x == 1:
                if self.actor.max_energy < 10:
                    self.actor.add_energy(1)
                self.string('use', format_dict={'actor': self.actor.name, 'skill': localization.LangTuple('utils',
                                                                                                          'energy')})
            elif x == 2:
                if self.actor.damage < 4:
                    self.actor.damage += 1
                self.string('use', format_dict={'actor': self.actor.name, 'skill': localization.LangTuple('utils',
                                                                                                          'damage')})
            elif x == 3:
                if self.actor.melee_accuracy < 5:
                    self.actor.melee_accuracy += 2
                    self.actor.range_accuracy += 2
                self.string('use', format_dict={'actor': self.actor.name, 'skill': localization.LangTuple('utils',
                                                                                                          'accuracy')})
            self.i = 0


class JumpBack(InstantAbility):
    name = 'jump-back'
    types = ['start']
    full = True
    order = 1
    cd = 4

    def start_act(self):
        for ability in self.unit.abilities:
            if ability.name == 'dodge':
                self.unit.abilities.remove(ability)

    def activate(self, action):
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.Buff(self.unit, 'evasion', 6, 1)
        self.unit.move_back()


class Doctor(TargetAbility):
    name = 'doctor'
    order = 10
    cd = 5

    def build_act(self):
        self.actor.max_hp -= 1
        if self.actor.hp > self.actor.max_hp:
            self.actor.hp = self.actor.max_hp

    def targets(self):
        return self.actor.team.alive_actors()

    def activate(self, action):
        self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name})
        statuses.Bleeding(self.actor)
        action.target.hp_delta += 2


class HoundMaster(InstantAbility):
    name = 'houndmaster'
    order = 1
    full = True

    def __init__(self, actor):
        InstantAbility.__init__(self, actor)
        self.dog_called = False
        self.dog = 0

    def build_act(self):
        self.actor.max_hp -= 1
        if self.actor.hp > self.actor.max_hp:
            self.actor.hp = self.actor.max_hp

    def call_dog(self):
        from fight import ai
        dog = ai.Dog(self.actor.fight)
        dog.name = localization.LangTuple('ai_hound', 'number', format_dict={'number': self.actor.name})
        dog.stats()
        self.actor.fight.add_fighter(dog, team=self.actor.team)
        self.string('special', format_dict={'dog': dog.name})

    def activate(self, action):
        self.string('use', format_dict={'actor': self.actor.name})
        statuses.CustomStatus(self.actor, order=60, delay=2, func=self.call_dog, permanent=True)
        self.dog_called = True

    def available(self):
        return True if not self.dog_called else False


class RatGeneral(Passive):
    name = 'rat-general-call'
    types = ['start', 'unique']
    order = 50

    def __init__(self, actor):
        Passive.__init__(self, actor)
        self.hp = 0
        self.rat_number = 0
        self.passive_turns = 1

    def call_rat(self):
        from fight import ai
        self.rat_number += 1
        rat = random.choice([ai.CrossbowRat, ai.HammerRat, ai.KnifeRat])(self.actor.fight.game)
        rat.name = localization.LangTuple('ai_rat', 'number', format_dict={'number': self.rat_number})
        rat.stats()
        self.actor.fight.add_ai(rat, rat.name, team=self.actor.team)
        self.string('use', format_dict={'actor': self.actor.name})

    def start_act(self):
        self.hp = self.actor.hp

    def activate(self, action=None):
        rats = self.hp - self.actor.hp
        for i in range(rats):
            standart_actions.Custom(self.call_rat, order=51, actor=self.actor)
        self.hp = self.actor.hp
        if self.actor.fight.turn > (self.rat_number + 1)*5:
            standart_actions.Custom(self.call_rat, order=51, actor=self.actor)


class RatInquisitor(InstantAbility):
    name = 'rat-inquisitor-burn'
    order = 5

    def activate(self, action):
        targets = self.actor.targets()
        self.string('use', format_dict={'actor': self.actor.name})
        for target in targets:
            statuses.Burning(target, stacks=5)


class Skeleton(Passive):
    name = 'skeleton'
    order = 41

    def activate(self, action=None):
        if self.actor.hp <= 0 and self.actor.armor:
            self.actor.hp = 1


class Bite(TargetAbility):
    def targets(self):
        return [target for target in self.actor.melee_targets() if 'bleeding' in target.statuses]

    def activate(self, action):
        attack = standart_actions.BaseAttack(self.actor, self.actor.fight)
        attack.activate(target=random.choice(self.targets()), weapon=self.actor.weapon)
        dmg_done = attack.dmg_done
        if dmg_done > 0:
            self.string('use', format_dict={'actor': self.actor.name, 'target': action.target.name})
            self.actor.hp_delta += 1
        else:
            self.string('fail', format_dict={'actor': self.actor.name, 'target': action.target.name})

    def available(self):
        if TargetAbility.available(self) and self.targets():
            return True
        return False


class Cannibal(TargetAbility):
    name = 'cannibal'

    def targets(self):
        allies = [target for target in self.unit.get_allies()]
        allies.remove(self.unit)
        return allies

    def activate(self, action):
        self.unit.target = action.target
        attack = standart_actions.BaseAttack(self.unit, self.unit.fight)
        attack.activate(target=action.target, weapon=self.unit.weapon)
        dmg_done = attack.dmg_done
        if dmg_done > 0:
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
            self.unit.change_hp(1)
        else:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name})

    def available(self):
        if TargetAbility.available(self) and self.targets():
            return True
        return False


class CorpseEater(TargetAbility):
    name = 'corpse-eater'

    def targets(self):
        return [key for key in self.unit.fight.dead if 'alive' in key.types and self.unit.fight.dead[key]]

    def activate(self, action):
        if self.unit.fight.dead[action.target]:
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
            self.unit.change_hp(2)
            self.unit.max_hp += 2
            self.unit.damage += 2
            self.unit.fight.dead[action.target] = False
        else:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name})

    def available(self):
        if TargetAbility.available(self) and self.targets():
            return True
        return False


class WeaponSnatcher(TargetAbility):
    name = 'weapon-snatcher'

    def targets(self):
        return [target for target in self.unit.melee_targets]

    def activate(self, action):
        if 'reload' in action.target.action and 'natural' not in action.target.weapon.types:
            self.unit.weapon = action.target.weapon
            action.target.weapon = weapons.weapon_dict[action.target.default_weapon](action.target)
            self.unit.weapon.unit = self.unit
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
            self.unit.stole = True
        else:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name})

    def available(self):
        if 'natural' in self.unit.weapon.types:
            return True
        return False


class Witch(TargetAbility):
    name = 'curse'
    cd = 3

    def targets(self):
        return self.unit.targets()

    def activate(self, action):
        self.unit.waste_energy(3)
        statuses.Buff(unit=action.target, attr='range_accuracy', value=4, length=2)
        statuses.Buff(unit=action.target, attr='melee_accuracy', value=4, length=2)
        self.string('use', format_dict={'actor':self.unit.name, 'target': action.target.name})


class Necromancer(InstantAbility):
    name = 'necromancer'

    def activate(self, action):
        self.unit.waste_energy(5)
        self.unit.change_hp(-1)
        self.string('use', format_dict={'actor': self.unit.name})
        self.unit.summon_unit(Skeleton)


class Spermonster(ReceiveHit):
    name = 'spermonster'

    def act(self, action):
        if engine.roll_chance(60) and action.weapon.melee:
            self.unit.damage += 1
            self.string('use', format_dict={'actor': self.unit.name}, order=21)

ability_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None}
ability_list = {value for key, value in ability_dict.items() if 'tech' not in value.types}
