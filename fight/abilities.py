#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import standart_actions, statuses, items, weapons, spells
from locales import emoji_utils, localization
from bot_utils import keyboards
import math
import random
import engine
import inspect
import sys


class Ability(standart_actions.GameObject):
    core_types = ['ability']
    db_string = 'abilities'
    action_type = ['ability']
    prerequisites = {}
    school = []

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
        elif self.energy_cost > self.unit.energy:
            return False
        return True


class InstantAbility(standart_actions.InstantObject, Ability):
    core_types = ['ability', 'instant']
    db_string = 'abilities'


class TargetAbility(standart_actions.TargetObject, Ability):
    core_types = ['ability', 'target']
    db_string = 'abilities'

    def available(self):
        if not self.targets():
            return False
        else:
            return Ability.available(self)


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


class OnLvl(Passive):
    core_types = ['ability', 'on_lvl']
    active = False
    stats = {}

    def act(self, action=None):
        pass

    def gain(self, user):
        unit_dict = user.get_unit_dict()
        for key in self.stats:
            if key not in unit_dict:
                start_value = user.get_fight_unit_dict()[key]
            else:
                start_value = unit_dict[key]
            start_value += self.stats[key]
            unit_dict[key] = start_value
            user.set_unit_dict(unit_dict)


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


class SpellCaster(OptionAbility):
    name = 'spellcast'
    types = ['spell']
    order = 0
    start_sigils = [emoji_utils.emote_dict['self_em'], emoji_utils.emote_dict['strength_em'], emoji_utils.emote_dict['palm_em']]
    buff_sigils = [emoji_utils.emote_dict['wind_em'], emoji_utils.emote_dict['earth_em'], emoji_utils.emote_dict['random_em']]
    end_sigils = [emoji_utils.emote_dict['spark_em'], emoji_utils.emote_dict['ice_em'], emoji_utils.emote_dict['ignite_em']]
    prerequisites = {'lvl': 100}

    def act(self, action):
        if self.check_final(action.info):
            spell_tuple = tuple(action.info[-1].split('-'))
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


# Способности ловкости
class Dodge(InstantAbility):
    name = 'dodge'
    types = ['dodge', 'move']
    order = 1
    cd = 2
    school = 'dexterity'

    def activate(self, action):
        InstantAbility.activate(self, action)
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.Buff(self.unit, 'evasion', 8, 1)

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

    def on_cd(self):
        InstantAbility.on_cd(self)
        if any(ability.name == 'jump-back' for ability in self.unit.abilities):
            ability = next(ability for ability in self.unit.abilities if ability.name == 'jump-back')
            ability.ready_turn = self.unit.fight.turn + self.unit.speed_penalty() + ability.cd


class JumpBack(InstantAbility):
    name = 'jump-back'
    types = ['dodge', 'move']
    order = 1
    cd = 5
    prerequisites = {'dexterity': 1}
    school = 'dexterity'

    def activate(self, action):
        InstantAbility.activate(self, action)
        self.string('use', format_dict={'actor': self.unit.name})
        statuses.Buff(self.unit, 'evasion', 6, 1)
        self.unit.move_back()

    def available(self):
        if not self.ready():
            return False
        if 'running' in self.unit.statuses:
            return False
        if self.unit.rooted:
            return False
        return True

    def on_cd(self):
        InstantAbility.on_cd(self)
        if any(ability.name == 'dodge' for ability in self.unit.abilities):
            ability = next(ability for ability in self.unit.abilities if ability.name == 'dodge')
            ability.ready_turn = self.unit.fight.turn + self.unit.speed_penalty() + ability.cd


class Trip(TargetAbility):
    name = 'trip'
    order = 5
    prerequisites = {'dexterity': 1}
    school = 'dexterity'

    def targets(self):
        return self.unit.melee_targets

    def activate(self, action):
        self.on_cd()
        if 'move' in action.target.action:
            self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})
            statuses.Prone(action.target)
        else:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name})


class Assassin(Passive):
    name = 'assassin'
    order = 41
    school = 'dexterity'
    prerequisites = {'dexterity': 2, 'strength': 1}

    def activate(self, action=None):
        if 'effect' in self.unit.weapon.types:
            if 'attack' not in self.unit.action:
                self.unit.weapon.effect_chance *= 3
            else:
                self.unit.weapon.effect_chance = self.unit.weapon.default_effect_chance
            print('Вероятность особой атаки')
            print(self.unit.weapon.effect_chance)


