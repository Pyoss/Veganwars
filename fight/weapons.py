#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fight import statuses, standart_actions
from bot_utils import keyboards, bot_methods
from locales import emoji_utils, localization
import engine
import inspect
import sys
import math


class OneHanded:
    core_types = ['weapon', 'one-handed']
    image_pose = 'one-handed'
    handle = (0, 0)
    weight = 1
    accuracy = 3
    dice_num = 3
    energy_cost = 2
    special_energy_cost = 2
    damage = 0
    damage_cap = 5
    file = './files/images/target.png'

    def get_image_dict(self):
        return {
         'handle': self.handle,
         'placement': 'right_hand',
         'file': self.file,
         'covered': 'hand_one_handed',
         'layer': 1
        }


class TwoHanded:
    core_types = ['weapon', 'two-handed']
    dice_num = 5
    accuracy = 2
    weight = 3
    damage_cap = 10
    energy_cost = 3
    image_pose = 'two-handed'
    handle = (0, 0)
    file = './files/images/target.png'

    def get_image_dict(self):
        return {
         'handle': self.handle,
         'placement': 'right_hand',
         'file': self.file,
         'covered': 'hand_two_handed',
         'layer': 1
        }

# -------------------------------------


class Weapon(standart_actions.GameObject):
    name = None
    natural = False
    melee = True
    range_option = False
    price = 100
    emote = emoji_utils.emote_dict['weapon_em']
    db_string = 'weapon'
    order = 5
    # Типы особого действия (если есть)
    special_types = []
    image_pose = 'two-handed'

    def __init__(self, unit=None, obj_dict=None):
        self.improved = 0
        standart_actions.GameObject.__init__(self, unit=unit, obj_dict=obj_dict)
        self.damage += self.improved

    def string(self, string_code, format_dict=None, order=0):
        format_dict = {} if None else format_dict
        self.unit.fight.string_tuple.row(localization.LangTuple(self.table_row, string_code, format_dict=format_dict))

    def to_dict(self):
        this_dict = standart_actions.GameObject.to_dict(self)
        if self.improved != self.__class__().improved:
            this_dict['improved'] = self.improved
        return this_dict

    def get_hit_chance(self):
        accuracy = self.unit.melee_accuracy if self.melee else self.unit.range_accuracy
        one_hit_chance = (self.accuracy + accuracy + self.unit.energy)
        miss_chance = 100
        for i in range(self.dice_num):
            miss_chance -= miss_chance * one_hit_chance / 10
        return int(100 - miss_chance) if miss_chance < 100 else 0

    def get_damage(self, target):
        accuracy = self.unit.melee_accuracy if self.melee else self.unit.range_accuracy
        energy = self.unit.energy if self.unit.energy < 6 else 5
        modifier = accuracy + self.accuracy - target.evasion + energy
        damage = engine.damage_roll(self.dice_num, modifier)
        if damage:
            damage += self.damage
        if damage > self.damage_cap:
            return self.damage_cap
        return damage

    def reload_button(self):
        if self.melee:
            return keyboards.MeleeReloadButton(self.unit)
        else:
            return keyboards.RangeReloadButton(self.unit)

    def before_hit(self, action):
        pass

    def modify_attack(self, action):
        pass

    def on_hit(self, action):
        pass

    def targets(self):
        return self.unit.get_melee_targets() if self.melee else self.unit.targets()

    def get_action(self):
        if not self.special_types and len(self.targets()) == 1:
            self.unit.target = self.targets()[0]
            attack = standart_actions.Attack(unit=self.unit, fight=self.unit.fight)
            attack.act()
            return True
        keyboard = keyboards.types.InlineKeyboardMarkup(row_width=2)
        buttons = self.attack_buttons()
        for button in buttons:
            keyboard.add(button)
        self.create_menu(keyboard)

    def get_lost(self):
        pass

    def recovery(self):
        pass

    def create_menu(self, keyboard):
        keyboard.add(keyboards.MenuButton(self.unit, 'back'))
        self.unit.controller.edit_message(self.get_menu_string(), reply_markup=keyboard)

    def get_menu_string(self, short_menu=False, target=None):
        if not short_menu:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})
        else:
            return localization.LangTuple(self.table_row, 'short_menu',
                                          format_dict={'chance': self.get_hit_chance(), 'target': target})

    def attack_buttons(self):
        return [keyboards.AttackButton(self.unit, target) for target in self.targets()]

    def special_button(self, target):
        if target is not None:
            return None if not self.special_available(target=target) else \
                keyboards.FightButton('special_button', self.unit,
                                      'special', str(target), special=self.table_row)
        else:
            ready = self.special_available(target=None)
            cd = self.ready_turn - self.unit.fight.turn if self.cd is not 0 else None
            return keyboards.FightButton('special_button', self.unit,
                                         'special', special=self.table_row, ready=ready, cd=cd)

    def activate_special_action(self, target):
        pass

    def start_special_action(self, info):
        pass

    def special_available(self, target):
        return True

    def available(self):
        if self.unit.disarmed:
            return False
        if self.targets() or self.range_option:
            return True

    def info_string(self):
        format_dict = {
            'emote': emoji_utils.emote_dict['range_em' if not self.melee else 'melee_em'],
            'name': localization.LangTuple(self.table_row, 'name'),
            'min_dmg': self.damage + 1,
            'max_dmg': self.dice_num + self.damage,
            'energy': self.energy_cost,
            'accuracy': self.accuracy,
            'info': localization.LangTuple(self.table_row, 'info', format_dict=self.info_dict()),
        }
        return localization.LangTuple('utils',
                                      'weapon-info', format_dict=format_dict)

    def info_dict(self):
        return {}

    def pop_info(self, call):
        try:
            bot_methods.answer_callback_query(call=call,
                                              text=self.info_string().translate(self.unit.controler.lang))
        except bot_methods.telebot.apihelper.ApiException:
            bot_methods.send_message(call.message.chat.id,
                                     message=self.info_string().translate(self.unit.controler.lang))

    def dungeon_use(self):
        self.dungeon_menu()

    def dungeon_menu(self):
        self.unit.send_message()

    def dungeon_buttons(self):
        if self.name == self.unit.weapon:
            main_key = keyboards.DungeonButton('strip', self.unit, 'strip')
        else:
            main_key = keyboards.DungeonButton('equip', self.unit, 'equip')
        return [main_key, keyboards.DungeonButton('equip', self.unit, 'inventory'),
                ]

    def get_image_dict(self):
        return None

    def error_text(self):
        if not self.ready():
            return 'Оружие еще не готово'


