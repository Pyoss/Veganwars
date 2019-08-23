from fight.units import StandardCreature, units_dict
from fight import abilities
from PIL import Image
from bot_utils import config


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

    def add_head(self, equipment_dicts, user_id):
        if not any(armor.placement == 'head' and armor.covering for armor in self.armor):
            if user_id is not None and user_id in config.special_units:
                hairstyle_image = './files/images/armor_heads/{}/naked/cover_head.png'.format(config.special_units[user_id])
                hairstyle_x, hairstyle_y = str(open('./files/images/armor_heads/{}/naked/cover_head_coord.txt'.format(config.special_units[user_id])).read()).split()
                hairstyle_x, hairstyle_y = int(hairstyle_x), int(hairstyle_y)
            else:
                hairstyle = self.get_hairstyle()
                hairstyle_image = hairstyle.path
                hairstyle_x, hairstyle_y = hairstyle.padding

            image_dict = {
             'handle': (hairstyle_x, hairstyle_y),
             'placement': 'head',
             'file': hairstyle_image,
             'covered': False,
             'layer': -1
            }
            equipment_dicts.append(image_dict)
        return equipment_dicts

    def construct_image(self, user_id=None):
        unit_image_dict = self.get_unit_image_dict()[self.weapon.image_pose]
        equipment_dicts = []
        equipment_dicts = self.add_head(equipment_dicts, user_id)
        weapon_image_dict = self.weapon.get_image_dict()
        if weapon_image_dict is not None:
            equipment_dicts.append(weapon_image_dict)
        for armor in self.armor:
            if armor.get_image_dict(user_id) is not None:
                equipment_dicts.append(armor.get_image_dict(user_id))
        base_width, base_height, top_padding, left_padding = self.calculate_base_image_parameters(unit_image_dict,
                                                                                                  equipment_dicts)
        base_png = Image.new('RGBA', (base_width, base_height), (255, 0, 0, 0))
        base_png.paste(Image.open(unit_image_dict['file']), (left_padding, top_padding))
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
            if covered:
                cover_dict = self.get_unit_image_dict()['covers'][covered]

                cover = Image.open(cover_dict['file'])
                cover_x, cover_y = cover_dict['coordinates']
                base_png.paste(cover, (cover_x + left_padding, cover_y + top_padding), mask=cover)
        return base_png, (left_padding + unit_image_dict['width_padding'], top_padding)

    def get_image(self, user_id=None):
        image, padding = self.construct_image(user_id)
        return image, self.unit_size, padding


units_dict[Human.unit_name] = Human
