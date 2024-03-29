#!/usr/bin/env python
# -*- coding: utf-8 -*-
from locales.localization import LangTuple
from locales.emoji_utils import emote_dict
from fight import standart_actions, weapons, ai, statuses, armors, abilities, items
from bot_utils.keyboards import *
import random
import engine
import image_generator
from PIL import Image
import file_manager


class Unit:
    control_class = None
    unit_name = 'unit'
    unit_size = 'standard'
    emote = '?'
    types = ['alive', 'animal']
    summoned = False
    standart_additional = ['move', 'move_back', 'skip']
    experience = 10
    danger = 10
    image = file_manager.my_path + '/files/images/units/default.png'

    # Список предметов, выпадающих из юнита при убийстве. Имеет вид [name: (quantity, chance)]
    default_loot = []
    # Вероятности, с которыми Вы можете получить оружие, броню или предметы цели при её смерти
    default_loot_chances = {'armor': 0, 'weapon': 0, 'items': 0}

    def __init__(self, name, controller=None):

        # То, как осуществляется управление юнитом
        self.controller = controller
        self.unit_name_marker = self.unit_name
        if controller is not None:
            self.controller.unit = self
        self.done = False
        self.active = True
        self.loot = self.default_loot
        self.loot_chances = self.default_loot_chances
        # Список доступных действий для клавиатуры

        # Параметры игрока
        self.name = name
        self.id = engine.rand_id()
        self.fight = None
        self.team = None
        self.lang = None
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.energy = 0
        self.speed = 9
        self.max_recovery = 5
        self.weapon = weapons.Fist(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []

        # Параметры для боя
        self.default_weapon = weapons.Fist(self)
        self.lost_weapon = []
        self.boosted_attributes = {}
        self.death_lang_tuple = None

        # Параметры для заклинаний
        self.spell_damage = 0
        self.spell_overload = 6
        self.overload_cooldown = 2
        self.cast_speed = 0
        self.known_sigils = [emote_dict['m_direction_em'], emote_dict['m_power_em'],
                             emote_dict['m_self_em'], emote_dict['m_control_em']]

        # Временные параметры
        self.blocked_damage = 0
        self.dmg_received = 0
        self.wasted_energy = 0
        self.hp_delta = 0
        self.melee_targets = []
        self.statuses = {}
        self.target = None
        self.action = []
        self.hp_changed = False
        self.weapon_to_member = []

        # Параметры для отсутствия возможности действовать/ходить/атаковать/использовать магию
        self.disabled = []
        self.rooted = []
        self.disarmed = []
        self.silenced = []

        # Параметры для ai
        self.number = 1
        self.named = True
        self.additional_actions = []

    def available_actions(self):
        actions = [(1, WeaponButton(self, self.weapon)), (1, MoveForward(self)), (1, self.weapon.reload_button()),
                   (3, AdditionalKeyboard(self))]
        actions = [*actions, *self.additional_actions]
        return actions

    def add_action(self, func, *args, order=5, to_queue=True, types=None, **kwargs):
        standart_actions.Custom(func, *args, order=order, to_queue=to_queue, unit=self, types=types, **kwargs)

    def equip_from_dict(self, unit_dict):
        for key, value in unit_dict.items():
            if key is not 'controller':
                setattr(self, key, value)
        if 'weapon' not in unit_dict or unit_dict['weapon'] is None:
            self.weapon = self.default_weapon
        else:
            self.weapon = weapons.weapon_dict[unit_dict['weapon']['name']](self, obj_dict=unit_dict['weapon'])
        self.weapons = []
        self.statuses = {}
        if 'abilities' in unit_dict:
            self.abilities = [abilities.ability_dict[ability['name']](self, obj_dict=ability) for ability in unit_dict['abilities']]
        if 'inventory' in unit_dict:
            self.items = engine.Container(base_dict=unit_dict['inventory']).fight_list(self)
            self.inventory = engine.Container(base_dict=unit_dict['inventory']).inv_list(self)
        if 'armor' in unit_dict:
            self.armor = [armors.armor_dict[armor['name']](self, obj_dict=armor) for armor in unit_dict['armor']]
        if 'statuses' in unit_dict:
            for status in unit_dict['statuses']:
                standart_actions.object_dict[status['name']](self, obj_dict=status)

    def get_additional_actions(self):
        actions = [(1, MoveForward(self)),
                   (1, MoveBack(self)),
                   (2, SkipButton(self)),
                    (3, PutOutButton(self))]
        return actions
    # -----------------------  Создание новых способностей для мобов -------------------

    def new_ability(self, ability_name, ability_type, ability_func,
                    ability_available=None, targets=None,
                    name_tuple=None, ability_order=5, cooldown=0):
        types_dict = {'instant': abilities.InstantAbility,
                      'target': abilities.TargetAbility,
                      'opinion': abilities.OptionAbility,
                      'start': abilities.StartAbility,
                      'passive': abilities.Passive,
                      'on_hit': abilities.OnHit,
                      'receive_hit': abilities.ReceiveHit,
                      }

        class AbilityClass(types_dict[ability_type]):
            name = ability_name
            order = ability_order
            name_lng_tuple = name_tuple
            cd = cooldown
            prerequisites = {'lvl': 10000}

            def name_lang_tuple(ability):
                return ability.name_lng_tuple

            def targets(ability):
                return targets(ability)

            def activate(ability, action=None):
                return ability_func(ability, action=action)

            def available(ability):
                return ability_available(ability) if ability_available is not None\
                    else types_dict[ability_type].available(ability)

        abilities.ability_dict[ability_name] = AbilityClass

        if not any(ability.name == ability_name for ability in self.abilities):
            self.abilities.append(AbilityClass(self))
        return AbilityClass

    # -----------------------  Функции создания картинки -------------------

    def get_image(self):
        # сформированная картинка, размер юнита, отступ сверху из-за слишком большого оружия
        image = file_manager.my_path + self.image[1:]
        return Image.open(image), self.unit_size, (0, 0)

    def get_hairstyle(self):
        import hairstyles
        return random.choice([hairstyles.Hairstyle_4])()

    def calculate_base_image_parameters(self, unit_image_dict, equipment_dicts):
        base = unit_image_dict['file']
        image = Image.open(base)
        width, height = image.size
        left_padding = 0
        right_padding = 0
        top_padding = self.get_hairstyle().passed_padding[1] if not any(armor.placement == 'head' and armor.covering for armor in self.armor) else 0
        for dct in equipment_dicts:
            handle_x, handle_y = dct['handle']
            placement = dct['placement']
            placement_x, placement_y = unit_image_dict[placement]
            left_padding = handle_x - placement_x if handle_x - placement_x > left_padding else left_padding
            pot_right_padding = (placement_x - handle_x + Image.open(dct['file']).size[0]) - width
            right_padding = pot_right_padding if pot_right_padding > right_padding else right_padding
            top_padding = handle_y - placement_y if handle_y - placement_y > top_padding else top_padding
        return left_padding + width + right_padding, height + top_padding, top_padding, left_padding

    # -----------------------  Менеджмент энергии и жизней -----------------------------

    def recovery(self):
        pass

    def add_energy(self, number):
        pass

    def waste_energy(self, energy):
        if 'wounded' in self.statuses:
            energy += 5
        self.wasted_energy += energy

    def change_hp(self, hp):
        self.hp_delta += hp
        self.hp_changed = True

    def speed_penalty(self):
        weight = self.weapon.weight
        for armor in self.armor:
            weight += armor.weight
        if any(ability.name == 'speedy' for ability in self.abilities):
            weight -= 1
        return weight

    def get_speed(self):
        return self.speed - self.speed_penalty()

    # -----------------------  Функции, связанные с оружием -----------------------------

    def change_weapon(self):
        if len(self.weapons) > 1:
            self.weapon = self.weapons[0 if self.weapon == self.weapons[1] else 1]
        else:
            self.weapon = self.weapons[0]

    def get_weapon(self, weapon):
        self.weapon = weapon

    @staticmethod
    def get_hit_chance(weapon):
        # Шанс попасть в противника из заданного оружия
        return weapon.get_hit_chance()

    def add_weapon(self, weapon):
        self.weapon = weapon
        self.weapons.append(weapon)

    def change_attribute(self, attr, value):
        if hasattr(self, attr):
            setattr(self, attr, (getattr(self, attr) + value))

    # -----------------------  Функции, связанные с броней -----------------------------

    def equip_armor(self, armor):
        self.armor.append(self)

    # ------------------------  Менеджмент целей и движение -----------------

    def targets(self):
        return [unit for unit in self.fight.units if unit not in self.team.units and unit.alive()]

    def get_melee_targets(self):
        return [unit for unit in self.melee_targets if unit.alive()]

    def get_allies(self):
        return list([unit for unit in self.team.units if unit.alive()])

    def get_targets(self):
        for unit in self.melee_targets:
            if not unit.alive():
                self.melee_targets.remove(unit)

    def move_back(self):
        for actor in self.targets():
            if self in actor.melee_targets:
                actor.melee_targets.remove(self)
        self.melee_targets = []
        statuses.Retreating(self, 1)

    def move_forward(self):
        for team in [tm for tm in self.fight.teams if self not in tm.units]:
            units_to_melee = [unit for unit in team.alive_actors() if 'forward' in unit.action]

            if not units_to_melee:
                units_to_melee = team.alive_actors()
            for unit in units_to_melee:
                if unit not in self.melee_targets:
                    unit.melee_targets.append(self)
                    self.melee_targets.append(unit)
        statuses.Running(self, 1)

    # ------------------------- Активация способностей -------------------

    def activate_statuses(self, sp_type=None, action=None):
        for k, v in list(self.statuses.items()):
            if sp_type is not None:
                if sp_type in v.types and self.alive():
                    v.act(action=action)
            else:
                if self.alive() or 'permanent' in v.types:
                    print(v.name)
                    v.act()

    def activate_abilities(self, sp_type, action=None):
        for ability in self.abilities:
            if sp_type in ability.types:
                ability.act(action=action)

    def before_hit(self, action):
        self.activate_statuses('before_hit', action=action)
        self.activate_abilities('before_hit', action=action)

    def on_hit(self, action):
        self.activate_statuses('on_hit', action=action)
        self.activate_abilities('on_hit', action=action)

    def on_spell(self, spell):
        if spell.dmg_done > 0:
            spell.dmg_done += spell.spell_damage
        self.activate_statuses('on_spell', action=spell)
        self.activate_abilities('on_spell', action=spell)

    def receive_hit(self, action):
        # Применение брони
        if action.dmg_done > 0:
            self.activate_statuses('receive_hit', action=action)
        if action.dmg_done > 0 and action.blockable:
            armor_data = self.activate_armor(action)
            if armor_data[0] >= action.dmg_done:
                if not action.stringed and action.armor_string_alt:
                    standart_actions.Custom(armor_data[1].string, 'use', order=19, unit=self, format_dict={'actor': self.name, 'dmg': action.dmg_done})
                action.dmg_blocked = action.dmg_done
                action.dmg_done = 0
                action.armored = armor_data[1]
            self.activate_abilities('receive_hit', action)

    def receive_spell(self, spell):
        self.activate_statuses('receive_spell', action=spell)
        self.activate_abilities('receive_spell', action=spell)
        if spell.dmg_done > 0:
            self.receive_damage(spell.dmg_done)

    def activate_passives(self):
        self.activate_abilities('passive')

    def actions(self):
        return [action for action in self.fight.action_queue.action_list if action.unit == self]

    # -------------------------- Функции сообщений бота ---------------------

    def get_status_string(self):
        statuses_info = []
        for key, value in self.statuses.items():
            if value.menu_string():
                statuses_info.append(value.menu_string())
        return '|'.join(statuses_info)

    def add_armor_string(self):
        for key in self.act_armor_dict:
            armor_string = LangTuple('fight', 'armor', format_dict={'actor': self.name,
                                                                    'damage_blocked': self.act_armor_dict[key],
                                                                    'armor': LangTuple('armor', key)})
            standart_actions.AddString(armor_string, 22, self)
        self.act_armor_dict = {}

    def info_string(self):
        pass

    def menu_string(self):
        pass

    def start_abilities(self):
        for ability in self.abilities:
            if 'start' in ability.types:
                ability.start_act()

    def announce(self, lang_tuple, image=None):
        self.fight.announce(lang_tuple, image=image)

    # ---------------------------- Методы боя ------------------------------

    def refresh(self):
        self.dmg_received = 0
        self.active = False
        self.target = None
        self.action = []
        self.hp_changed = False
        self.controller.talked = False

    def alive(self):
        pass

    def activate_armor(self, action):
        if not self.armor or self.rooted or self.disabled:
            return 0, None
        armor = list(armor for armor in self.armor if armor.armor > 0 and armor.rating >= action.dmg_done)
        armor.sort(key=lambda x: x.rating)
        blocked_damage = 0
        acted_piece = None
        for piece in armor:
            chance = piece.current_coverage
            if engine.roll_chance(chance):
                blocked_damage = piece.block(action.dmg_done)
                acted_piece = piece
                break
        return blocked_damage, acted_piece

    def receive_damage(self, dmg_done, death_lang_tuple=None):
        # Получение урона
        damage = dmg_done
        self.death_lang_tuple = death_lang_tuple
        self.dmg_received += damage if damage > 0 else 0

    def lose_round(self):
        pass

    def dies(self):
        if not self.alive() and self not in self.fight.dead:
            if self.death_lang_tuple is None:
                self.fight.string_tuple.row(LangTuple('fight', 'death', format_dict={'actor': self.name}))
            else:
                death_tuple = self.get_death_effect_tuple(self.death_lang_tuple)
                if death_tuple is not None:
                    self.fight.string_tuple.row(death_tuple)
                else:
                    self.fight.string_tuple.row(LangTuple('fight', 'death', format_dict={'actor': self.name}))
            return True
        return False

    def get_death_effect_tuple(self, attack_tuple):
        format_dict = {'target': self.name, 'actor': attack_tuple['target']}
        source = attack_tuple['source']
        if 'alive' in self.types:
            lang_tuple = source.lang_tuple('finish_animal')
            lang_tuple.format_dict = format_dict
            return lang_tuple
    # ---------------------------- Служебные методы ------------------------------

    def __str__(self):
        return str(self.id)

    def end_turn(self):
        self.controller.end_turn()

    def get_action(self, edit=False):
        self.controller.get_action(edit=edit)

    def stats(self):
        pass

    def clear(self):
        for armor in self.armor:
            armor.clear()
        for weapon in [*self.lost_weapon, *self.weapon_to_member]:
            self.inventory.append(weapon)

    def to_string(self, string, format_dict=None):
        lang_tuple = localization.LangTuple('unit_' + self.unit_name, string, format_dict=format_dict)
        return lang_tuple

    def string(self, string, format_dict=None, order=0):
        lang_tuple = self.to_string(string, format_dict=format_dict)
        if not order:
            self.fight.string_tuple.row(lang_tuple)
        else:
            standart_actions.AddString(lang_tuple=lang_tuple, unit=self, order=order)

    @staticmethod
    def create_action(name, func, button_name, order=5):
        if name not in standart_actions.action_dict:
            standart_actions.UnitAction(name, func, button_name, order=order)
        return standart_actions.action_dict[name]

    @staticmethod
    def generate_ability(name, func, button_name, order=5, cd=0):
        if name not in standart_actions.action_dict:
            standart_actions.AbilityFactory(name, func, button_name, order=order, cd=cd)
        return standart_actions.action_dict[name]

    def action_button(self, name, button_name, available):
            button = FightButton(button_name, self, name, special='unit_' + self.unit_name)
            button.available = available
            return button

    def boost_attribute(self, key, value):
        if key in self.boosted_attributes:
            self.boosted_attributes[key] += value
        else:
            self.boosted_attributes[key] = value

    def form_ai_name(self):
        same_class_units = [unit for unit in self.team.units if unit.unit_name_marker == self.unit_name_marker and not unit.named]
        if self.number == any(unit.number for unit in same_class_units):
            self.number = len(same_class_units) + 1
        if self.number == 1:
            self.name = localization.LangTuple('unit_' + self.unit_name, 'name')
        else:
            self.name = localization.LangTuple('unit_' + self.unit_name,
                                               'name-number', format_dict={'number': self.number})

    def summon_unit(self, unit_class, name=None, unit_dict=None, **kwargs):
        new_unit = self.fight.add_ai(unit_class, name=name, unit_dict=unit_dict, **kwargs)
        new_unit.team = self.team
        self.team.units.append(new_unit)
        new_unit.summoned = True
        return new_unit

    @staticmethod
    def get_dungeon_format_dict(member, inventory='', inventory_fill=''):
        status_list = ''.join([standart_actions.object_dict[status['name']](obj_dict=status).map_string()
                    for status in member['statuses'] if
                    standart_actions.object_dict[status['name']](obj_dict=status).map_string() is not False])

        return {'name': member.name,
                'hp': member['hp'],
                'max_hp': member['max_hp'] - member['hp'],
                'equipment': member.inventory.get_equipment_string(member.lang),
                'inventory': inventory, 'fill': inventory_fill, 'statuses': status_list,
                'exhaustion': member.max_exhaustion - member.exhaustion, 'max_exhaustion': member.max_exhaustion}

    # Выдавание конечного списка лута при смерти.
    def generate_loot(self):
        if self.lost_weapon:
            self.weapon = self.lost_weapon[0]
        elif self.weapon_to_member:
            self.weapon = self.weapon_to_member[0]
        loot = engine.Container()
        for item in self.loot:
            if engine.roll_chance(item[1][1]):
                loot.put(item[0], value=item[1][0])
        if engine.roll_chance(self.loot_chances['weapon']) and not self.weapon.natural:
            loot.put(self.weapon.name)
        for piece in self.armor:
            if engine.roll_chance(self.loot_chances['armor']):
                loot.put(piece.name)
        for item in self.items:
            if engine.roll_chance(self.loot_chances['items']):
                loot.put(item.name)
        return loot


class StandardCreature(Unit):

    danger = 7

    def __init__(self, name, controller=None, unit_dict=None, complexity=None):
        Unit.__init__(self, name, controller=controller)
        # Максимальные параметры
        self.max_hp = 3
        self.hp = self.max_hp
        self.max_energy = 4
        self.toughness = 6
        self.melee_accuracy = 0
        self.range_accuracy = 0
        self.evasion = 0
        self.damage = 0
        self.default_weapon = weapons.Fist(self)
        self.weapons = []
        self.abilities = []
        self.items = []
        self.armor = []
        self.inventory = []
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = int(self.max_energy/2 + 1)

    def to_dict(self):
        unit_dict = {
            'controller': None,
            'unit_name': self.unit_name,
            'name': self.name,
            'max_hp': self.max_hp,
            'hp': self.hp,
            'max_energy': self.max_energy,
            'melee_accuracy': self.melee_accuracy,
            'range_accuracy': self.range_accuracy,
            'speed': self.speed,
            'max_recovery': self.max_recovery,
            'spell_damage': self.spell_damage,
            'evasion': self.evasion,
            'damage': self.damage,
            'toughness': self.toughness,
            'abilities': [ability.to_dict() for ability in self.abilities],
            'inventory': engine.Container(base_list=[*[item.to_dict() for item in self.items], *[item.to_dict() for item in self.inventory]]).base_dict,
            'armor': [armor.to_dict() for armor in self.armor],
            'weapon': self.weapon,
            'statuses': [status.to_dict() for status in list(self.statuses.values()) if status.to_dict() is not False]
        }
        if unit_dict['weapon'] is not None:
            if unit_dict['weapon'].natural:
                unit_dict['weapon'] = None
            else:
                unit_dict['weapon'] = unit_dict['weapon'].to_dict()
        for key in self.boosted_attributes:
            unit_dict[key] -= self.boosted_attributes[key]
        if unit_dict['hp'] < 1:
            unit_dict['hp'] = 1
            if not any(status['name'] == 'wounded' for status in unit_dict['statuses']):
                unit_dict['statuses'].append(statuses.Wounded().to_dict())
        return unit_dict

    def recovery(self):
        recovery_speed = self.recovery_speed()

        self.energy += recovery_speed
        self.weapon.recovery()
        return recovery_speed

    def recovery_speed(self):
        speed = self.get_speed() if self.get_speed() > 2 and 'exhausted' not in self.statuses else 2
        recovery_speed = speed if speed < self.max_recovery else self.max_recovery
        return recovery_speed

    def add_energy(self, number):
        self.energy += number
        self.max_energy += number

    def info_string(self, lang=None):
        lang = self.lang if lang is None else lang
        ability_list = ', '.join([LangTuple('abilities_' + ability.name, 'name').translate(lang)
                                  for ability in self.abilities if 'tech' not in ability.types])
        item_list = ', '.join([LangTuple('items_' + item.name, 'button').translate(lang)
                               for item in self.items])
        return LangTuple('utils', 'full_info', format_dict={'actor': self.name,
                                                            'hp': self.hp,
                                                            'energy': self.energy,
                                                            'abilities': ability_list,
                                                            'items': item_list})

    def menu_string(self):
        if len(self.weapon.targets()) != 1 or 'option' in self.weapon.types:
            return LangTuple('unit_' + self.unit_name, 'player_menu',
                             format_dict={'actor': self.name, 'hp': self.hp,
                                          'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                     + self.weapon.name, 'name'),
                                          'statuses': self.get_status_string()})
        else:
            menu_string = LangTuple('unit_' + self.unit_name, 'player_menu',
                             format_dict={'actor': self.name, 'hp': self.hp,
                                          'energy': self.energy, 'weapon': LangTuple('weapon_'
                                                                                     + self.weapon.name, 'name'),
                                          'statuses': self.get_status_string()}).translate(self.controller.lang)
            menu_string += '\n'
            # menu_string += self.weapon.get_menu_string(short_menu=False, target=self.weapon.targets()[0].name).translate(self.controller.lang)
            return menu_string

    def refresh(self):
        Unit.refresh(self)
        self.wasted_energy = 0
        self.hp_delta = 0
        if self.energy < 0:
            self.energy = 0
        elif self.energy > self.max_energy:
            self.energy = self.max_energy

    def alive(self):
        if self.hp > 0:
            return True
        else:
            return False

    def lose_round(self):
        if self.dmg_received > 0:
            toughness = self.toughness if self.toughness > 1 else 2
            self.hp_delta -= 1 + self.dmg_received // toughness


class Tech(Unit):
    control_class = ai.TechAi
    types = ['tech']
    summoned = True


class Shadow(StandardCreature):
    unit_name = 'shadow'
    emote = emote_dict['skeleton_em']

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.max_hp = 3
        self.evasion = 1
        self.abilities = [abilities.WeaponSnatcher(self), abilities.Dodge(self)]
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy


units_dict = {}


def fill_unit_dict():
    from fight.unit_files import skeleton, goblin, human, lich, rat,\
        bloodbug, snail, worm, zombie, goblin_bomber, red_oak, ogre, goblin_shaman, dragon, tutorial_goblin



