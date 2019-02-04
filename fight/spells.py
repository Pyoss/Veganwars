from fight import standart_actions, statuses
from locales import localization
from locales.emoji_utils import emote_dict
import sys, inspect, random


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
        self.emote = self.sigils[-1]
        self.dmg_done = self.damage

    def concentrate(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def use(self):
        print('{} is casting {}'.format(self.unit.name, self.name))
        self.unit.on_spell(self)
        if self.targetable:
            self.target.receive_spell(self)

    def start_casting(self, action, turn_numbers):
        statuses.Casting(self.unit, self.id)
        self.unit.waste_energy(self.energy_cost)
        if self.targetable:
            self.target = self.unit.fight[action.info[-2]]
        if turn_numbers > 1:
            statuses.CustomStatus(func=self.second_stage_check, delay=1, order=self.order, unit=self.unit,
                                  name='second_stage_{}'.format(self.name))
        if turn_numbers > 2:
            statuses.CustomStatus(func=self.third_stage_check, delay=2, order=self.order, unit=self.unit,
                                  name='third_stage_{}'.format(self.name))
        statuses.CustomStatus(func=self.finish, delay=self.turn_numbers, order=60, unit=self.unit, acting=True,
                              name='finish_spell_{}'.format(self.name))

    def check_casting(self):
        if 'casting' in self.unit.statuses:
            if self.unit.statuses['casting'].spell_id == self.id:
                return True
        return False

    def activate(self, action):
        self.start_casting(action, self.turn_numbers)
        statuses.CustomStatus(func=self.first_stage, delay=1, order=self.order, unit=self.unit,
                              acting=True,
                              name='first_stage_{}'.format(self.name))

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

    def finish(self):
        if 'casting' in self.unit.statuses:
            if self.unit.statuses['casting'].spell_id == self.id:
                self.unit.statuses['casting'].finish()


# -------------- Anti-Magic Spells ----------------------- #
class SpellShield(Spell):
    name = 'spell_shield'
    sigils = (emote_dict['self_em'], emote_dict['self_em'], emote_dict['palm_em'])
    turn_number = 1
    order = 1
    energy_cost = 2

    def first_stage(self):
        self.use()
        statuses.SpellShield(self.unit, 4)
        self.string('use', format_dict={'actor': self.unit.name})


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
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

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
        statuses.Buff(self.target, 'spell_damage', 2, 3)
        self.string('use', format_dict={'actor':self.unit.name, 'target': self.target.name})

# -------------- Fire Spells ------------------------- #


class Ignite(Spell):
    name = 'ignite'
    sigils = (emote_dict['ignite_em'],)
    turn_numbers = 1
    targetable = True

    def first_stage(self):
        self.use()
        statuses.Burning(self.target, stacks=1 + int(self.unit.spell_damage/2))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class StrongIgnite(Spell):
    name = 'strong_ignite'
    sigils = (emote_dict['strength_em'], emote_dict['ignite_em'])
    turn_numbers = 2
    targetable = True

    def first_stage(self):
        self.concentrate()

    def second_stage(self):
        self.use()
        statuses.Burning(self.target, 2 + int(self.unit.spell_damage/2))
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


class SoulEviction(Spell):
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
        statuses.Chilled(self.target, 2 + self.unit.spell_damage)
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
        statuses.Chilled(self.target, 3 + self.unit.spell_damage)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


# ---------------- Misc ------------------------------#
class HexPudge(Spell):
    name = 'hex_pudge'
    sigils = (emote_dict['self_em'], emote_dict['palm_em'], emote_dict['strength_em'])
    turn_numbers = 2
    targetable = True

    def first_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name, 'emote': self.emote}),
                                   order=5,
                                   unit=self.unit)

    def second_stage(self):
        target = self.target
        self.use()
        count = 1
        statuses.Pudged(target,count)
        self.string('use', format_dict={'actor': self.unit.name, 'target': self.target.name})


spell_dict = {value.sigils: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.sigils is not None}
