#!/usr/bin/env python
# -*- coding: utf-8 -*-
import emoji
import string

emote_dict = {
    # Стандартные эмодзи
    "energy_em": emoji.emojize(':zap:', use_aliases=True),
    "health_em": emoji.emojize(':hearts:', use_aliases=True),
    "lose-health_em": u'\U0001F5A4',
    "gain-health_em": u'\U0001F49A',
    "target_em": emoji.emojize(':dart:', use_aliases=True),
    "exclaim_em": u'\U00002757',
    'warning_em': u'\U000026A0',
    "check_em": u'\U00002714',
    'cross_em': u'\U0000274C',

    # Бой
    "reload_em": u'\U0001F553',
    "melee_em": emoji.emojize(':punch:', use_aliases=True),
    "range_em": u'\U0001F4A5',
    "shield_em": u'\U0001F6E1',
    "miss_em": u'\U0001F4A8',
    "rest_em": u'\U0001F624',
    "move_em": u'\U0001F463',
    "skip_em": emoji.emojize(':arrow_down:', use_aliases=True),
    'death_em': u'\U00002620',

    # Статусы
    "weapon_em": u'\U00002694',
    "bomb_em": emoji.emojize(':bomb:', use_aliases=True),
    "fire_em": emoji.emojize(':fire:', use_aliases=True),
    "stun_em": emoji.emojize(':cyclone:', use_aliases=True),
    "bleeding_em": u'\U00002763',
    'afk_em': u'\U0001F4F4',
    'crippled_em': u'\U0001F494',
    'confused_em': u'\U0001F915',
    'poisoned_em': '🤢',

    # Оружие
    "hammer_em": u'\U0001F528',
    'boomerang_em':  u'\U000021A9',
    'chain_em': u'\U000026D3',
    'whip_em': u'\U0001F4AB',
    'katana_em': u'\U00003299',
    'mace_em': u'\U0001F4A2',
    'weapon_loss_em': u'\U0001F450',
    'pick_up_em': u'\U0001F64C',
    'arrow_em': u'\U0001F3F9',

    # Предметы
    "drug_em": emoji.emojize(':syringe:', use_aliases=True),
    "knife_em": emoji.emojize(':knife:', use_aliases=True),
    "soundbomb_em": u'\U0001F514',
    "flashbomb_em": emoji.emojize(':astonished:', use_aliases=True),
    "smokebomb_em": emoji.emojize(':see_no_evil:', use_aliases=True),
    'molotov_em': u'\U0001F378',
    'force_shield_em': emoji.emojize(':large_blue_circle:', use_aliases=True),

    # Способности
    "sadist_em": emoji.emojize(':smiley:', use_aliases=True),
    "berserk_em": u'\U0001F620',
    "pyroman_em": u'\U0001F47A',
    "zombie_em": u'\U0001F62C',
    'junkie_em': u'\U0001F643',
    'thief_em': u'\U0001F60F',
    'failthief_em': u'\U0001F612',
    'hypnosis_em': u'\U0001F31A',
    'failhypnosis_em': u'\U0001F31D',
    'thrower_em': u'\U00002604',
    'munchkin_em': u'\U0001F199',
    'doctor_em': u'\U0001F637',
    'houndmaster_em': u'\U0001F436',
    'revenge_em': u'\U00002757',
    'chains_em': '\u26d3',

    # Мобы
    "dog_em": u'\U0001F436',
    "wolf_em": emoji.emojize(':wolf:', use_aliases=True),
    'rat_em': u'\U0001F42D',
    'zombie_em': '\U0001f9df\u200d\u2642\ufe0f',
    'skeleton_em': '💀',
    'worm_em': '\U0001f40d',
    'basilisk_em':'snk',
    'lich_em':'\u26b0',
    'snail_em':'\U0001f95f',
    'spermonster_em':'\U0001f4a6',
    'pedobear_em':'\U0001f43b',
    'bird_em': '\U0001f985',
    'bear_em': '\U0001f43b',
    'goblin_em': '\U0001f47a',

    # Меню_мобов
    "arm_em": u'\U0001F4AA',
    "leg_em": u'\U0001F9B5',
    'bone_em': u'\U00002620',


    # Карта
    'current_map_em': emoji.emojize(':busts_in_silhouette:', use_aliases=True),
    'visited_map_em': ' ',
    'question_em': emoji.emojize(':question:', use_aliases=True),
    'wall_em': '⬛️',
    'kaaba_em': '\U0001f54b',
    'crossroad_em': '\u2795',
    'smith_em': '\u2692',
    'loose_loot_em': '\U0001f46e\U0001f3fe'
    }


def parse(my_string):
    if any('_em' in tup for tup in [tup[1] for tup in string.Formatter().parse(my_string) if tup[1] is not None]):
        return my_string.format(**emote_dict)