class SpecialActionWeapon(Weapon):
    special_types = ['special']

    def get_action(self):
        keyboard = keyboards.form_keyboard(*self.attack_buttons())
        keyboard.add(self.special_button(target=None))
        self.create_menu(keyboard)

    def start_special_action(self, info):
        standart_actions.Custom(self.activate_special_action, order=self.order, unit=self.unit)

    def special_available(self, target):
        return self.ready()


class SpecialOptionWeapon(Weapon):
    special_types = ['option']

    def get_action(self):
        keyboard = keyboards.form_keyboard(*self.attack_buttons())
        if self.special_available(target=None):
            keyboard.add(self.special_button(target=None))
        self.create_menu(keyboard)

    def special_button(self, target):
        if target is not None:
            return None if not self.special_available(target=target) else \
                keyboards.FightButton('special_button', self.unit,
                                      'wpspecial', str(target), special=self.table_row)
        else:
            return keyboards.FightButton('special_button', self.unit,
                                         'wpspecial', special=self.table_row)

    def target_keyboard(self):
        return keyboards.form_keyboard(*self.options_keyboard(),
                                       keyboards.MenuButton(self.unit, 'back'))

    def options(self):
        return []

    def options_keyboard(self):
        return [keyboards.FightButton(option[0], self.unit,
                                      'wpspecial', str(option[1]), named=True) for option in self.options()]

    def modify_attack(self, action):
        pass

    def start_special_action(self, info):
        if len(info) > 4:
            standart_actions.Custom(self.activate_special_action, info[-1], order=self.order, unit=self.unit)
            self.unit.end_turn()
        else:
            self.unit.active = True
            self.ask_options()

    def activate_special_action(self, info):
        pass

    def ask_options(self):
        keyboard = self.target_keyboard()
        self.unit.controller.edit_message(localization.LangTuple(self.table_row, 'weapon_menu_2',
                                      format_dict={'chance': self.get_hit_chance()}), reply_markup=keyboard)

    def special_available(self, target=None):
        if self.ready_turn <= self.unit.fight.turn:
            return True
        return False


class SpecialTargetWeapon(Weapon):
    special_types = ['attack']

    def get_action(self):
        keyboard = keyboards.form_keyboard()
        for target in self.targets():
            keyboard.add(keyboards.AttackButton(self.unit, target), self.special_button(target=target)) if \
                self.special_available(target=target) else keyboard.add(keyboards.AttackButton(self.unit, target))
        self.create_menu(keyboard)

    def start_special_action(self, info):
        target = self.unit.fight[info[-1]]
        standart_actions.Custom(self.activate_special_action, target,
                                order=self.order, unit=self.unit)

    def activate_special_action(self, target):
        Weapon.activate_special_action(self, target=target)


class SpecialAttackWeapon(SpecialTargetWeapon):
    def start_special_action(self, info):
        self.unit.target = self.unit.fight[info[-1]]
        if self.special_available(target=self.unit.target):
            self.unit.fight.edit_queue(standart_actions.SpecialAttack(unit=self.unit, fight=self.unit.fight,
                                                                      info=info, order=self.order, energy_cost=self.special_energy_cost))
        else:
            self.unit.fight.edit_queue(standart_actions.Attack(unit=self.unit, fight=self.unit.fight,
                                                               info=info))

    def modify_attack(self, action):
        pass