class TwoHandedMastery(Passive):
    name = 'two-handed-mastery'
    order = 41
    school = 'strength'
    prerequisites = {'lvl': 2}

    def activate(self, action=None):
        if 'two-handed' in self.unit.weapon.types:
            if 'attack' in self.unit.action:
                self.unit.energy += 1


class ShieldMastery(Passive):
    name = 'shield-mastery'
    order = 41
    school = 'protection'
    prerequisites = {'protection': 1}

    def activate(self, action=None):
        if 'shield' in self.unit.action:
            shield = next(armor for armor in self.unit.armor if 'shield' in armor.types)
            self.unit.energy += shield.block_energy_cost


class Charge(Passive):
    name = 'charge'
    school = 'strength'

    def activate(self, action=None):
        pass


class Push(TargetAbility):
    name = 'push'
    order = 1
    cd = 3
    default_energy_cost = 1
    school = 'strength'
    prerequisites = {'strength': 2, 'protection': 1}

    def targets(self):
        return [target for target in self.unit.melee_targets if 'massive' not in target.types]

    def activate(self, action):
        self.on_cd()
        if 'dodge' in action.target.action:
            self.string('fail', format_dict={'target': action.target.name, 'actor': self.unit.name})
        elif 'shield' in action.target.action:
            self.string('special', format_dict={'target': action.target.name, 'actor': self.unit.name})
        else:
            self.string('use', format_dict={'target': action.target.name, 'actor': self.unit.name})
            statuses.Buff(action.target, 'melee_accuracy', -6, 1)
            statuses.Buff(action.target, 'range_accuracy', -6, 1)
            action.target.move_back()


class Heavy(OnLvl):
    name = 'heavy'
    stats = {'speed': 4}
    school = 'protection'
    prerequisites = {'lvl': 2}


class Tough(OnLvl):
    name = 'tough'
    school = 'protection'
    stats = {'toughness': 3}


class Slow(OnLvl):
    name = 'slow'
    stats = {'max_recovery': -2, 'max_energy': 2}
    prerequisites = {'protection': 2}
    school = 'protection'


class Sturdy(OnLvl):
    name = 'sturdy'
    stats = {'max_hp': 1, 'hp': 1}
    prerequisites = {'protection': 1}
    school = 'protection'


class Armorer(StartAbility):
    name = 'armorer'
    prerequisites = {'protection': 3}
    school = 'protection'

    def start_act(self):
        for armor in self.unit.armor:
            armor.armor += 2
            armor.current_coverage += 15


class Block(TargetAbility):
    name = 'block'
    order = 1
    cd = 1
    default_energy_cost = 1
    types = ['defense']
    prerequisites = {'protection': 2, 'dexterity': 1}
    school = 'protection'

    def targets(self):
        return self.unit.melee_targets

    def activate(self, action):
        self.on_cd()
        if any('shield' in armor.types for armor in self.unit.armor) and \
                        next(armor for armor in self.unit.armor if 'shield' in armor.types).armor > 0:
            blocker = next(armor for armor in self.unit.armor if 'shield' in armor.types)
            max_dmg = 100
        else:
            blocker = self.unit.weapon
            max_dmg = self.unit.weapon.dice_num
            max_dmg = self.unit.weapon.damage_cap if self.unit.weapon.damage_cap < max_dmg else max_dmg
            if 'two-handed' in blocker.types:
                self.unit.waste_energy(1)
        if 'attack' not in action.target.action:
            self.string('fail', format_dict={'actor': self.unit.name, 'target': action.target.name,
                                             'blocker': blocker.name_lang_tuple()})
        else:
            for actn in self.unit.fight.action_queue.action_list:
                if actn.unit == action.target and 'attack' in actn.action_type:
                    dmg = actn.weapon.get_damage(action.unit)
                    if dmg <= max_dmg:
                        action.target.waste_energy(action.target.weapon.energy_cost)
                        self.unit.fight.action_queue.remove(actn)
                        self.string('use', format_dict={'actor': self.unit.name,
                                                        'target': action.target.name,
                                                        'blocker':  blocker.name_lang_tuple()})
                    else:
                        self.string('special', format_dict={'actor': self.unit.name,
                                                            'target': action.target.name,
                                                            'blocker':  blocker.name_lang_tuple()})


