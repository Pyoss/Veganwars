from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi


class SnailAi(StandardMeleeAi):

    def move_forward(self, chance):
        self.add_action(self.unit.crawl_action, chance)

    def form_actions(self):
        StandardMeleeAi.form_actions(self)
        self.make_action(self.unit.split_check_action)


class Snail(StandardCreature):
    unit_name = 'snail'
    control_class = SnailAi
    emote = emote_dict['snail_em']
    image = './files/images/units/snail.png'
    danger = 18
    greet_msg = 'Слизень'
    unit_size = 'high'
    default_loot = [('snail_mucus', (1, 90)),('snail_mucus', (1, 70)),('snail_mucus', (1, 50))]

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, summoned=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        summoned = 0 if summoned is None else summoned
        self.max_hp -= summoned*2
        if self.max_hp < 1:
            self.max_hp = 1
        self.hp = self.max_hp
        self.add_energy(-summoned)
        self.default_weapon = 'teeth'
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)
        self.energy = self.max_energy
        self.split_check_action = self.create_action('split_check', self.split_check, 'button_3', order=59)
        self.crawl_action = self.create_action('worm-crawl-forward', self.crawl, 'button_1', order=10)

    def crawl(self, action):
        action.unit.string('skill_1', format_dict={'actor': action.unit.name})
        self.move_forward()

    def split_check(self, action):
        unit = action.unit
        if unit.hp <= 0 and unit.max_hp > 1:
            unit.split(action)

    def split(self, action):
        unit = action.unit
        unit.summon_unit(Snail, summoned=unit.summoned+1)
        unit.summon_unit(Snail, summoned=unit.summoned+1)
        unit.string('skill_2', format_dict={'actor': unit.name})

    def dies(self):
        if not self.alive() and self not in self.fight.dead:
            return True
        return False

units_dict[Snail.unit_name] = Snail