# -------------------------------------


class Sword(SpecialOptionWeapon):
    name = 'sword'
    order = 0
    cd = 2

    def activate_special_action(self, option):
        self.unit.waste_energy(1)
        self.on_cd()
        self.string('special_hit', format_dict={'actor': self.unit.name, 'option': option})
        statuses.CustomPassive(self.unit, types=['receive_hit'], func=self.parry, option=option)

    def parry(self, action, option):
        if action.dmg_done == int(option):
            self.string('special_hit_self', format_dict={'actor':self.unit.name, 'target': action.unit.name})
            action.dmg_done = 0
            action.stringed = False
            x = standart_actions.Attack(self.unit, self.unit.fight, order=6)
            x.activate(target=action.unit, waste=1)
        elif action.dmg_done == int(option) - 1:
            action.dmg_done = 0
            action.stringed = False
            self.string('special_miss', format_dict={'actor': self.unit.name, 'target': action.unit.name})

    def options(self):
        return [(str(n+1), str(n+1)) for n in range(3)]

    def target_keyboard(self):
        return keyboards.form_keyboard(*self.options_keyboard(),
                                       keyboards.MenuButton(self.unit, 'back'), row_width=3)


# Оружие, проверенное на работоспособность с системой данжей
class Knife(OneHanded, Weapon):
    name = 'knife'
    bleed_chance_modifier = 5
    handle = (15, 10)
    file = './files/images/knife.png'

    def __init__(self, unit=None, obj_dict=None):
        OneHanded.__init__(self)
        Weapon.__init__(self, unit=unit, obj_dict=obj_dict)
        self.bleed_applied_turn = 0

    def on_hit(self, attack_action):
        if attack_action.dmg_done and engine.roll_chance(
                self.get_bleed_chance()) and 'alive' in attack_action.target.types:
            statuses.Bleeding(attack_action.unit.target)
            attack_action.to_emotes(emoji_utils.emote_dict['bleeding_em'])
            self.bleed_applied_turn = self.unit.fight.turn

    def info_dict(self):
        return {'bleed_chance': self.bleed_chance_modifier}

    def get_menu_string(self, short_menu=False, target=None):
        if not short_menu:
            return localization.LangTuple(self.table_row, 'weapon_menu_1' ,
                                          format_dict={'chance': self.get_hit_chance(), 'bleed_chance': self.get_bleed_chance()})
        else:
            return localization.LangTuple(self.table_row, 'short_menu',
                                          format_dict={'chance': self.get_hit_chance(), 'target': target, 'bleed_chance': self.get_bleed_chance()})

    def get_bleed_chance(self):
        chance = (self.unit.fight.turn - self.bleed_applied_turn)\
               * (self.bleed_chance_modifier + self.unit.get_speed())
        return chance if chance < 100 else 100


class Spear(OneHanded, SpecialActionWeapon):
    name = 'spear'
    order = 0
    handle = (73, 121)
    special_energy_cost = 1
    cd = 1
    file = './files/images/spear.png'

    def activate_special_action(self, target=None):
        self.on_cd()
        targets = [target for target in self.targets()
                   if any('attack' in action.action_type for action in target.actions())
                   and target.target == self.unit]
        if targets:
            standart_actions.Custom(self.counterattack, targets[0], order=10, unit=self.unit)
        else:
            standart_actions.AddString(localization.LangTuple(self.table_row,
                                                              'special_1_miss', format_dict={'actor': self.unit.name}),
                                       order=0, unit=self.unit)
            self.unit.waste_energy(self.special_energy_cost)

    def counterattack(self, target):
        self.unit.melee_accuracy += 2
        self.unit.target = target
        x = standart_actions.SpecialAttack(self.unit, self.unit.fight, order=6, info=None, energy_cost=None)
        x.activate()
        self.unit.melee_accuracy -= 2


class Fist(OneHanded, Weapon):
    name = 'fist'
    types = ['unique', 'natural']
    natural = True
    accuracy = 2
    dice_num = 2
    energy_cost = 2


class Cleaver(TwoHanded, Weapon):
    name = 'cleaver'
    weight = 6
    energy_cost = 4
    damage = 4
    dice_num = 6
    accuracy = -3
    damage_cap = 100

    # -------------------------
    handle = (50, 270)
    file = './files/images/cleaver.png'


