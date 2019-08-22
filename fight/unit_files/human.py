from fight.units import StandardCreature, units_dict
from fight import abilities
from PIL import Image


class Human(StandardCreature):
    unit_name = 'human'

    def __init__(self, name=None, controller=None, fight=None, unit_dict=None, complexity=None):
        StandardCreature.__init__(self, name, controller=controller, fight=fight, unit_dict=unit_dict)
        # Максимальные параметры
        if unit_dict is None:
            self.abilities = [abilities.Dodge(self), abilities.SpellCaster(self)]

    def get_unit_image_dict(self):
        main_armor = next(iter(armor for armor in self.armor if armor.placement == 'body'), None)
        main_armor_name = main_armor.name if main_armor is not None else 'naked'
        return {
            'one-handed':
                {
                    'file': './files/images/armor_bodies/{}/dummy.png'.format(main_armor_name),
                    'right_hand': (30, 320),
                    'left_hand': (220, 320),
                    'body_armor': (110, 200),
                    'head': (111, 30),
                    'width_padding': 0
                },
            'two-handed':
                {
                    'file': './files/images/armor_bodies/{}/dummy_twohanded.png'.format(main_armor_name),
                    'right_hand': (15, 160),
                    'left_hand': (307, 320),
                    'body_armor': (197, 200),
                    'head': (199, 30),
                    'width_padding': 60
                },
            'covers':
                {
                    'hand_one_handed':
                        {
                            'file': './files/images/armor_bodies/{}/cover_arm.png'.format(main_armor_name),
                            'coordinates': (-3, 108)
                        },
                }
        }

    def add_head(self, pil_image, top_padding, left_padding):
        if not any(armor.placement == 'head' and armor.covering for armor in self.armor):
            hairstyle = self.get_hairstyle()
            hairstyle_image = Image.open(hairstyle.path)
            hairstyle_x, hairstyle_y = hairstyle.padding
            head_coord_tuple_x, head_coord_tuple_y = self.get_unit_image_dict()[self.weapon.image_pose]['head']
            pil_image.paste(hairstyle_image, (head_coord_tuple_x - hairstyle_x + left_padding,
                                              head_coord_tuple_y - hairstyle_y + top_padding),
                            mask=hairstyle_image)
            return pil_image
        else:
            return pil_image

    def construct_image(self):
        unit_image_dict = self.get_unit_image_dict()[self.weapon.image_pose]
        equipment_dicts = []
        weapon_image_dict = self.weapon.get_image_dict()
        if weapon_image_dict is not None:
            equipment_dicts.append(weapon_image_dict)
        for armor in self.armor:
            if armor.get_image_dict() is not None:
                equipment_dicts.append(armor.get_image_dict())
        base_width, base_height, top_padding, left_padding = self.calculate_base_image_parameters(unit_image_dict,
                                                                                                  equipment_dicts)
        base_png = Image.new('RGBA', (base_width, base_height), (255, 0, 0, 0))
        base_png.paste(Image.open(unit_image_dict['file']), (left_padding, top_padding))
        base_png = self.add_head(base_png, top_padding, left_padding)
        print(equipment_dicts)
        equipment_dicts.sort(key=lambda i: i['layer'], reverse=True)
        for equipment in equipment_dicts:
            handle_x, handle_y = equipment['handle']
            placement = equipment['placement']
            placement_x, placement_y = unit_image_dict[placement]
            covered = equipment['covered']
            equipment_image = Image.open(equipment['file'])

            base_png.paste(equipment_image,
                           (placement_x - handle_x + left_padding, placement_y - handle_y + top_padding),
                            mask=equipment_image)
            if covered == 'hand_two_handed':
                base_png = self.add_head(base_png, top_padding, left_padding)
            elif covered:
                cover_dict = self.get_unit_image_dict()['covers'][covered]

                cover = Image.open(cover_dict['file'])
                cover_x, cover_y = cover_dict['coordinates']
                base_png.paste(cover, (cover_x + left_padding, cover_y + top_padding), mask=cover)
        return base_png, (left_padding + unit_image_dict['width_padding'], top_padding)

    def get_image(self):
        image, padding = self.construct_image()
        return image, self.unit_size, padding


units_dict[Human.unit_name] = Human
