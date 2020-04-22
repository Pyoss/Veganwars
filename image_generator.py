from PIL import Image
import io
import os


class ImageObject:
    def __init__(self, image_file: Image, height_type: str, padding_tuple: tuple):
        self.image = image_file
        self.width, self.height = image_file.size
        self.height_type = height_type
        self.padding_width = padding_tuple[0]
        self.padding_height = padding_tuple[1]
        self.background_place = None

    def resize(self, planned_height: int):
        image_modifier = planned_height/(self.height - self.padding_height)
        self.height = int(self.height * image_modifier)
        self.width = int(self.width * image_modifier)
        self.image = self.image.resize((self.width, self.height))
        self.padding_width = int(self.padding_width * image_modifier)
        self.padding_height = int(self.padding_height * image_modifier)

    def get_center(self) -> int:
        return int(self.width/2) + self.padding_width


class ImageBackground:
    def __init__(self, image_file: Image):
        self.image_file = image_file
        self.width, self.height = image_file.size


class ImageConstructor:
    def __init__(self, background: Image, image_objects: tuple):
        print(image_objects)
        self.background_image = background
        self.size_heights = self.get_size_heights()
        self.sized_lists_dict = {'high': [], 'standard': [], 'low': []}
        self.image_objects = [ImageObject(*image_object) for image_object in image_objects]
        self.common_pudding_list = []
        self.padding_markers_dict = None

    def get_size_heights(self):
        return {'standard': int(self.background_image.height*2/3),
                'high': int(self.background_image.height*5/6),
                'low': int(self.background_image.height*2/5)}

    def get_common_height_tier_list(self, resize=False):
        for image_object in self.image_objects:
            image_object.resize(self.size_heights[image_object.height_type if not resize else 'high'])
            self.sized_lists_dict[image_object.height_type].append(image_object)

        if len(self.sized_lists_dict['standard']) == len(self.sized_lists_dict['low']) == len(self.sized_lists_dict['high']) == 1:
            self.common_pudding_list = ['high', 'standard', 'low']
        if len(self.sized_lists_dict['standard']) == len(self.sized_lists_dict['low']) == 1:
            self.common_pudding_list = ['standard', 'low']
        elif len(self.sized_lists_dict['high']) == len(self.sized_lists_dict['standard']) == 1:
            self.common_pudding_list = ['high', 'standard']
        elif len(self.sized_lists_dict['high']) == len(self.sized_lists_dict['low']) == 1 and len(
                self.sized_lists_dict['standard']) == 0:
            self.common_pudding_list = ['high', 'low']

    def setup_markers(self):

        class PaddingMarker:

            def __init__(self):
                self.padding = 0
                self.items_len = 1

        common_marker = PaddingMarker()
        self.padding_markers_dict = {key: common_marker if key in self.common_pudding_list else PaddingMarker()
                                     for key in self.sized_lists_dict.keys()}

        for image_object in self.image_objects:
            marker = self.padding_markers_dict[image_object.height_type]
            marker.items_len += 1

    def get_background_coord(self, image_object):
        padding_marker = self.padding_markers_dict[image_object.height_type]
        padding_coord = int(self.background_image.width/padding_marker.items_len)
        padding_marker.padding += padding_coord
        return padding_marker.padding - image_object.get_center()

    def create_image(self, resize=False):
        self.get_common_height_tier_list(resize)
        self.setup_markers()
        for value in self.sized_lists_dict.values():
            for image_object in value:
                self.background_image.image_file.paste(image_object.image,
                                                       (self.get_background_coord(image_object),
                                                        self.background_image.height - image_object.height),
                                                       mask=image_object.image)


        return self.background_image.image_file


class DuelImage(ImageConstructor):

    def __init__(self, background: Image, image_objects: tuple):
        ImageConstructor.__init__(self, background=background, image_objects=image_objects)
        self.left_corner = int(self.background_image.width/3)
        self.right_corner = int(self.background_image.width/3*2)
        self.left_taken = False

    def get_background_coord(self, image_object):
        if self.left_taken:
            corner = self.right_corner
            return corner
        else:
            corner = self.left_taken
            self.left_taken = True
            return corner + image_object.get_center()


def create_dungeon_image(background, image_tuples, resize=False):
    constructor = ImageConstructor(ImageBackground(Image.open(background)), image_tuples)
    image = constructor.create_image(resize)
    return io_from_PIL(image)


def io_from_PIL(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr


if __name__ == '__main__':
    from fight.unit_files.human import Human
    from fight.unit_files.goblin import Goblin
    from fight import weapons, armors
    unit = Human()
    unit.weapon = weapons.Spear()
    unit.armor = [armors.Cuirass(), armors.HeavyShield()]
    unit1 = Goblin()
    constructor = ImageConstructor(ImageBackground(Image.open('files/images/backgrounds/Duel.png')),
                                                   (unit.get_image(1),))
    image = constructor.create_image()

    image.save('test.png', 'PNG')
