from PIL import Image
import io

def create_dungeon_image(background_image, image_list):
    background_image = Image.open(background_image)
    width, height = background_image.size
    standard_height = int(height*2/3)
    width_padding = int(width/(len(image_list) + 1))
    current_padding = 0
    for image in image_list:
        current_padding += width_padding
        pasting_image = Image.open(image)
        pasting_width, pasting_height = pasting_image.size
        new_width = int(pasting_width*(standard_height/pasting_height))
        pasting_image = pasting_image.resize((new_width, standard_height))
        background_image.paste(pasting_image, (int(current_padding-new_width/2), height - standard_height), mask=pasting_image)

    imgByteArr = io.BytesIO()
    background_image.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr