from fight import standart_actions, statuses
from locales import localization
from locales.emoji_utils import emote_dict
import sys, inspect, random, engine


class Spell(standart_actions.GameObject):
    sigils = None
    base_turn_numbers = 1
    targetable = False
    db_string = 'spells'
    damage = 0
    energy_cost = 2

    def __init__(self, unit, failed=False):
        standart_actions.GameObject.__init__(self, unit=unit)
        self.target = None
        self.dmg_done = self.damage
        self.failed = failed
        self.spell_damage = self.unit.spell_damage
        self.turn_numbers = self.base_turn_numbers - unit.cast_speed
        if self.turn_numbers < 1:
            self.turn_numbers = 1

    def concentrate(self):
        self.check_combust()
        if self.check_casting():
            standart_actions.AddString(localization.LangTuple('unit_' + self.unit.unit_name,
                                                              'cast',
                                                              format_dict={'actor': self.unit.name}),
                                       order=10,
                                       unit=self.unit)

    def check_casting(self):
        if 'casting' in self.unit.statuses:
            if self.unit.statuses['casting'].spell_id == self.id:
                return True
        return False

    def use(self):
        self.unit.on_spell(self)
        if self.targetable:
            self.target.receive_spell(self)

    def activate(self, action):
        statuses.Casting(self.unit, self.id, delay=self.turn_numbers)
        self.unit.waste_energy(self.energy_cost)
        if self.targetable:
            self.target = self.unit.fight[action.info[-2]]
        for turn in range(self.turn_numbers-1):
            statuses.CustomStatus(func=self.concentrate, delay=turn + 1, order=self.order, unit=self.unit,
                                  name='{}_stage_{}'.format(turn, self.name), acting=True)
        statuses.CustomStatus(func=self.casting, delay=self.turn_numbers, order=self.order, unit=self.unit,
                              name='cast_spell_{}'.format(self.name), acting=True)

    def casting(self):
        self.check_combust()
        if self.check_casting():
            self.use()
            self.cast_spell()

    def cast_spell(self):
        pass

    def check_combust(self):
        Overloaded(self.unit)
        overload = self.unit.statuses['overloaded']
        if engine.roll_chance(self.get_combustion_chance(overload.strength)):
            self.combust()

    @staticmethod
    def get_combustion_chance(overload_value):
        combustion_chance = (overload_value - 8) * 8.3
        if combustion_chance >= 99:
            return 99
        elif combustion_chance <= 1:
            return 1
        return int(combustion_chance)

    def combust(self):
        self.dmg_done = 8
        self.unit.statuses['overloaded'].string('use', format_dict={'actor': self.unit.name, 'damage': self.dmg_done})
        self.unit.statuses['overloaded'].finish()
        if 'casting' in self.unit.statuses:
            self.unit.statuses['casting'].finish()
        self.unit.receive_spell(self)


class Overloaded(statuses.Status):
    name = 'overloaded'
    emote = emote_dict['fiery_em']
    order = 60
    sigils = None

    def __init__(self, unit):
        self.strength = unit.spell_overload
        statuses.Status.__init__(self, unit, acting=True)

    def reapply(self, parent):
        parent.strength += parent.unit.spell_overload

    def activate(self, action=None):
        self.strength -= self.unit.overload_cooldown
        if self.strength == 0:
            self.finish()

    def menu_string(self):
        return self.emote + str(self.strength)


def find_spell(spell_tuple):
    for key in spell_dict:
        if all(sigil in key for sigil in spell_tuple) and len(spell_tuple) == len(key):
            return spell_dict[key]
    return False