class Hatchet(OneHanded, Weapon):
    name = 'hatchet'
    cripple_chance_modifier = 5

    # -------------------------
    handle = (40, 30)
    file = './files/images/hatchet.png'

    def __init__(self, unit=None, obj_dict=None):
        OneHanded.__init__(self)
        Weapon.__init__(self, unit=unit, obj_dict=obj_dict)

    def on_hit(self, attack_action):
        if attack_action.dmg_done and engine.roll_chance(self.get_cripple_chance()):
            if 'alive' in attack_action.target.types:
                statuses.Crippled(attack_action.unit.target)
                attack_action.to_emotes(emoji_utils.emote_dict['crippled_em'])
            else:
                attack_action.dmg_done += 1

    def info_dict(self):
        return {'bleed_chance': self.cripple_chance_modifier}

    def get_menu_string(self, short_menu=False, target=None):
        if not short_menu:
            return localization.LangTuple(self.table_row, 'weapon_menu_1' ,
                                          format_dict={'chance': self.get_hit_chance(), 'cripple_chance': self.get_cripple_chance()})
        else:
            return localization.LangTuple(self.table_row, 'short_menu',
                                          format_dict={'chance': self.get_hit_chance(), 'target': target, 'cripple_chance': self.get_cripple_chance()})

    def get_cripple_chance(self):
        chance = (self.cripple_chance_modifier + self.unit.get_speed())*3
        return chance if chance < 100 else 100


class Axe(TwoHanded, Hatchet):
    name = 'axe'
    cripple_chance_modifier = 10

    # -------------------------
    handle = (40, 270)
    file = './files/images/axe.png'


class Halberd(TwoHanded, Spear):
    name = 'halberd'

    # -------------------------
    handle = (40, 270)
    file = './files/images/halberd.png'


class Bow(OneHanded, SpecialActionWeapon):
    name = 'bow'
    order = 5
    melee = False
    energy_cost = 3
    draw_damage = 2
    draw_accuracy = 1
    handle = (137, 315)
    file = './files/images/great_bow.png'

    def __init__(self, unit=None, obj_dict=None):
        SpecialActionWeapon.__init__(self, unit=unit, obj_dict=obj_dict)
        self.drown = 0
        self.draw_turn = 0

    def before_hit(self, action):
        if self.drown and self.draw_turn + 1 == self.unit.fight.turn:
            self.accuracy += self.drown
        else:
            self.drown = 0

    def on_hit(self, action):
        if action.dmg_done:
            action.dmg_done += self.drown * self.draw_damage
        if self.drown:
            self.accuracy -= self.drown
        self.drown = 0

    def get_menu_string(self):
        if self.drown and self.draw_turn + 1 == self.unit.fight.turn:
            return localization.LangTuple(self.table_row, 'weapon_menu_2',
                                          format_dict={'chance': self.get_hit_chance(),
                                                       'drown': self.drown})
        else:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})

    def special_available(self, target=None):
        print('Натяжение лука:{}'.format(self.drown))
        return False if self.drown > 1 else True

    def activate_special_action(self, target=None):
        if self.draw_turn + 1 == self.unit.fight.turn:
            self.drown += 1
        else:
            self.drown = 1
        self.draw_turn = self.unit.fight.turn
        self.string('special_hit', format_dict={'actor': self.unit.name})

    def recovery(self):
        self.draw_turn = self.unit.fight.turn

    def reload_button(self):
        return keyboards.MeleeReloadButton(self.unit)

    def error_text(self):
        return 'Вы не можете натянуть Лук сильнее.'


class Chain(OneHanded, SpecialActionWeapon):
    name = 'chain'
    order = 5
    swing_accuracy = 2
    range_option = True
    # -------------------------------------
    handle = (40, 30)
    file = './files/images/chain.png'

    def __init__(self, unit=None, obj_dict=None):
        SpecialActionWeapon.__init__(self, unit=unit, obj_dict=obj_dict)
        self.swinging = False

    def before_hit(self, action):
        if self.swinging:
            self.accuracy += self.swing_accuracy
            action.to_emotes(emoji_utils.emote_dict['chain_em'])

    def on_hit(self, action):
        if self.swinging:
            self.accuracy -= self.swing_accuracy
            self.swinging = False
            self.unit.waste_energy(-self.energy_cost)

    def special_available(self, target=None):
        return False if self.swinging else True

    def activate_special_action(self, target=None):
        self.swinging = True
        self.string('special_hit', format_dict={'actor': self.unit.name})

    def error_text(self):
        return 'Вы уже крутите Цепь.'


class Crossbow(TwoHanded, SpecialActionWeapon):
    name = 'crossbow'
    order = 5
    damage = 3
    melee = False

    def __init__(self, unit=None, obj_dict=None):
        SpecialActionWeapon.__init__(self, unit=unit, obj_dict=obj_dict)
        self.loaded = False

    def on_hit(self, action):
        self.loaded = False

    def targets(self):
        return SpecialActionWeapon.targets(self)

    def attack_buttons(self):
        return [keyboards.AttackButton(self.unit, target) for target in self.targets()] if self.loaded else []

    def available(self):
        return True

    def get_menu_string(self, sp_string=None):
        if self.loaded:
            return localization.LangTuple(self.table_row, 'weapon_menu_2',
                                          format_dict={'chance': self.get_hit_chance()})
        else:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})

    def special_available(self, target=None):
        return False if self.loaded else True

    def activate_special_action(self, target=None):
        self.loaded = True
        self.string('special_hit', format_dict={'actor': self.unit.name})

    def reload_button(self):
        return keyboards.MeleeReloadButton(self.unit)


