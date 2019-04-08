from fight.units import Unit, Tech, units_dict
from fight.ai import Ai
from fight import weapons, statuses
from fight.standart_actions import *
import random
from fight.unit_files.skeleton import Skeleton


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


class Lich(Skeleton):
    unit_name = 'lich'
    control_class = LichAi
    types = ['undead', 'boss']
    blood_spell_img = 'AgADAgADeaoxG8zb0EsDfcIlLz_K6IyROQ8ABDkUYT5md9D4O2MBAAEC'
    greet_msg = 'текст-лича'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        complexity = 30 if complexity is None else complexity
        Skeleton.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        self.max_wounds = complexity
        self.wounds = complexity
        self.weapon = weapons.Claws(self)
        self.default_weapon = weapons.Teeth(self)
        self.blood_touch_action = self.create_action('blood_touch', self.blood_touch, 'button_1', order=5)
        self.chain_action = self.create_action('chain', self.chain, 'button_2', order=5)
        self.check_blood_action = self.create_action('check_blood', self.check_blood, 'button_3', order=20)
        self.summon_skeleton_action = self.create_action('summon_skeleton', self.summon_skeleton, 'button', order=11)
        self.chains = False
        if unit_dict is not None:
            self.equip_from_dict(unit_dict)

    def shatter(self):
        self.string('skill_8', format_dict={'actor': self.name})

    def blood_touch(self, action):
        unit = action.unit
        target = unit.target
        statuses.Bleeding(target)
        unit.string('skill_1', format_dict={'actor': unit.name, 'target': target.name})

    def chain(self, action):
        unit = action.unit
        target = unit.target
        unit.chains = True
        unit.chain_turn = unit.fight.turn
        unit.string('skill_2', format_dict={'actor': unit.name, 'target': target.name})

        class Chains(Tech):
            unit_name = 'lich_chains'

            def __init__(chains, name=None, controller=None, fight=None, unit_dict=None, target=None):
                Unit.__init__(chains, name=name, controller=controller, fight=fight, unit_dict=unit_dict)
                chains.wounds = 1
                chains.evasion = -5
                chains.chained = target
                chains.chained.disabled.append(chains.unit_name)

            def dies(chains):
                chains.wounds -= chains.dmg_received
                if chains.wounds <= 0 and chains not in chains.fight.dead:
                    chains.string('died_message', format_dict={'actor': chains.name})
                    chains.chained.disabled.remove(chains.unit_name)
                    unit.chains = False
                    return True

            def alive(chains):
                if chains.wounds > 0:
                    return True
                return False
        chain_unit = unit.summon_unit(Chains, target=target)
        chain_unit.move_forward()

    def check_blood(self, action):
        unit = action.unit
        triggered = False
        for target in unit.targets():
            if any(actn.name == 'bleeding' for actn in target.actions()) and 'bleeding' in target.statuses:
                if target.statuses['bleeding'].strength >= 9:
                    triggered = True
                    break
                elif target.statuses['bleeding'].strength > 6 and 'idle' not in target.action:
                    triggered = True
                    break
        if triggered:
            unit.announce(unit.to_string('skill_5', format_dict={'actor': unit.name}), image=unit.blood_spell_img)
            Custom(unit.string, 'skill_3', unit=unit, order=22, format_dict={'actor': unit.name})
            for target in unit.targets():
                statuses.Bleeding(target)

    def summon_skeleton(self, action):
        unit = action.unit
        unit.summon_unit(Skeleton)
        unit.string('skill_4', format_dict={'actor': unit.name})

units_dict[Lich.unit_name] = Lich
