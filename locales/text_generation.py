# -*- coding: utf8 -*-

import random

# < | > - один из нескольких
# [ | ] - все в случайном порядке

multiple_choice = ('<', '>')
random_order = ('[', ']')
border = '/'




def get_piece_indexes(starting_index, text_template, delimiter):
            bracket_counter = 1
            bracket_index = starting_index
            while bracket_counter:
                bracket_index += 1
                if text_template[bracket_index] == delimiter[0]:
                    bracket_counter += 1
                elif text_template[bracket_index] == delimiter[1]:
                    bracket_counter -= 1
            return starting_index + 1, bracket_index


def transform_text(from_index, text_template):
    reviewed_symbol = text_template[from_index]
    if reviewed_symbol == multiple_choice[0] or reviewed_symbol == random_order[0]:
        start_index, end_index = get_piece_indexes(from_index, text_template, multiple_choice if reviewed_symbol in multiple_choice else random_order)
        formatted_piece = format_piece(text_template[start_index:end_index], func=get_random if reviewed_symbol == multiple_choice[0] else get_random_order)
        text_template = text_template[:start_index-1] + formatted_piece + text_template[end_index + 1:]
    return text_template


def generate_unique_text(text_template):
    counter_index = 0
    while counter_index < len(text_template) and multiple_choice[0] in text_template:
        reviewed_symbol = text_template[counter_index]
        if reviewed_symbol == multiple_choice[0] or reviewed_symbol == random_order[0]:
            text_template = transform_text(counter_index, text_template)
        counter_index += 1
    return text_template


def get_random(text_template):
    text_list = text_template.split(border)
    return random.choice(text_list)


def get_random_order(text_template):
    text_list = text_template.split(border)
    random.shuffle(text_list)
    text_list = ''.join(text_list)
    return text_list


def format_piece(text, func=get_random):
    while multiple_choice[0] in text:
        counter_index = 0
        while counter_index < len(text):
            reviewed_symbol = text[counter_index]
            if reviewed_symbol == multiple_choice[0] or reviewed_symbol == random_order[0]:
                text = transform_text(counter_index, text)
            counter_index += 1
    text = func(text)
    return text

