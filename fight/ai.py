#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import weapons, abilities, items, armors, standart_actions
from fight import fight_main
import random
from fight.standart_actions import *
from operator import attrgetter


def get_lowest_hp(team):
    try:
        if team:
            return min(team, key=attrgetter('hp'))
        else:
            return None
    except AttributeError:
        return random.choices(team)


def get_lowest_energy(team):
    if team:
        return min(team, key=attrgetter('energy'))
    else:
        return None


def get_largest_opponent_team(actor, game):
    i = 0
    for team in game.lobby:
        if actor not in team and len(team) > i:
            i = len(team)
    return i


class Ai:
    ai = True

    def __init__(self, fight):
        self.number = 0
        self.fight = fight
        self.chat_id = id(self)
        self.action_dict = {}
        self.done = True
        self.difficulty = 0
        self.unit = None
        self.talked = False

    def form_actions(self):
        pass

    def find_target(self):
        pass

    def add_action(self, action_class, chance, **kwargs):
        action = action_class(self.unit, self.fight, **kwargs)
        if 'ability' in action.types:
            if not action.ability.available():
                return False
        if 'item' in action.types:
            if not action.item.available():
                return False
        self.action_dict[action] = chance

    def action_ability(self, name, chance, target=None):
        info = ['fgt', str(self.fight), str(self.unit), 'ability', name]
        if target is not None:
            info.append(str(target))
        self.add_action(Ability, chance,
                        info=info)

    def action_item(self, name, chance, target=None):
        info = ['fgt', str(self.fight), str(self.unit), 'item', name]
        if target is not None:
            info.append(str(target))
        self.add_action(Item, chance,
                        info=info)

    def action_weapon(self, chance, target=None):
        info = ['fgt', str(self.fight), 'special']
        if target is not None:
            info.append(str(target))
        self.add_action(SpecialWeaponAction, chance,
                        info=info)

    def action_weapon_option(self, chance, option):
        info = ['fgt', str(self.fight), str(self.unit), 'wpspecial', option]
        self.add_action(SpecialWeaponOption, chance, info=info)

    def make_action(self, action_class, **kwargs):
        action_class(self.unit, self.fight, **kwargs).act()

    def clear_actions(self):
        self.action_dict = {}

    def get_action(self, edit=False):
        self.form_actions()
        print('Выбор действий моба ' + self.unit.name.translate(self.fight.lang) + ':')
        print('Энергия: {}'.format(self.unit.energy))
        for a in self.action_dict:
            print(str(a.name) + '     ' + str(self.action_dict[a]))
        chance_sum = sum([value for key, value in self.action_dict.items()])
        if chance_sum == 0:
            return False
        current_chance = random.randint(1, chance_sum)
        actions = list(self.action_dict.items())
        at = 1
        for action in actions:
            if current_chance in range(at, at + action[-1]):
                action[0].act()
                return True
            at += action[-1]

    def move_forward(self, chance):
            self.add_action(MoveForward, chance)

    def attack(self, chance):
            self.add_action(Attack, chance)

    def reload(self, chance):
            self.add_action(MeleeReload, chance)

    def end_turn(self):
        self.unit.done = True


class StandartMeleeAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_energy(self.unit.weapon.targets())
            if engine.roll_chance(30):
                self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class TechAi(Ai):

    def get_action(self, edit=False):
        self.unit.done = True


class SkeletonAi(Ai):

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.weapon_ai_dict = {'default': self.default_weapon_actions,
                               'bow': self.bow_weapon_actions}

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    # Выбор алгоритма действий в зависимости от оружия
    def form_actions(self):
        if self.unit.weapon.name in self.weapon_ai_dict:
            self.weapon_ai_dict[self.unit.weapon.name]()
        else:
            self.weapon_ai_dict['default']()

    # Алгоритм действий при экипировке оружия ближнего боя
    def default_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.bone_dict['legs']:
            self.move_forward(1 if not self.unit.weapon.targets() else 0)
        else:
            self.add_action(self.unit.crawl_action, 1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)

    # Алгоритм действий при экипировке лука
    def bow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available(self.unit.target):
            self.add_action(SpecialWeaponAction, 5, info=['fgt', str(self.fight), 'special'])