class FastAttack(TargetAbility):
    name = 'fast-attack'
    full = False
    default_energy_cost = 1
    cd = 2
    prerequisites = {'dexterity': 2, 'strength': 1}
    school = 'dexterity'

    def targets(self):
        return self.unit.melee_targets

    def act(self, action):
        if len(action.info) > 5:
            self.act_options(action)
            for action_type in action.action_type:
                self.unit.action.append(action_type)
            self.on_cd()
            if self.energy_cost > 0:
                self.unit.waste_energy(self.energy_cost)
            self.unit.rooted.append('fast-attack')
            self.ask_action()
        else:
            self.ask_options()

    def activate(self, action):
        self.unit.rooted.remove('fast-attack')
        attack = standart_actions.Attack(self.unit, self.unit.fight)
        attack.activate(target=action.target)


class Cleave(InstantAbility):
    name = 'cleave'
    types = ['attack']
    order = 5
    cd = 2
    default_energy_cost = 2
    prerequisites = {'strength': 1}
    school = 'strength'

    def name_lang_tuple(self):
        return localization.LangTuple(self.table_row, 'button')

    def activate(self, action):
        self.on_cd()
        self.string('special', format_dict={'actor': self.unit.name, 'weapon': self.unit.weapon.name_lang_tuple()})
        statuses.CustomStatus(self.unit, 4, 1, self.cleave, name='attack_modifier_random')

    def cleave(self):
        for action in self.unit.fight.action_queue.action_list:
            if action.unit == self.unit and action.name == 'attack':
                self.unit.fight.action_queue.remove(action)
                self.unit.waste_energy(self.unit.weapon.energy_cost)
                targets = [target for target in self.unit.melee_targets if 'dodge' not in target.action]
                if targets:
                    damage = engine.aoe_split(self.unit.weapon.dice_num + 1 + self.unit.weapon.damage + self.unit.damage,
                                              len(targets))
                    self.string('use', format_dict={'actor': self.unit.name, 'damage': damage,
                                                    'targets': ', '.join([target.name if isinstance(target.name, str) else target.name.translate('rus') for target in targets])})

                    for target in targets:
                        attack_action = standart_actions.Attack(self.unit, self.unit.fight, stringed=False)
                        attack_action.activate(target=target, waste=0, dmg=damage)
                else:
                    self.string('fail', format_dict={'actor': self.unit.name})

    def available(self):
        if 'two-handed' not in self.unit.weapon.types:
            return False
        return InstantAbility.available(self)


class Provoke(TargetAbility):
    name = 'provoke'
    order = 5
    cd = 2
    default_energy_cost = 1
    prerequisites = {'lvl': 2}
    school = 'dexterity'

    def targets(self):
        return self.unit.targets()

    def activate(self, action):
        statuses.CustomPassive(action.target, types=['on_hit'], name='provoke_stop',
                               delay=6, func=self.stop_provoke, option=action.unit)
        statuses.PermaStatus(action.target, 1, 6, self.provoke, name='provoke', emoji='😡', args=[action.target])
        self.string('use', format_dict={'actor': self.unit.name, 'target': action.target.name})

    @staticmethod
    def provoke(target):
        target.waste_energy(2)
        Provoke(target).string('special', format_dict={'actor': target.name})

    @staticmethod
    def stop_provoke(action, options):
        if action.target == options:
            action.unit.statuses['provoke'].finish()
            action.unit.statuses['provoke_stop'].finish()


class SecondBreath(Passive):
    name = 'second-breath'
    order = 60
    prerequisites = {'dexterity': 2, 'protection': 1}
    school = 'dexterity'

    def __init__(self, unit=None, obj_dict=None):
        Passive.__init__(self, unit=unit, obj_dict=obj_dict)
        self.used = False

    def activate(self, action=None):
        if not self.used:
            if self.unit.energy <= 0:
                self.string('use', format_dict={'actor': self.unit.name})
                self.unit.energy = self.unit.max_energy
                self.used = True


class ShieldSmash(TargetAbility):
    name = 'shield-smash'
    order = 3
    prerequisites = {'strength': 1, 'protection': 1}
    school = 'protection'

    def targets(self):
        return self.unit.melee_targets

    def activate(self, action):
        self.on_cd()
        target = action.target
        attack = standart_actions.Attack(self.unit, self.unit.fight)
        shield = next(armor for armor in self.unit.armor if 'shield' in armor.types)
        attack.activate(target=target, weapon=shield)
        self.unit.waste_energy(shield.energy_cost)
        shield.current_coverage = 100
        statuses.CustomStatus(self.unit, 0, 1, self.stop_shield, args=[shield])

    @staticmethod
    def stop_shield(shield):
        shield.current_coverage = shield.get_coverage()

    def available(self):
        if not any('shield' in armor.types for armor in self.unit.armor):
            return False
        elif next(armor for armor in self.unit.armor if 'shield' in armor.types).armor <= 0:
            return False
        return TargetAbility.available(self)


