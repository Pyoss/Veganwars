
# Выбор способностей в начале раунда.
def choose_abilities(self, ability_number=5, max_abilities=2, players=None):
    players = self.players() if players is None else players
    for actor in players:
        actor.statuses['ability_choice'] = [max_abilities, ability_number]
        actor.send_ability_choice(ability_number)
    time_elapsed = 0
    while not all(player.done for player in players) and time_elapsed < config.build_time:
        time.sleep(2)
        time_elapsed += 2
    for player in players:
        player.active = False
        player.done = True
        if 'ability_choice' in player.statuses:
            while player.statuses['ability_choice'][0]:
                random_ability = random.choice([value for key, value in abilities.ability_dict.items()])(player)
                if random_ability.suit():
                    player.statuses['ability_choice'][0] -= 1
                    player.abilities.append(random_ability)
            del player.statuses['ability_choice']

def choose_weapon(self, weapon_number=3, cancelable=False, players=None):
    players = self.players() if players is None else players
    for player in players:
        player.len_weapons = len(player.weapons)
        player.send_weapon_choice(player, weapon_number, cancelable=cancelable)
    time_elapsed = 0
    while not all(player.done for player in players) and time_elapsed < config.build_time:
        time.sleep(2)
        time_elapsed += 2
    for player in players:
        player.active = False
        if not player.done and not cancelable:
            random_weapon = random.choice([value for key, value in weapons.weapon_dict.items()])(player)
            player.get_weapon(random_weapon)
            player.done = True
        if cancelable and len(player.weapons) > player.len_weapons:
            player.weapons = player.weapons[1:]
            del player.len_weapons


назначение оружия и способностей как часть боя - рак и должен быть исправлен

надо исправить саму архитектуру подземелий, потому что сейчас там черт ногу сломит



пример:
хранится размер сетки
хранится словарь координат с типами клеток
тип клетки включает в себя название(мобы, сокровище, босс), тип(скелеты, шаман и прочее) и то, была ли клетка посещена

(0,1):'mob_skeleton_cleared'
(3,4):'treasure_0_locked'

необходимо составить скрипты пополнения инветаря, увеличения опыта и лвлапа хотя бы в масштабах подземелья
необходимо составить специальный параметр для группы (locked), который будет запрещать передвижения
при условии, что кто-то еще не поменял экипировку или не повысил уровень
повышение уровня будет автоматически ставить locked
также статус будет ставится при открытии инвентаря кем-то в группе
party.locked() будет проверять каждого игрока на Locked, и возвращать true, если все игроки ничем не заняты
проверка на наличие новых уровней должна выполняться при обновлении карты
все данные должны храниться в новой динамичной базе данных

