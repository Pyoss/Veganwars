from fight.units import StandardCreature, units_dict
from fight import abilities


class Human(StandardCreature):
    unit_name = 'human'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        if unit_dict is None:
            self.abilities = [abilities.Dodge(self)]

    def get_image(self):
        image, padding = self.construct_image()
        return image, self.unit_size, padding


units_dict[Human.unit_name] = Human