class Jump(TargetAbility):
    name = 'jump'
    order = 10
    cd = 1
    prerequisites = {'strength': 2, 'dexterity': 1}
    school = 'strength'

    def get_energy_cost(self):
        if self.unit is not None:
            return self.unit.weapon.energy_cost
        else:
            return self.default_energy_cost

    def targets(self):
        return [target for target in self.unit.targets() if target not in self.unit.melee_targets]

    def activate(self, action):
        self.unit.move_forward()
        self.string('use', format_dict={'actor': self.unit.name})
        attack = standart_actions.Attack(self.unit, self.unit.fight)
        attack.activate(target=action.target)


class Execute(OnHit):
    name = 'execute'
    prerequisites = {'strength': 1}
    school = 'strength'

    def act(self, action):
        if action.target.hp <= math.ceil(action.target.max_hp/4):
            action.dmg_done *= 2
            action.to_emotes(emoji_utils.emote_dict['exclaim_em'])


class KnockBack(TargetAbility):
    name = 'knock-back'
    order = 4
    cd = 2
    default_energy_cost = 2
    prerequisites = {'strength': 1, 'protection': 1}
    school = 'strength'

    def targets(self):
        return self.unit.melee_targets

    def activate(self, action):
        self.on_cd()
        if action.target.energy < action.unit.energy + random.randint(0, 1):
            self.string('use', format_dict={'actor': action.unit.name, 'target': action.target.name})
            statuses.Buff(action.target, 'melee_accuracy', -6, 1)
            statuses.Buff(action.target, 'range_accuracy', -6, 1)
            print(action.target.melee_accuracy)
            statuses.Prone(action.target)
        else:
            self.string('fail', format_dict={'actor': action.unit.name, 'target': action.target.name})


# ################################ НИЖЕ НИЧЕГО НЕ ПРОВЕРЕНО #######################################
# Способность Садист: прибавляет энергию, если у текущей цели отнялись жизни.

class Sadist(Passive):
    name = 'sadist'
    order = 41
    prerequisites = {'strength': 1, 'dexterity': 1}
    school = 'dexterity'

    def __init__(self, unit=None, obj_dict=None):
        Passive.__init__(self, unit=unit, obj_dict=obj_dict)
        self.hp = 0

    def act(self, action=None):
        standart_actions.Custom(self.set_hp, order=40, unit=self.unit)
        self.unit.fight.action_queue.append(self)

    def activate(self, action=None):
        if self.hp > 0:
            if self.hp > self.unit.target.hp:
                print(True)
                self.unit.energy += self.hp - self.unit.target.hp
                self.string('use', format_dict={'actor': self.unit.name, 'energy': self.hp - self.unit.target.hp})
        self.hp = 0

    def set_hp(self):
        if self.unit.target is not None:
            self.hp = self.unit.target.hp


# Способность Берсерк: Ваша начальная энергия уменьшается на 2.
#  Вы получаете дополнительную энергию за каждую недостающую жизнь.
#  Вы наносите бонусный урон, пока у вас остается только 1 жизнь.