class SledgeHammer(TwoHanded, SpecialAttackWeapon):
    name = 'sledgehammer'
    order = 9
    special_energy_cost = 4

    def modify_attack(self, action):
        if action.dmg_done:
            action.dmg_done += self.unit.target.max_energy - self.unit.target.energy + self.unit.target.wasted_energy

    def start_special_action(self, info):
        self.unit.target = self.unit.fight[info[-1]]
        if self.special_available(target=self.unit.target):
            self.unit.fight.edit_queue(standart_actions.SpecialAttack(unit=self.unit, fight=self.unit.fight,
                                                                      info=info, order=self.order, energy_cost=self.special_energy_cost))
            self.unit.fight.edit_queue(standart_actions.Custom(self.unit.waste_energy, self.special_energy_cost,
                                                               unit=self.unit))
        else:
            self.unit.fight.edit_queue(standart_actions.Attack(unit=self.unit, fight=self.unit.fight,
                                                               info=info))

    def special_available(self, target):
        return True if self.unit.energy > self.special_energy_cost else False


class Harpoon(SpecialOptionWeapon, Knife):
    name = 'harpoon'
    order = 9
    special_energy_cost = 4
    bleed_chance = 100
    range_option = True

    def start_special_action(self, info):
        if len(info) > 4:
            self.melee = False
            self.unit.target = self.unit.fight[info[-1]]
            standart_actions.Custom(self.activate_special_action, info, order=self.order, unit=self.unit)
            self.unit.end_turn()
        else:
            self.unit.active = True
            self.ask_options()

    def activate_special_action(self, info):
        attack = standart_actions.SpecialAttack(unit=self.unit, fight=self.unit.fight,
                                       info=None, order=self.order, energy_cost=self.special_energy_cost)
        attack.activate()
        self.unit.lose_weapon()

    def get_menu_string(self, sp_string=None):
        return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                      format_dict={'chance': self.get_hit_chance()})

    def options(self):
        self.melee = False
        targets = self.targets()
        self.melee = True
        return [(unit.name, str(unit)) for unit in targets]

    def on_hit(self, attack_action):
        if not self.melee:
            if attack_action.dmg_done and engine.roll_chance(
                    self.bleed_chance
            ) and 'alive' in attack_action.target.types:

                statuses.Bleeding(attack_action.unit.target)
                attack_action.to_emotes(emoji_utils.emote_dict['bleeding_em'])
            self.melee = True


# --------------------------------------------------
class Shovel(OneHanded, Weapon):
    name = 'shovel'
    confuse_chance = 45

    def on_hit(self, action):
        if action.dmg_done and engine.roll_chance(self.confuse_chance):
            statuses.Confused(action.target)
            action.to_emotes(emoji_utils.emote_dict['confused_em'])

    def info_dict(self):
        return {'confuse_chance': self.confuse_chance}


class Flamethrower(OneHanded, Weapon):
    name = 'flamethrower'
    accuracy = 3
    dice_num = 1
    energy_cost = 3
    melee = False

    def on_hit(self, attack_action):
        if attack_action.dmg_done:
            statuses.Burning(attack_action.actor.target)
            attack_action.to_emotes(emoji_utils.emote_dict['fire_em'])


class Revolver(OneHanded, Weapon):
    name = 'revolver'
    accuracy = 3
    dice_num = 1
    damage = 2
    energy = 3
    melee = False


class Mace(OneHanded, Weapon):
    name = 'mace'

    def __init__(self, actor):
        Weapon.__init__(self, actor)
        self.combo_turn = 0
        self.damage_stacked = 0

    def on_hit(self, attack_action):
        if attack_action.dmg_done and self.combo_turn == self.unit.fight.turn:
            attack_action.dmg_done += self.damage_stacked
            attack_action.to_emotes(emoji_utils.emote_dict['mace_em'])
        if self.combo_turn == self.unit.fight.turn:
            if self.damage_stacked < 3:
                self.damage_stacked += 1
        else:
            self.damage_stacked = 1
        self.combo_turn = self.unit.fight.turn + 1


class Knuckles(OneHanded, Weapon):
    name = 'knuckles'
    accuracy = 2
    dice_num = 2
    energy_loss = 4

    def __init__(self, actor):
        Weapon.__init__(self, actor)

    def on_hit(self, attack_action):
        if attack_action.dmg_done and 'reload' in attack_action.target.action:
            attack_action.target.waste_energy(4)
            attack_action.str = 'special'

    def info_dict(self):
        return {'energy_loss': self.energy_loss}