class LichAi(Ai):

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.skeleton_summoned = 0
        self.unit.chain_turn = 0

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.make_action(self.unit.check_blood_action)
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.add_action(self.unit.blood_touch_action, self.unit.energy if self.unit.target is not None else 0)
        if self.unit.target is not None:
            self.add_action(self.unit.chain_action, self.unit.energy*4 if len(self.unit.targets()) > 1
                                                                          and not self.unit.chains and self.unit.fight.turn - self.unit.chain_turn > 4 else 0)
        if self.skeleton_summoned < 1 and self.unit.wounds < 30:
            self.add_action(self.unit.summon_skeleton_action, 10)
            self.skeleton_summoned += 1


class ZombieAi(Ai):
    ai_name = 'zombie'

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)


class GoblinAi(StandartMeleeAi):
    ai_name = 'goblin'
    snatch_targets = []

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.action_pattern_dict = {'default': self.default_weapon_actions,
                                    'fist': self.snatch_weapon_action,
                                    'bow': self.bow_weapon_actions,
                                    'crossbow': self.crossbow_weapon_actions,
                                    'harpoon': self.harpoon_weapon_actions}

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.weapon.name in self.action_pattern_dict:
            self.action_pattern_dict[self.unit.weapon.name]()
        else:
            self.action_pattern_dict['default']()

    def snatch_weapon_action(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)
        if self.unit.target is not None and 'natural' not in self.unit.target.weapon.types \
                and not self.unit.weapon_to_member and not self.unit.lost_weapon:
            self.action_ability('weapon-snatcher',
                                (2 - self.unit.target.energy if self.unit.target.energy < 3 else 0)*5,
                                target=self.unit.target)
        elif self.unit.lost_weapon:
            self.add_action(PickUpWeapon, 5 - self.unit.energy if self.unit.energy < 3 else 0)

    def default_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(3 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)

    def bow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.add_action(MoveBack, 5 - self.unit.energy if self.unit.melee_targets and self.unit.target.weapon.melee else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available(self.unit.target):
            self.action_weapon(self.unit.energy + 1 if self.unit.energy > 0 else 0)

    def harpoon_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.move_forward(2 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        if self.unit.weapon.special_available():
            self.action_weapon_option(self.unit.energy if self.unit.energy > 0 else 0,
                                      str(random.choice(self.unit.targets())))

    def crossbow_weapon_actions(self):
        self.clear_actions()
        self.find_target()
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        self.add_action(MoveBack, 5 - self.unit.energy if self.unit.melee_targets
                                                       and self.unit.target.weapon.melee
                                                       and not self.unit.weapon.loaded else 0)
        if not self.unit.weapon.loaded:
            self.action_weapon(self.unit.energy if self.unit.target is not None else 0)
        else:
            self.attack(self.unit.energy if self.unit.target is not None else 0)


class RatAi(StandartMeleeAi):
    ai_name = 'rat'

    def __init__(self, fight):
        Ai.__init__(self, fight)
        self.action_pattern_dict = {'default': self.default_weapon_action,
                                    'sledgehammer': self.sledgehammer_weapon_action,
                                    'dodge': lambda: self.action_ability('dodge', self.unit.max_energy - self.unit.energy
                                                                         if self.state == 'victim' else 0)}
        self.state = None

    def get_fight_state(self):
        self.state = None
        if sum([unit.energy for unit in self.unit.team.units]) \
            - max([sum([unit.energy for unit in team.units])/len(team.units) for team in self.unit.fight.teams]) < -1:
            self.state = 'victim'

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.get_fight_state()
        if self.unit.weapon.name in self.action_pattern_dict:
            self.action_pattern_dict[self.unit.weapon.name]()
        else:
            self.action_pattern_dict['default']()
        for item in [*self.unit.items, *self.unit.armor, *self.unit.abilities]:
            if item.name in self.action_pattern_dict:
                self.action_pattern_dict[item.name]()

    def default_weapon_action(self):
        StandartMeleeAi.form_actions(self)

    def sledgehammer_weapon_action(self):
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        if self.unit.weapon.special_available(target=self.unit.target):
            self.action_weapon_option(self.unit.energy - 1 + self.unit.target.max_energy - self.unit.target.energy
                                      if self.unit.energy > 0 and self.unit.target.energy > 1 else 0,
                                      str(self.unit.target))


# Монстры Артема
class ShadowAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_energy(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class SnailAi(StandartMeleeAi):

    def move_forward(self, chance):
        self.add_action(self.unit.crawl_action, chance)

    def form_actions(self):
        StandartMeleeAi.form_actions(self)
        self.make_action(self.unit.split_check_action)


# Монстры Пасюка
class SperMonsterAi(StandartMeleeAi):

    def form_actions(self):
        StandartMeleeAi.form_actions(self)
        self.make_action(self.unit.sperm_check_action)


class PedoBearAi(StandartMeleeAi):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.reload(1 if self.unit.energy < 1 else 0)
        if self.unit.energy > 0 and self.unit.target is not None:
            if self.unit.locked_in is not None:
                self.unit.target = self.unit.locked_in
                self.make_action(self.unit.hug_action)
            else:
                self.make_action(self.unit.find_target_action)


# Монстры Асгард
class BearAi(StandartMeleeAi):

    def find_target(self):
        stunned_targets = [target for target in self.unit.weapon.targets() if 'stun' in target.disabled]

        if stunned_targets:
            target = random.choice(stunned_targets)
        elif not self.unit.weapon.targets():
            target = None
        else:
            target = random.choice(self.unit.weapon.targets())
        self.unit.target = target

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        target = self.unit.target
        if target is not None:
            if 'stun' in target.disabled:
                self.add_action(self.unit.destroy_action, self.unit.energy)
            else:
                self.attack(self.unit.energy)


class BirdRukhAi(StandartMeleeAi):
    def __init__(self, fight):
        StandartMeleeAi.__init__(self, fight)
        self.charged = False

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if not self.charged:
            self.make_action(self.unit.stun_action)
            self.charged = True
        else:
            self.add_action(self.unit.fly_action, 1 if not self.unit.weapon.targets() else 0)
            self.attack(self.unit.energy if self.unit.target is not None else 0)
            self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)


class BasiliskAi(Ai):
    ai_name = 'basilisk'

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if self.unit.stun_ready:
            self.add_action(self.unit.stun_action, 1)
        elif self.unit.hurt:
            self.add_action(self.unit.recovery_action, 1)
        else:
            self.add_action(self.unit.rush_action, 1 if not self.unit.weapon.targets() and self.unit.energy > 4 else 0)
            self.attack(self.unit.energy if self.unit.target is not None else 0)
            self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)


class WormAi(Ai):

    def find_target(self):
        if self.unit.weapon.targets():
            self.unit.target = get_lowest_hp(self.unit.weapon.targets())
            if engine.roll_chance(20):
                self.unit.target = random.choice(self.unit.weapon.targets())
        else:
            self.unit.target = None

    def form_actions(self):
        allies = self.unit.get_allies()
        allies.remove(self.unit)
        self.clear_actions()
        self.find_target()
        self.attack(self.unit.energy if self.unit.target is not None and not self.unit.feared else 0)
        self.add_action(self.unit.crawl_action, 1 if not self.unit.weapon.targets() else 0)
        self.add_action(self.unit.crawl_back_action, 1 if self.unit.feared and self.unit.weapon.targets() else 0)
        if not self.unit.weapon.targets() and allies:
            self.add_action(Ability, self.unit.max_hp - self.unit.hp, info=['fgt', str(self.fight), str(self.unit),
                                                          'ability', 'cannibal',
                                                                            str(get_lowest_hp(allies))])
        if any(v for k, v in self.unit.fight.dead.items()):
            self.add_action(Ability, 10, info=['fgt', str(self.fight), str(self.unit),
                                                                        'ability', 'corpse-eater',
                                                                        str(random.choice([k for k, v in self.unit.fight.dead.items()
                                                                                           if self.unit.fight.dead[k]]))])
        self.reload(5 - self.unit.energy if self.unit.energy < 3 else 0)


class Dog(Ai):
    ai_name = 'dog'

    def stats(self):
        self.chat_id = id(self)
        self.max_hp = 3
        self.hp = self.max_hp
        self.toughness = 3
        self.default_weapon = weapons.Fangs(self)
        self.weapon = weapons.Fangs(self)

    def find_target(self):
        self.target = get_lowest_hp(self.melee_targets)

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        if 'burning' in self.statuses:
            if self.statuses['burning'].stacks > 1:
                Custom(self.put_fire_out, actor=self, order=0)
                return None
        self.move_forward(1 if not self.weapon.targets() else 0)
        self.attack(self.energy if self.target is not None else 0)
        self.reload(4 - self.energy if self.energy < 5 else 0)

    def put_fire_out(self):
        self.action.append('skip')
        if self.ai_name != 'leader':
            self.string('fire_out', format_dict={'actor': self.name})

    def reload(self, chance):
        if 'burning' in self.statuses:
            self.add_action(Custom(self.put_fire_out, actor=self), chance)
        else:
            self.add_action(MeleeReload, chance)


class Leader(Dog):
    ai_name = 'leader'

    def stats(self):
        self.chat_id = id(self)
        self.max_hp = 4
        self.hp = self.max_hp
        self.toughness = 6
        self.default_weapon = weapons.Fangs(self)
        self.weapon = weapons.Fangs(self)
        self.raged = False

    def set_difficulty(self, game):
        self.difficulty = get_largest_opponent_team(self, game)
        self.max_hp = 4 + self.difficulty
        self.hp = 2
        self.max_energy = 4 + self.difficulty

    def rage(self):
        self.string('skill_1', format_dict={'actor': self.name})
        self.damage += self.difficulty*2
        self.max_energy += self.difficulty
        self.armor_dict['hide'] = (self.difficulty, 80)
        self.weapon.bleed_chance = 100
        self.raged = True

    def enrage(self):
        Custom(self.rage, actor=self, order=0)

    def pack(self):
        self.string('skill_2', format_dict={'actor': self.name})
        dog_1 = Dog(self.fight)
        dog_1.name = localization.LangTuple('ai_pup', 'number', format_dict={'number': 1})
        dog_2 = Dog(self.fight)
        dog_2.name = localization.LangTuple('ai_pup', 'number', format_dict={'number': 2})
        self.fight.add_ai(dog_1, dog_1.name, team=self.team)
        self.fight.add_ai(dog_2, dog_2.name, team=self.team)

    def summon_pack(self, chance):
        self.action_dict[Custom(self.pack, actor=self, to_queue=False)] = chance

    def prepare_actions(self):
        self.clear_actions()
        self.find_target()
        if self.hp <= int(self.max_hp/2) and not self.raged:
            self.enrage()
        if 'burning' in self.statuses:
            Custom(self.put_fire_out, actor=self, order=0)

    def form_actions(self):
        self.prepare_actions()
        #if len([actor for actor in self.team.actors if actor.alive()]) == 1:
        #   self.summon_pack(15)
        self.move_forward(1 if not self.weapon.targets() else 0)
        self.attack(self.energy if self.target is not None else 0)
        self.reload(5 - self.energy if self.energy < 5 else 0)

    def reload(self, chance):
        Ai.reload(self, chance)


class Rat(Ai):
    ai_name = 'rat'

    def stats(self):
        self.default_weapon = weapons.Claws(self)
        self.abilities.append(abilities.PickUpWeapon(self))
        self.abilities.append(abilities.Dodge(self))

    def find_target(self):
        self.target = get_lowest_hp(self.weapon.targets())
        if random.randint(1, 100) < 30 and self.weapon.targets():
            self.target = random.choice(self.weapon.targets())

    # Оценка ситуации на поле боя, назначение "настроения"
    def mood_state(self):
        team_aggressions = {}
        for team in self.fight.teams:
            team_aggression_rate = sum(actor.energy for actor in team.actors)
            team_aggressions[team] = team_aggression_rate
        top_aggression = max(value for key, value in team_aggressions.items())
        if team_aggressions[self.team] == top_aggression:
            second_top_aggression = max(value for key, value in team_aggressions.items() if key != self.team)
            if second_top_aggression < len([team for team in team_aggressions
                                           if team_aggressions[team] == second_top_aggression
                                            and team != self.team][0].actors)*2:
                return 'victorious'
            else:
                return 'aggressive'
        elif top_aggression < len([team for team in team_aggressions
                                  if team_aggressions[team] == top_aggression][0].actors)*2:
            return 'passive'
        elif self.hp == min(actor.hp for actor in self.team.actors) and any(self in actor.weapon.targets(
        ) for actor in [actor for actor in self.fight.actors if actor.team != self.team]):
            return 'vulnerable'
        else:
            return 'protective'

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        mood = self.mood_state()
        self.move_forward(1 if not self.weapon.targets() else 0)
        if 'burning' in self.statuses:
            self.add_action(Skip, 5*self.statuses['burning'].stacks)
        else:
            self.reload(4 - self.energy if self.energy < 5 else 0)
        if mood == 'aggressive' or mood == 'victorious':
            self.attack(self.energy if self.target is not None else 0)
        if mood == 'protective':
            if self.lost_weapon:
                self.add_action(Ability, 5, info=['fgt',  str(self.fight), 'ability', 'pick-up-weapon'])
        if mood == 'vulnerable':
            self.add_action(Ability, self.hp, ability_name='dodge')
        if not sum([value for key, value in self.action_dict.items()]):
            self.attack(1)


class KnifeRat(Rat):

    def stats(self):
        Rat.stats(self)
        self.items.append(items.ThrowingKnife(self))
        self.items.append(items.ThrowingKnife(self))
        self.items.append(items.ThrowingKnife(self))
        self.items.append(items.ThrowingKnife(self))
        self.get_weapon(weapons.Knife(self))

    def form_actions(self):
        Rat.form_actions(self)
        mood = self.mood_state()
        if mood == 'victorious' \
           or mood == 'aggressive' and self.target is None and any(item.name =='throwknife' for item in self.items):
            if self.target is None:
                self.target = get_lowest_hp(self.targets())
            self.add_action(Item, self.energy*2, info=['fgt', str(self.fight), 'item', 'throwknife', str(self.target)])


class InquisitorRat(Rat):
    ai_name = 'rat-inquisitor'

    def __init__(self, game):
        Rat.__init__(self, game)
        self.reloaded = False

    def stats(self):
        Rat.stats(self)
        self.abilities.append(abilities.Thrower(self))
        self.abilities.append(abilities.RatInquisitor(self))
        self.get_weapon(weapons.Torch(self))

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        mood = self.mood_state()
        if 'burning' in self.statuses:
            self.add_action(Skip, 5*self.statuses['burning'].stacks)
        elif self.reloaded:
            self.add_action(Ability, 100, info=['fgt',  str(self.fight), 'ability', 'rat-inquisitor-burn'])
            self.reloaded = False
        else:
            self.reload(4 - self.energy if self.energy < 5 else 0)
        if mood == 'aggressive' or mood == 'victorious':
            self.attack(self.energy if self.target is not None else 0)
            if self.weapon.__class__ == weapons.Torch:
                if not self.weapon.burning:
                    self.add_action(Ability, self.energy*2, info=['fgt',  str(self.fight), 'ability', 'ignite-torch'])
            self.add_action(Ability, self.energy, info=['fgt',  str(self.fight), 'ability', 'thrower',
                                                        str(random.choice(self.targets()))])
            self.add_action(Ability, 5, info=['fgt',  str(self.fight), 'ability', 'pick-up-weapon'])
        if mood == 'vulnerable':
            self.add_action(MoveBack, self.hp if self.weapon.targets() else 0)
        if mood == 'protective' or not sum([value for key, value in self.action_dict.items()]):
            self.add_action(Ability, 5, info=['fgt',  str(self.fight), 'ability', 'pick-up-weapon'])
            if self.weapon.__class__ == weapons.Torch:
                if not self.weapon.burning:
                    self.add_action(Ability, self.energy*2, info=['fgt',  str(self.fight), 'ability', 'ignite-torch'])
                elif any(self in actor.melee_targets for actor in self.fight.actors):
                    self.add_action(MoveBack, 3)
        if not sum([value for key, value in self.action_dict.items()]):
            self.reload(1)

    def recovery(self):
        Rat.recovery(self)
        self.reloaded = True


class HammerRat(Rat):
    def stats(self):
        Rat.stats(self)
        self.abilities.append(abilities.Sturdy(self))
        self.items.append(items.Bomb(self))
        self.items.append(items.Bomb(self))
        self.get_weapon(weapons.SledgeHammer(self))

    def form_actions(self):
        Rat.form_actions(self)
        mood = self.mood_state()
        if mood == 'aggressive' and self.target is not None:
            if self.weapon.special_available(self.target):
                self.add_action(SpecialAttack, self.energy, info=['fgt', str(self.fight), 'special', str(self.target)],
                                order=self.weapon.order)
        if self.target is None and any(item.name == 'bomb' for item in self.items):
            if mood == 'victorious' or mood == 'aggressive' and self.target is None:
                if self.target is None:
                    self.target = get_lowest_hp(self.targets())
            self.add_action(Item, self.energy, info=['fgt', str(self.fight), 'item', 'bomb', str(self.target)])


class CrossbowRat(Rat):

    def stats(self):
        Rat.stats(self)
        self.abilities.append(abilities.Target(self))
        self.abilities.append(abilities.JumpBack(self))
        self.get_weapon(weapons.Crossbow(self))

    def form_actions(self):
        self.clear_actions()
        self.find_target()
        mood = self.mood_state()
        if 'burning' in self.statuses:
            self.add_action(Skip, 5*self.statuses['burning'].stacks)
        else:
            self.reload(4 - self.energy if self.energy < 5 else 0)
        if mood == 'aggressive' or mood == 'victorious':
            if self.weapon.__class__ == weapons.Crossbow:
                if self.weapon.loaded:
                    self.attack(self.energy if self.target is not None else 0)
                else:
                    self.add_action(SpecialWeaponAction, self.energy*2, info=['fgt', str(self.fight), 'special'])
            else:
                self.attack(self.energy if self.target is not None else 0)
        if mood == 'protective':
            if self.lost_weapon:
                self.add_action(Ability, 5, info=['fgt',  str(self.fight), 'ability', 'pick-up-weapon'])
            elif self.weapon.__class__ == weapons.Crossbow:
                if not self.weapon.loaded:
                    self.add_action(SpecialWeaponAction, self.energy*2, info=['fgt', str(self.fight), 'special'])
                elif any(self in actor.melee_targets for actor in self.fight.actors):
                    self.add_action(MoveBack, 3)
        if mood == 'vulnerable':
            self.add_action(Ability, self.hp, ability_name='jump-back')
        if not sum([value for key, value in self.action_dict.items()]):
            if self.weapon.__class__ == weapons.Crossbow:
                if not self.weapon.loaded:
                    self.add_action(SpecialWeaponAction, self.energy*2, info=['fgt', str(self.fight), 'special'])
        if not sum([value for key, value in self.action_dict.items()]):
            self.attack(1)


class RatGeneral(Rat):
    ai_name = 'rat-general'

    def stats(self):
        Rat.stats(self)
        self.abilities.append(abilities.Sturdy(self))
        self.abilities.append(abilities.RatGeneral(self))
        self.get_weapon(weapons.Spear(self))

    def set_difficulty(self, game):
        self.difficulty = get_largest_opponent_team(self, game)
        self.max_hp = 3 + self.difficulty
        self.hp = 3 + self.difficulty
        self.energy = 4 + self.difficulty
        self.max_energy = 4 + self.difficulty
        self.recovery_energy = 4 + self.difficulty
        self.damage = self.difficulty - 1


# Противник, накладывающий кровотечение ударами. Затем он может откусить кусок от истекающего кровью противника, игнорируя
# броню и восстанавливая себе жизни.
class Vanamingo(Ai):
    ai_name = 'vanamingo'

    def stats(self):
        self.default_weapon = weapons.Claws
        self.abilities.append


#class Slug(Ai):


#class Beast(Ai):


#class Crawler(Ai):




