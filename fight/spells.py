from fight import standart_actions, statuses
from locales import emoji_utils, localization
import sys, inspect, random

class Spell(standart_actions.GameObject):
    sigils = None
    turn_numbers = 1
    db_string = 'spells'

    def start_casting(self, turn_numbers):
        statuses.Casting(self.unit, self.id)
        if turn_numbers > 1:
            statuses.CustomStatus(func=self.second_stage_check, delay=1, order=self.order, unit=self.unit)
        if turn_numbers > 2:
            statuses.CustomStatus(func=self.third_stage_check, delay=2, order=self.order, unit=self.unit)

    def check_casting(self):
        if 'casting' in self.unit.statuses:
            if self.unit.statuses['casting'].spell_id == self.id:
                return True
        return False

    def activate(self, action):
        self.start_casting(self.turn_numbers)
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

    def finish(self):
        self.unit.statuses['casting'].finish()


class Spark(Spell):
    name = 'spark'
    sigils = (emoji_utils.emote_dict['energy_em'], emoji_utils.emote_dict['energy_em'], emoji_utils.emote_dict['energy_em'])
    turn_numbers = 1

    def first_stage(self):
        target = random.choice(self.unit.targets())
        target.receive_damage(1)
        self.string('use', format_dict={'actor':self.unit.name, 'target': target.name})
        self.finish()


class StrongSpark(Spell):
    name = 'strong_spark'
    sigils = (emoji_utils.emote_dict['energy_em'], emoji_utils.emote_dict['energy_em'], emoji_utils.emote_dict['miss_em'])
    turn_numbers = 2

    def first_stage(self):
        standart_actions.AddString(localization.LangTuple('abilities_spellcast',
                                                          'use',
                                                          format_dict={'actor': self.unit.name}),
                                   order=5,
                                   unit=self.unit)

    def second_stage(self):
        target = random.choice(self.unit.targets())
        target.receive_damage(3)
        self.string('use', format_dict={'actor':self.unit.name, 'target': target.name})
        self.finish()



spell_dict = {value.sigils: value for key, value
              in dict(inspect.getmembers(sys.modules[__name__], inspect.isclass)).items()
              if value.sigils is not None}