class BaseballBat(OneHanded, Weapon):
    name = 'baseball-bat'
    stun_chance = 25

    def __init__(self, actor):
        Weapon.__init__(self, actor)

    def on_hit(self, attack_action):
        if attack_action.dmg_done and engine.roll_chance(self.stun_chance):
            statuses.Stun(attack_action.target)
            attack_action.to_emotes(emoji_utils.emote_dict['stun_em'])

    def info_dict(self):
        return {'stun_chance': self.stun_chance}


class BearClaw(BaseballBat):
    name = 'bear-claw'
    stun_chance = 70
    types = ['natural']
    natural = True


class RukhBeak(OneHanded, Weapon):
    name = 'rukh-beak'
    types = ['natural']
    natural = True
    damage = 1
    dice_num = 4
    accuracy = 0


class RedOakBranch(OneHanded, Weapon):
    name = 'red-oak-branch'
    types = ['unique', 'natural']
    natural = True
    accuracy = 2
    dice_num = 5
    energy_cost = 2


class RedOakAncor(OneHanded, Weapon):
    name = 'red-oak-ancor'
    types = ['unique', 'natural']
    natural = True
    accuracy = 2
    dice_num = 2
    energy_cost = 2
    damage_cap = 2
    melee = False


class Cock(OneHanded, Weapon):
    name = 'cock'
    types = ['natural']
    natural = True


class SniperRifle(OneHanded, SpecialTargetWeapon):
    name = 'sniper-rifle'
    order = 1
    dice_num = 1
    damage = 7
    energy = 5
    accuracy = -3
    melee = False

    def __init__(self, actor):
        SpecialTargetWeapon.__init__(self, actor)
        self.aim_target = None
        self.bonus_accuracy = 3
        self.stacked_accuracy = 0
        self.bonus_accuracy = 4
        self.activated = False

    def get_lost(self):
        self.aim_target = None
        self.bonus_accuracy = 3
        self.stacked_accuracy = 0
        self.bonus_accuracy = 4
        self.activated = False

    def activate_special_action(self, target):
        if self.aim_target != target:
            self.aim_target = target
            self.stacked_accuracy = self.bonus_accuracy
        else:
            self.stacked_accuracy += self.bonus_accuracy
        self.string('special_hit', format_dict={'actor': self.unit.name, 'target': target.name})

    def get_target_hit_chance(self):
        accuracy = self.unit.melee_accuracy if self.melee else self.unit.range_accuracy
        one_hit_chance = (self.accuracy + accuracy + self.stacked_accuracy + self.unit.energy)
        miss_chance = 100
        for i in range(self.dice_num):
            miss_chance -= miss_chance * one_hit_chance / 10
        return int(100 - miss_chance)

    def get_menu_string(self):
        if self.aim_target is None:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})
        else:
            return localization.LangTuple(self.table_row, 'weapon_menu_2',
                                          format_dict={'chance': self.get_hit_chance(),
                                                       'target': self.aim_target.name,
                                                       'target_chance': self.get_target_hit_chance()})

    def before_hit(self, action):
        if action.actor.target == self.aim_target:
            action.actor.range_accuracy += self.bonus_accuracy * self.stacked_accuracy
            self.activated = True
        self.aim_target = None

    def on_hit(self, action):
        if self.activated:
            action.actor.range_accuracy -= self.bonus_accuracy * self.stacked_accuracy
            self.activated = False
            self.stacked_accuracy = 0


class Whip(OneHanded, SpecialTargetWeapon):
    name = 'whip'
    order = 2

    def __init__(self, actor):
        Weapon.__init__(self, actor)
        self.bonus_damage = 1
        self.bonus_energy = 2

    def activate_special_action(self, target):
        self.string('special_hit', format_dict={'actor': self.unit.name, 'target': target.name})
        statuses.Buff(target, 'damage', self.bonus_damage, 1)
        target.energy += self.bonus_energy
        target.dmg_received += 1
        self.unit.waste_energy(self.energy)

    def get_action(self):
        keyboard = keyboards.form_keyboard()
        for target in self.targets():
            if target in self.unit.team.actors:
                if target.alive() and target != self.unit:
                    keyboard.add(self.special_button(target))
            else:
                keyboard.add(keyboards.AttackButton(self.unit, target))
        self.create_menu(keyboard)

    def special_button(self, target):
        return keyboards.FightButton(target.name, self.unit,
                                     'special', str(target), special=self.table_row, named=True)

    def targets(self):
        return [*self.unit.melee_targets, *[actor for actor in self.unit.team.actors if actor != self.unit]]


