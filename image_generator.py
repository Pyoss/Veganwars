from PIL import Image
import io


def create_dungeon_image(background_image, image_tuple_list):
    background_image = Image.open(background_image)
    width, height = background_image.size

    size_height_dict = {'standard': int(height*2/3),
                        'high': int(height*5/6),
                        'low': int(height*2/5)}
    sized_lists_dict = {'high': [], 'standard': [], 'low': []}

    for tpl in image_tuple_list:
        sized_lists_dict[tpl[1]].append((tpl[0], tpl[2]))

    common_pudding_list = []
    if len(sized_lists_dict['standard']) == len(sized_lists_dict['low']) == len(sized_lists_dict['high']) == 1:
        common_pudding_list = ['high', 'standard', 'low']
    if len(sized_lists_dict['standard']) == len(sized_lists_dict['low']) == 1:
        common_pudding_list = ['standard', 'low']
    elif len(sized_lists_dict['high']) == len(sized_lists_dict['standard']) == 1:
        common_pudding_list = ['high', 'standard']
    elif len(sized_lists_dict['high']) == len(sized_lists_dict['low']) == 1 and len(sized_lists_dict['standard']) == 0:
        common_pudding_list = ['high', 'low']

    class Common:
        common_pudding = 0
        common_item_len = sum([len(sized_lists_dict[item]) for item in common_pudding_list]) if common_pudding_list else 0

    for key in sized_lists_dict:
        current_padding = Common.common_pudding if key in common_pudding_list else 0
        current_height = size_height_dict[key]
        for image_tuple in sized_lists_dict[key]:
            print(image_tuple)
            items_len = len(sized_lists_dict[key]) if key not in common_pudding_list else Common.common_item_len
            width_padding = int(width/(items_len + 1))
            current_padding += width_padding
            if key in common_pudding_list:
                Common.common_pudding += width_padding
            pasting_image = image_tuple[0]
            pasting_width, pasting_height = pasting_image.size
            image_width_padding, image_top_padding = image_tuple[1]
            print(image_tuple[1])
            new_width = int(pasting_width*(current_height/(pasting_height-image_top_padding)))
            pasting_image = pasting_image.resize((new_width, current_height + int(image_top_padding*(current_height/(pasting_height-image_top_padding)))))
            background_image.paste(pasting_image, (int(current_padding-new_width/2) - image_width_padding,
                                                   height - current_height - int(image_top_padding*(current_height/(pasting_height-image_top_padding)))), mask=pasting_image)

    return io_from_PIL(background_image)


def create_duel_image(image_tuple_list):
    background_image = Image.open('D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\Duel.png')
    width, height = background_image.size

    size_height_dict = {'standard': int(height*2/3),
                        'high': int(height*5/6),
                        'low': int(height*2/5)}
    ######
    image_tuple = image_tuple_list[0]
    pasting_image = image_tuple[0]
    pasting_width, pasting_height = pasting_image.size
    image_width_padding, image_top_padding = image_tuple[2]
    current_height = size_height_dict[image_tuple[1]]
    new_width = int(pasting_width*(current_height/pasting_height))
    new_height = current_height + int(image_top_padding*(current_height/pasting_height))
    pasting_image = pasting_image.resize((new_width, new_height))
    background_image.paste(pasting_image,
                           (0, height - current_height - int(image_top_padding*(current_height/pasting_height))),
                           mask=pasting_image)
    ######
    image_tuple = image_tuple_list[1]
    pasting_image = image_tuple[0]
    pasting_width, pasting_height = pasting_image.size

    image_width_padding, image_top_padding = image_tuple[2]
    current_height = size_height_dict[image_tuple[1]]
    new_width = int(pasting_width*(current_height/pasting_height))
    new_height = current_height + int(image_top_padding*(current_height/pasting_height))
    pasting_image = pasting_image.resize((new_width, new_height))
    background_image.paste(pasting_image,
                           (width-new_width,
                            height - current_height - int(image_top_padding*(current_height/pasting_height))),
                           mask=pasting_image)
    return io_from_PIL(background_image)


def io_from_PIL(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

if __name__ == '__main__':
    from fight.unit_files import goblin, goblin_bomber
    from fight import weapons, armors
    unit = goblin.Goblin()
    unit1 = goblin_bomber.GoblinBomber()
    image = create_dungeon_image('D:\YandexDisk\Veganwars\Veganwars\\files\images\\backgrounds\default.jpg', (unit1.get_image(), unit.get_image()))
    image.save('test.png', 'PNG')
