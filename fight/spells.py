from fight import standart_actions, statuses
from locales import localization
from locales.emoji_utils import emote_dict
import sys, inspect, random, engine


class Spell(standart_actions.GameObject):
    sigils = None
    turn_numbers = 1
    targetable = False
    db_string = 'spells'
    damage = 0
    energy_cost = 2

    def __init__(self, unit):
        standart_actions.GameObject.__init__(self, unit=unit)
        self.target = None
        self.dmg_done = self.damage

    def concentrate(self):
        standart_actions.AddString(localization.LangTuple('unit_' + self.unit.unit_name,
                                                          'cast',
                                                          format_dict={'actor': self.unit.name}),
                                   order=10,
                                   unit=self.unit)

    def use(self):
        self.unit.on_spell(self)
        if self.targetable:
            self.target.receive_spell(self)

    def start_casting(self, action, turn_numbers):
        statuses.Casting(self.unit, self.id, delay=self.turn_numbers)
        self.unit.waste_energy(self.energy_cost)
        if self.targetable:
            self.target = self.unit.fight[action.info[-2]]
        if turn_numbers > 1:
            statuses.CustomStatus(func=self.second_stage_check, delay=1, order=self.order, unit=self.unit,
                                  name='second_stage_{}'.format(self.name))
        if turn_numbers > 2:
            statuses.CustomStatus(func=self.third_stage_check, delay=2, order=self.order, unit=self.unit,
                                  name='third_stage_{}'.format(self.name))

    def check_casting(self):
        if 'casting' in self.unit.statuses:
            if self.unit.statuses['casting'].spell_id == self.id:
                return True
        return False

    def activate(self, action):
        self.start_casting(action, self.turn_numbers)
        self.first_stage_check()

    def first_stage_check(self):
        if self.check_casting():
            self.first_stage()

    def second_stage_check(self):
        if self.check_casting():
            self.second_stage()

    def third_stage_check(self):
        if self.check_casting():
            self.third_stage()

    def first_stage(self):
        pass

    def second_stage(self):
        pass

    def third_stage(self):
        pass


class FireSpell(Spell):
    emote = emote_dict['ignite_em']

    def activate(self, action):
        self.start_casting(action, self.turn_numbers)
        if self.turn_numbers == 1:
            self.check_combust()
        else:
            statuses.CustomStatus(func=self.check_combust, delay=self.turn_numbers-1,
                                  order=2, unit=self.unit,
                                  name='check_combust_{}'.format(self.name))
        self.first_stage_check()

    def combust(self):
        self.dmg_done = 8
        self.unit.statuses['fiery'].string('use', format_dict={'actor': self.unit.name, 'damage': self.dmg_done})
        self.unit.statuses['fiery'].finish()
        if 'casting' in self.unit.statuses:
            self.unit.statuses['casting'].finish()
        self.unit.receive_spell(self)

    def check_combust(self):
        Fiery(self.unit, strength=3+self.turn_numbers)
        fiery = self.unit.statuses['fiery']
        if engine.roll_chance(fiery.strength*10 - 50):
            self.combust()


class Fiery(statuses.Status):
    name = 'fiery'
    emote = emote_dict['fiery_em']
    order = 60
    sigils = None

    def __init__(self, actor, strength=4):
        self.strength = strength
        statuses.Status.__init__(self, actor, acting=True)

    def reapply(self, parent):
        parent.strength += 4

    def activate(self, action=None):
        self.strength -= 1
        if self.strength == 0:
            self.finish()

    def menu_string(self):
        return self.emote + str(self.strength)


# -------------- Anti-Magic Spells ----------------------- #
class SpellShield(Spell):
    name = 'spell_shield'
    sigils = (emote_dict['self_em'], emote_dict['self_em'], emote_dict['palm_em'])
    turn_number = 1
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


class SpellBreak(Spell):
    name = 'spell_break'
    sigils = (emote_dict['palm_em'], emote_dict['strength_em'], emote_dict['palm_em'])
    turn_number = 1
    order = 20
    energy_cost = 1
    targetable = True

    def first_stage(self):
        self.use()
        if 'casting' in self.target.statuses:
            self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})
            self.target.statuses['casting'].finish()
        else:
            self.string('alternative', format_dict={'actor': self.unit.name, 'target': self.target.name})