class Katana(SpecialAttackWeapon, Knife):
    name = 'katana'
    order = 9
    bleed_chance = 15
    handle = (33, 171)
    file = './files/images/katana.png'

    def modify_attack(self, action):
        if action.dmg_done:
            action.target.hp_delta -= 1
        self.unit.wasted_energy += 2

    def special_available(self, target):
        return True if target.hp == 1 and self.unit.energy > 3 else False

    def info_dict(self):
        return {'bleed_chance': self.bleed_chance}


class Fangs(Knife):
    name = 'fangs'
    types = ['unique', 'natural']
    natural = True


class Sting(Knife):
    name = 'sting'
    types = ['unique', 'natural']
    natural = True
    bleed_chance_modifier = 10
    damage_cap = 1


class Teeth(Knife):
    name = 'teeth'
    types = ['unique', 'natural']
    natural = True
    accuracy = 2
    dice_num = 2
    bleed_chance_modifier = 0


class Claws(Knife):
    name = 'fangs'
    types = ['unique', 'natural']
    natural = True


class PoisonedFangs(OneHanded, Weapon):
    name = 'poison-fangs'
    types = ['unique', 'natural']
    natural = True
    poison_chance = 70
    dice_num = 2
    accuracy = 0

    def on_hit(self, attack_action):
        if attack_action.dmg_done and engine.roll_chance(self.poison_chance):
            if 'undead' or 'zombie' not in attack_action.target.types:
                statuses.Poison(attack_action.unit.target)
                attack_action.to_emotes(emoji_utils.emote_dict['poisoned_em'])


class PoisonedBloodyFangs(OneHanded, Weapon):
    name = 'poison-bloody-fangs'
    types = ['unique', 'natural']
    natural = True
    poison_chance = 70
    dice_num = 3
    accuracy = 2

    def on_hit(self, attack_action):
        if attack_action.dmg_done and engine.roll_chance(self.poison_chance):
            if 'undead' or 'zombie' not in attack_action.target.types:
                if engine.roll_chance(50):
                    statuses.Poison(attack_action.unit.target)
                    attack_action.to_emotes(emoji_utils.emote_dict['poisoned_em'])
                else:
                    statuses.Bleeding(attack_action.unit.target)
                    attack_action.to_emotes(emoji_utils.emote_dict['bleeding_em'])


class Pistol(OneHanded, Weapon):
    name = 'pistol'
    melee = False
    accuracy = 3
    energy = 3


class Shotgun(OneHanded, Weapon):
    name = 'shotgun'
    melee = False
    dice_num = 6
    energy = 4
    accuracy = 0
    bonus_damage = 1

    def on_hit(self, attack_action):
        if self.unit.target in self.unit.melee_targets and attack_action.dmg_done:
            attack_action.dmg_done += self.bonus_damage
            attack_action.to_emotes(emoji_utils.emote_dict['exclaim_em'])

    def info_dict(self):
        return {'bonus_damage': self.bonus_damage}


class SawnOff(Shotgun):
    name = 'sawn-off'
    melee = False
    dice_num = 8
    accuracy = 1
    energy = 3


class Boomerang(OneHanded, SpecialAttackWeapon):
    name = 'boomerang'
    melee = False
    bleed_chance = 100

    def __init__(self, unit=None, obj_dict=None):
        Weapon.__init__(self, unit=unit, obj_dict=obj_dict)
        self.melee = self.melee
        self.target = None

    def start_special_action(self, info):
        self.melee = True
        SpecialAttackWeapon.start_special_action(self, info)

    def on_hit(self, action):
        if self.melee:
            self.melee = False
        else:
            self.unit.lose_weapon()
            self.unit.lost_weapon.remove(self)
            self.unit.weapon_to_member.append(self)
            self.target = self.unit.target
            statuses.CustomStatus(self.unit, order=0, func=self.go_back, delay=2, permanent=True)
            statuses.CustomStatus(self.unit, order=5, func=self.equip, delay=2)

    def get_damage(self, target, flying=False):
        accuracy = self.unit.melee_accuracy if self.melee else self.unit.range_accuracy
        energy = self.unit.energy if not flying else 5
        modifier = accuracy + self.accuracy - target.evasion + energy
        damage = engine.damage_roll(self.dice_num, modifier)
        if damage:
            damage += self.damage
        return damage

    def go_back(self):

        # Решил, что лучше будет создать дополнительный класс для обратной атаки бумеранга.
        class BackAttack(standart_actions.BaseAttack):

            def __init__(new):
                standart_actions.BaseAttack.__init__(new, self.unit, self.unit.fight, None)
                new.target = self.target

            def activate(new):
                # Определение цели
                new.attack()
                new.on_attack()
                # Добавление описания в строку отчета
                new.string('special_1')

            def string(new, hit_string):
                action = 'hit' if new.dmg_done > 0 else 'miss'
                if new.target == new.unit:
                    action += '_self'
                if hit_string != '':
                    action = hit_string + '_' + action
                attack_dict = {'actor': self.unit.name, 'target': self.target.name,
                               'damage': new.dmg_done if not new.special_emotes else str(new.dmg_done) +
                                                                                     ''.join(new.special_emotes)}
                attack_tuple = localization.LangTuple(self.table_row, action, attack_dict)
                new.fight.string_tuple.row(attack_tuple)

            def attack(new):
                self.before_hit(self)
                # Вычисление нанесенного урона и трата энергии
                new.dmg_done = self.get_damage(self.target, flying=True)
                # Применение способностей и особых свойств оружия
                new.dmg_done += new.unit.damage if new.dmg_done else 0
                new.target.receive_hit(new)

        self.unit.fight.edit_queue(BackAttack())

    def equip(self):
        self.unit.weapon_to_member.remove(self)
        self.unit.get_weapon(self)

    def reload_button(self):
        return keyboards.MeleeReloadButton(self.unit)

    def special_available(self, target=None):
        return True if target in self.unit.melee_targets else False


