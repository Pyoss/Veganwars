from locales.emoji_utils import emote_dict
from fight.units import StandardCreature, units_dict
from fight.ai import StandardMeleeAi, Ai
from fight import abilities, weapons


class RatAi(StandardMeleeAi):
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
        StandardMeleeAi.form_actions(self)

    def sledgehammer_weapon_action(self):
        self.move_forward(1 if not self.unit.weapon.targets() else 0)
        self.attack(self.unit.energy if self.unit.target is not None else 0)
        self.reload(5 - self.unit.energy if self.unit.energy < 2 else 0)
        if self.unit.weapon.special_available(target=self.unit.target):
            self.action_weapon_option(self.unit.energy - 1 + self.unit.target.max_energy - self.unit.target.energy
                                      if self.unit.energy > 0 and self.unit.target.energy > 1 else 0,
                                      str(self.unit.target))


class Rat(StandardCreature):
    greet_msg = 'текст-крысы'
    control_class = RatAi
    emote = emote_dict['rat_em']
    unit_name = 'rat'
    image = 'D:\YandexDisk\Veganwars\Veganwars\\files\images\\units\\rat.png'
    unit_size = 'high'

    danger = 15

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        self.damage = 2
        self.toughness = 7
        self.max_hp = 5
        self.max_energy = 6
        if unit_dict is None:
            self.abilities = [abilities.Dodge(self), abilities.Muscle(self)]
            self.weapon = weapons.SledgeHammer(self)
        self.energy = int(self.max_energy / 2 + 1)

units_dict[Rat.unit_name] = Rat
