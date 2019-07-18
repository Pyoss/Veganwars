from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi
from fight.standart_actions import *
from fight import weapons, statuses


class BloodBugAi(StandardMeleeAi):
    ai_name = 'bloodbug'

    def move_forward(self, chance):
        self.action_ability('fly', chance)

    def form_actions(self):
        StandardMeleeAi.form_actions(self)


class BloodBug(StandardCreature):
    greet_msg = 'комарик'
    unit_name = 'bloodbug'
    control_class = BloodBugAi
    default_loot = [('chitin', (1, 20))]
    emote = emote_dict['bloodbug_em']
    image = './files/images/units/Bloodbug.png'

    danger = 9

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.max_hp = 4
        self.toughness = 3
        self.hp = 4
        self.max_energy = 4
        self.energy = 4
        self.weapon = weapons.Sting(self)
        self.blood_filled = False
        self.new_ability(ability_name='fly', ability_func=self.fly,
                         ability_type='instant',
                        name_tuple=self.to_string('button_1'))

        self.new_ability(ability_name='get_blood',
                         ability_func=self.get_blood,
                         ability_type='passive',
                         ability_order=21)

    @staticmethod
    def get_blood(ability, action=None):
        unit = ability.unit
        trigger_target = None
        if unit.blood_filled:
            return False
        for target in unit.targets():
            if any(actn.name == 'bleeding' for actn in target.actions()) and 'bleeding' in target.statuses:
                if target.statuses['bleeding'].strength >= 9:
                    trigger_target = target
                    break
                elif target.statuses['bleeding'].strength > 6 and 'idle' not in target.action:
                    trigger_target = target
                    break
        if trigger_target is not None:
            unit.blood_filled = True
            unit.string('skill_2', format_dict={'actor': unit.name, 'target': trigger_target.name})
            unit.start_regenerating()

    @staticmethod
    def fly(ability, action):
        unit = action.unit
        unit.move_forward()
        unit.string('skill_1', format_dict={'actor': unit.name})

    def start_regenerating(self):
        statuses.Buff(self, 'damage', 2, 3)
        statuses.CustomStatus(self, 21, 0, self.regenerate, name='custom_{}_{}'.format('regenerate', engine.rand_id()), acting=True)
        statuses.CustomStatus(self, 21, 1, self.regenerate, name='custom_{}_{}'.format('regenerate', engine.rand_id()))
        statuses.CustomStatus(self, 21, 2, self.regenerate, name='custom_{}_{}'.format('regenerate', engine.rand_id()))
        statuses.CustomStatus(self, 22, 2, self.reset_blood, name='custom_{}_{}'.format('blood_reset', engine.rand_id()))

    def regenerate(self):
        if self.hp < self.max_hp:
            self.change_hp(1)

    def reset_blood(self):
        self.blood_filled = False

units_dict[BloodBug.unit_name] = BloodBug