class Torch(OneHanded, SpecialActionWeapon):
    name = 'torch'
    order = 0

    def __init__(self, actor):
        SpecialActionWeapon.__init__(self, actor)
        self.burning = False
        self.start_fire_turn = -2
        self.burning_turns = 2

    def on_hit(self, action):
        if self.burning and action.dmg_done:
            statuses.Burning(action.actor.target)
            action.to_emotes(emoji_utils.emote_dict['fire_em'])

    def targets(self):
        if self.unit.fight.turn > self.start_fire_turn + self.burning_turns:
            self.burning = False
        return SpecialActionWeapon.targets(self)

    def get_menu_string(self):
        if not self.burning:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})
        else:
            return localization.LangTuple(self.table_row, 'weapon_menu_2',
                                          format_dict={'chance': self.get_hit_chance()})

    def special_available(self, target=None):
        return False


class LasGun(OneHanded, Weapon):
    name = 'lasgun'
    types = ['unique', 'arsenal']
    melee = False
    heating = 6
    damage = 1
    energy = 1
    accuracy = 3

    def __init__(self, actor):
        Weapon.__init__(self, actor)
        self.heat = 0
        self.last_heated = 1

    def on_hit(self, action):
        if engine.roll_chance((self.heat - 4) * 5):
            if engine.roll_chance(50):
                if action.dmg_done:
                    action.dmg_done = action.dmg_done * 2
                    statuses.Burning(action.target)
                    action.str = 'special'
            else:
                action.dmg_done = 0
                self.unit.dmg_received += 1
                statuses.Stun(action.actor)
                action.str = 'special_1'
                self.heat = 0
        self.heat += self.heating

    def targets(self):
        if self.heat and self.last_heated != self.unit.fight.turn:
            self.heat -= (self.unit.fight.turn - self.last_heated) * 2
            self.last_heated = self.unit.fight.turn
        return SpecialActionWeapon.targets(self)

    def recovery(self):
        self.heat -= 2

    def get_menu_string(self):
        if not self.heat - 4 > 0:
            return localization.LangTuple(self.table_row, 'weapon_menu_1',
                                          format_dict={'chance': self.get_hit_chance()})
        else:
            return localization.LangTuple(self.table_row, 'weapon_menu_2',
                                          format_dict={'chance': self.get_hit_chance(),
                                                       'heat': (self.heat - 4) * 5})


class ChainSword(Knife):
    name = 'chainsword'
    types = ['unique', 'arsenal']
    energy = 2
    damage = 1
    bleed_chance = 100


class Target(Fist):
    image_pose = 'two-handed'

    def get_image_dict(self):
        return {
         'handle': (0, 0),
         'placement': 'right_hand',
         'file': './files/images/target.png',
         'covered': True
        }


weapon_dict = {value.name: value for key, value
               in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items() if hasattr(value, 'name')
               and value.name is not None}
weapon_list = [value for k, value in weapon_dict.items()]
for k, v in weapon_dict.items():
    standart_actions.object_dict[k] = v


def get_weapon_statistic(weapon_class):
    class UnitPlaceholder:
        energy = 3
        melee_accuracy = 0
        range_accuracy = 0
        evasion = 0

    unit = UnitPlaceholder()
    weapon = weapon_class(unit=unit)

    result_dict = {}
    for i in range(0, 10000):
        damage = weapon.get_damage(target=unit)
        if damage in result_dict:
            result_dict[damage] += 1
        else:
            result_dict[damage] = 1
    items = result_dict.items()
    x = list(items)
    x.sort(key=lambda y: y[0])
    weapon_value = sum([z[0]*z[1] for z in x])
    print('Вероятность попасть с {} энергии. Оружие - {}.'.format(unit.energy, weapon.name))
    for key in x:
        print(str(key[0]) + ' : ' + str(int(key[1]/100)) + '%')
    print('Weapon value: {}'.format(int(round(weapon_value/1000, 0))))

if __name__ == '__main__':
    get_weapon_statistic(Axe)