# -------------- Lighting Spells ----------------------- #
class Spark(Spell):
    name = 'spark'
    sigils = (emote_dict['spark_em'],)
    turn_numbers = 1
    targetable = True
    damage = 1

    def first_stage(self):
        self.use()
        if self.dmg_done > 0:
            self.string('use', format_dict={'actor':self.unit.name, 'target': self.target.name, 'damage': self.dmg_done})


class StrongSpark(Spell):
    name = 'strong_spark'
    sigils = (emote_dict['strength_em'], emote_dict['spark_em'])
    turn_numbers = 2
    targetable = True
    damage = 3

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        target = self.target
        self.use()
        if self.dmg_done > 0:
            self.string('use', format_dict={'actor': self.unit.name, 'target': target.name, 'damage': self.dmg_done})


class RandomSpark(Spell):
    name = 'random_spark'
    sigils = (emote_dict['strength_em'], emote_dict['random_em'], emote_dict['spark_em'])
    turn_numbers = 3
    targetable = True
    damage = 3

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        self.concentrate()

    def third_stage(self):
        target = self.target
        self.dmg_done += random.randint(1,4)
        self.use()
        if self.dmg_done > 0:
            self.string('use', format_dict={'actor': self.unit.name, 'target': target.name, 'damage': self.dmg_done})


class FlyingSpark(Spell):
    name = 'flying_spark'
    sigils = (emote_dict['strength_em'], emote_dict['wind_em'], emote_dict['spark_em'])
    turn_numbers = 3
    targetable = True
    order = 2
    damage = 3

    def first_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def second_stage(self):
        self.unit.action.append('dodge')
        self.string('alternative', format_dict={'actor': self.unit.name})
        statuses.Flying(self.unit, 1)

    def third_stage(self):
        target = self.target
        self.use()
        if self.dmg_done > 0:
            self.string('use', format_dict={'actor': self.unit.name, 'target': target.name, 'damage': self.dmg_done})


class SpellDamage(Spell):
    name = 'spell_damage'
    sigils = (emote_dict['self_em'], emote_dict['spark_em'])
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.use()
        statuses.Buff(self.target, 'spell_damage', 2, 3, emoji='✨')
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})

# -------------- Fire Spells ------------------------- #


class Ignite(FireSpell):
    name = 'ignite'
    sigils = (emote_dict['ignite_em'],)
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.use()
        statuses.Burning(self.target, stacks=2 + int(self.unit.spell_damage/2))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class FireStorm(FireSpell):
    name = 'fire_storm'
    sigils = (emote_dict['earth_em'], emote_dict['random_em'], emote_dict['ignite_em'])
    turn_numbers = 2
    targetable = False

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        self.use()
        damage = random.randint(4, 6) + self.unit.spell_damage
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
                    statuses.Burning(self.target, stacks=2 + int(self.unit.spell_damage/2))
            else:
                self.string('use_2', format_dict={'target': target.name})


class Flash(FireSpell):
    name = 'flash'
    sigils = (emote_dict['palm_em'], emote_dict['ignite_em'])
    order = 3
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.dmg_done = self.unit.spell_damage
        if self.dmg_done:
            self.string('use_1', format_dict={'actor': self.unit.name, 'target': self.target.name, 'damage': self.dmg_done})
        else:
            self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})
        self.use()
        self.target.energy -= 6


class StrongIgnite(FireSpell):
    name = 'strong_ignite'
    sigils = (emote_dict['strength_em'], emote_dict['ignite_em'])
    turn_numbers = 2
    targetable = True

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        self.use()
        statuses.Burning(self.target, 3 + int(self.unit.spell_damage))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class SoulEviction(FireSpell):
    name = 'soul_eviction'
    sigils = (emote_dict['self_em'], emote_dict['ignite_em'])
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
    sigils = (emote_dict['ice_em'],)
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.use()
        statuses.Chilled(self.target, 3 + self.unit.spell_damage)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class StrongChill(Spell):
    name = 'strong_chill'
    sigils = (emote_dict['strength_em'], emote_dict['ice_em'])
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
        statuses.Chilled(self.target, 4 + self.unit.spell_damage*2)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


spell_dict = {value.sigils: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.sigils is not None}