# -------------- Anti-Magic Spells ----------------------- #
class SpellShield(Spell):
    name = 'spell_shield'
    sigils = (emote_dict['m_self_em'], emote_dict['m_self_em'], emote_dict['m_control_em'])
    base_turn_numbers = 1
    order = 1
    energy_cost = 2

    def first_stage(self):
        self.use()
        self.strength = 4
        self.activated = False
        statuses.CustomPassive(self.unit, types=['receive_spell'], func=self.block, option=None)
        self.string('use', format_dict={'actor': self.unit.name})

    def block(self, action, option):
        if action.dmg_done > 0:
            if not self.activated:
                self.unit.waste_energy(-2)
                self.activated = 1
            dmg = action.dmg_done - self.strength
            if dmg <= 0:
                self.strength = -dmg
                self.string('use_1', format_dict={'actor': action.target.name, 'damage': action.dmg_done})
                dmg = 0
            else:
                self.strength = 0
                self.string('use_2', format_dict={'actor': action.target.name, 'damage': action.dmg_done - self.strength})
            action.dmg_done = dmg


# -------------- Lighting Spells ----------------------- #
class Spark(Spell):
    name = 'spark'
    sigils = (emote_dict['m_spark_em'],)
    base_turn_numbers = 1
    targetable = True
    damage = 1

    def cast_spell(self):
        if self.dmg_done > 0:
            self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name,
                                            'damage': self.dmg_done})

# -------------- Fire Spells ------------------------- #


class FireSpell(Spell):
    emote = emote_dict['m_ignite_em']


class Ignite(FireSpell):
    name = 'ignite'
    sigils = (emote_dict['m_ignite_em'],)
    base_turn_numbers = 1
    targetable = True

    def cast_spell(self):
        statuses.Burning(self.target, stacks=2 + int(self.spell_damage/2))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class FireStorm(FireSpell):
    name = 'fire_storm'
    base_turn_numbers = 2
    targetable = False

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        self.use()
        damage = random.randint(4, 6) + self.spell_damage
        targets = self.unit.targets()
        self.string('use', format_dict={'actor': self.unit.name})
        damage_spread = engine.aoe_split(damage, len(targets))
        damage_index = 0
        for target in targets:
            damage = damage_spread[damage_index]
            damage_index += 1
            if not damage:
                pass
            elif 'dodge' not in target.action:
                self.dmg_done = damage
                self.target = target
                target.receive_spell(self)
                if self.dmg_done:
                    self.string('use_1', format_dict={'target': target.name, 'damage': self.dmg_done})
                if engine.roll_chance(50):
                    statuses.Burning(self.target, stacks=2 + int(self.spell_damage/2))
            else:
                self.string('use_2', format_dict={'target': target.name})


class Flash(FireSpell):
    name = 'flash'
    order = 3
    base_turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.dmg_done = self.spell_damage
        if self.dmg_done:
            self.string('use_1', format_dict={'actor': self.unit.name, 'target': self.target.name, 'damage': self.dmg_done})
        else:
            self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})
        self.use()
        self.target.energy -= 6


class StrongIgnite(FireSpell):
    name = 'strong_ignite'
    base_turn_numbers = 2
    targetable = True

    def cast_spell(self):
        statuses.Burning(self.target, 3 + int(self.spell_damage))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class SoulEviction(FireSpell):
    name = 'soul_eviction'
    turn_numbers = 3
    targetable = True
    order = 20
    damage = 5

    def first_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def second_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def third_stage(self):
        target = self.target
        self.use()
        if 'undead' in target.types:
            self.dmg_done += 5
            self.string('alternative', format_dict={'actor': self.unit.name, 'target': target.name, 'dmg': self.damage})
        else:
            self.string('use', format_dict={'actor': self.unit.name, 'target': target.name, 'dmg': self.damage})


# -------------- Ice Spells ------------------------- #

class Chill(Spell):
    name = 'chill'
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.use()
        statuses.Chilled(self.target, 3 + self.spell_damage)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class StrongChill(Spell):
    name = 'strong_chill'
    turn_numbers = 2
    targetable = True

    def first_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def second_stage(self):
        self.use()
        statuses.Chilled(self.target, 4 + self.spell_damage*2)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


spell_dict = {value.sigils: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.sigils is not None}