class Berserk(Passive):
    name = 'berserk'
    core_types = ['ability', 'on_lvl']
    types = ['passive', 'on_hit']
    order = 42
    prerequisites = {'strength': 2}
    school = 'strength'
    stats = {'max_energy': -2}

    def __init__(self, unit=None, obj_dict=None):
        Passive.__init__(self, unit=unit, obj_dict=obj_dict)
        self.bonus_damage = False
        self.bonus_energy = 0

    def act(self, action=None):
        if action is None:
            Passive.act(self, action=action)
        else:
            if action.dmg_done and self.bonus_damage:
                action.dmg_done += 2
                action.to_emotes(emoji_utils.emote_dict['exclaim_em'])

    def activate(self, action=None):
        # Определяет разницу между максимальным и текущим хп. bonus_energy - число этой разницы
        bonus_energy = self.unit.max_hp - self.unit.hp
        if bonus_energy > self.bonus_energy:
            # Если прошлый бонус меньше этого - добавляет строку с разницей бонусов и увеличивает количество энергии
            # и максимум запаса энергии.
            plus = bonus_energy - self.bonus_energy
            self.string('use', format_dict={'actor': self.unit.name, 'plus': plus})
            self.unit.max_energy += plus
            self.unit.energy += plus
            self.unit.speed += plus

        elif bonus_energy < self.bonus_energy:
            # Если прошлый бонус больше этого - уменьшает только максимум запаса энергии
            minus = self.bonus_energy - bonus_energy
            self.unit.max_energy -= minus
            self.unit.speed -= minus
        self.bonus_energy = bonus_energy

        # Увеличивает урон на 2 при одной жизни.
        if self.unit.hp == 1:
            if not self.bonus_damage:
                self.bonus_damage = True
                self.string('special', format_dict={'actor': self.unit.name})
        elif self.bonus_damage:
            self.bonus_damage = False

    def gain(self, user):
        OnLvl.gain(self, user)


class HandToHand(OnHit):
    name = 'hand-to-hand'
    prerequisites = {'dexterity': 2}
    school = 'dexterity'

    def act(self, action=None):
        if action.dmg_done and action.weapon.name == 'fist':
            action.dmg_done += 2


class UnrelentingForce(InstantAbility):
    name = 'unrelenting-force'
    order = 15
    types = ['attack']
    default_energy_cost = 4
    cd = 3
    prerequisites = {'strength': 3}
    school = 'strength'

    def activate(self, action):
        if self.unit.dmg_received == 0:
            self.string('fail', format_dict={'actor': self.unit.name})
        if self.unit.melee_targets:
            target = random.choice(self.unit.melee_targets)
            if 'dodge' not in target.action:
                damage = self.unit.dmg_received
                attack_action = standart_actions.Attack(self.unit, self.unit.fight, stringed=False)
                attack_action.activate(target=target, waste=0, dmg=damage)
                self.string('use', format_dict={'actor': self.unit.name, 'target': target.name,
                                                 'damage': attack_action.dmg_done})
        else:
            self.string('special', format_dict={'actor': self.unit.name})


class CounterAttack(Passive):
    name = 'counterattack'
    types = ['passive', 'before_hit', 'on_hit']
    order = 20
    prerequisites = {'dexterity': 1, 'protection': 1}
    school = 'protection'

    def __init__(self, unit=None, obj_dict=None):
        Passive.__init__(self, unit=unit, obj_dict=obj_dict)
        self.activated_round = 0
        self.switch = False

    def act(self, action=None):
        if action is None:
            Passive.act(self, action=action)
        else:
            if self.activated_round == self.unit.fight.turn:
                if not self.switch:
                    print(1)
                    self.unit.melee_accuracy += 3
                    self.unit.waste_energy(-1)
                    self.switch = True
                else:
                    self.unit.melee_accuracy -= 3
                    print(2)
                    if action.dmg_done > 0:
                        action.dmg_done += 1
                        action.to_emotes(emoji_utils.emote_dict['exclaim_em'])
                    self.switch = False

    def activate(self, action=None):
        if any(unit.target == self.unit and 'attack' in unit.action for unit in self.unit.targets()) and self.unit.dmg_received == 0:
            if 'shield' in self.unit.action or 'dodge' in self.unit.action or 'defense' in self.unit.action:
                standart_actions.Custom(self.string, 'use', order=60, format_dict={'actor': self.unit.name}, unit=self.unit)
                self.activated_round = self.unit.fight.turn + 1


class Cannibal(TargetAbility):
    name = 'cannibal'
    prerequisites = {'lvl': 100}

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
    prerequisites = {'lvl': 100}

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
    prerequisites = {'lvl': 100}

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
    prerequisites = {'lvl': 100}

    def targets(self):
        return self.unit.targets()

    def activate(self, action):
        self.unit.waste_energy(3)
        statuses.Buff(unit=action.target, attr='range_accuracy', value=4, length=2)
        statuses.Buff(unit=action.target, attr='melee_accuracy', value=4, length=2)
        self.string('use', format_dict={'actor':self.unit.name, 'target': action.target.name})

ability_dict = {value.name: value for key, value
                in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
                if value.name is not None}
ability_list = {value for key, value in ability_dict.items() if 'tech' not in value.types}
