from fight import fight_main, ai, units
from locales import localization
from bot_utils import bot_methods, keyboards
import threading
from adventures import dungeon_main, maps, map_engine
import engine


def team_string(team, game, message):
    next_arrow = '┞'
    end_arrow = '┕'
    message.row(localization.LangTuple('utils', 'players').translate(game.lang))
    if len(team) > 0:
        for actor in team[:-1]:
            message.row(next_arrow, actor)
        message.row(end_arrow, team[-1])
    message.row()


class GameDict(dict):
    def __getitem__(self, item):
        return dict.__getitem__(self, int(item))

game_dict = GameDict()
dungeons = {}


# lobby = [team={chat_id:name} or team={ai_class:ai_class.name}]
def test_fight(chat_id, name):
    game = Game(chat_id, 'rus')
    game.lobby = [{chat_id: (name, None)}, {units.Zombie: ('Зомби', None)}]
    game.start()


class Game:
    def __init__(self, chat_id, lang, team_number=2, test=False):
        self.id = chat_id
        game_dict[self.id] = self
        self.langs = ['rus']
        self.lang = lang
        self.lobby = [dict() for _ in range(team_number)]
        self.chat_id = chat_id
        self.string_dict = dict()
        self.fight = None
        self.started = False
        if not test:
            bot_methods.send_message(self.chat_id, localization.LangTuple('utils', 'game_start').translate(self.lang))
            self.lobby_id = self.send_lobby()

    def finish(self):
        del game_dict[self.chat_id]

    def __str__(self):
        return str(self.chat_id)

    def join_lobby(self, chat_id, name):
        pass

    def error(self, error):
        bot_methods.send_message(self.chat_id,
                                 localization.LangTuple('errors', error).
                                 translate(self.lang))

    def ask_start(self):
        if all(team for team in self.lobby):
            self.start()
        else:
            self.error('small_team')

    def start(self):
        self.update_lobby(keyboard=False)
        self.fight = fight_main.Fight(self)
        self.started = True
        self.fight.form_teams(self.lobby)
        x = threading.Thread(target=self.fight.run)
        x.daemon = True
        x.start()

    def change_team(self, chat_id):
        player_team = [team for team in self.lobby if chat_id in team]
        if player_team:
            team_num = self.lobby.index(player_team[0])
            name = self.lobby[team_num].pop(chat_id)
            if team_num != len(self.lobby) - 1:
                new_team_num = team_num + 1
            else:
                new_team_num = 0
            self.lobby[new_team_num][chat_id] = name
            self.update_lobby()
        else:
            self.error('player_not_exists')

    def send_message(self, *args):
        message = localization.PlayerString(self)
        message.row(*args)
        message.construct()
        return bot_methods.send_message(self.chat_id, message.result_dict[self.lang])

    def send_lobby(self):
        return bot_methods.send_message(self.chat_id, self.lobby_message(), reply_markup=keyboards.join_keyboard(self))

    def update_lobby(self, keyboard=True):
        self.clear_empty_teams()
        bot_methods.edit_message(self.chat_id, self.lobby_id.message_id, self.lobby_message()
                                 , reply_markup=keyboards.join_keyboard(self) if keyboard else None)

    def lobby_message(self):
        teams = [[v[0] if isinstance(v[0], str) else localization.LangTuple('unit_'+k[0].unit_name, 'name').translate(self.lang) for k, v in team.items()] for team in self.lobby]
        message = localization.GameString(self)
        next_arrow = '┞'
        end_arrow = '┕'
        i = 0
        for team in teams:
            message.row(localization.LangTuple('fight', 'team',
                                               format_dict={'team_name': i+1}).translate(self.lang))
            if len(team) > 0:
                for actor in team[:-1]:
                    message.row(next_arrow, actor)
                message.row(end_arrow, team[-1])
            message.row()
            i += 1
        message.construct()
        return message.result_dict[self.lang]

    def clear_empty_teams(self):
        pass


class FFAGame(Game):
    def __init__(self, chat_id, lang):
        Game.__init__(self, chat_id, lang, team_number=1)

    def join_lobby(self, chat_id, name):
        if self.started:
            return False
        if not any(chat_id in team for team in self.lobby):
            if not self.lobby[0]:
                self.lobby[0][chat_id] = name
            else:
                self.lobby.append({chat_id: name})
            self.update_lobby()
        else:
            self.error('player_exists')

    def add_ai(self, ai_class):
        if self.started:
            return False
        ai_actor = ai_class(self)
        self.lobby.append({ai_actor:ai_actor.name})
        self.update_lobby()

    def clear_empty_teams(self):
        if len(self.lobby) > 1:
            for team in self.lobby:
                if len(team) == 0:
                    self.lobby.remove(team)

    def change_team(self, chat_id):
        player_team = [team for team in self.lobby if chat_id in team]
        if player_team:
            team_num = self.lobby.index(player_team[0])
            name = self.lobby[team_num].pop(chat_id)
            if team_num != len(self.lobby) - 1:
                new_team_num = team_num + 1
            else:
                if len(self.lobby[team_num]) == 0:
                    new_team_num = 0
                else:
                    self.lobby.append({chat_id: name})
                    self.update_lobby()
                    return False
            self.lobby[new_team_num][chat_id] = name
            self.update_lobby()
        else:
            self.error('player_not_exists')


class VsGame(Game):

    def __init__(self, chat_id, lang, team_number=2):
        Game.__init__(self, chat_id, lang, team_number=team_number)
        # Баловство
        self.mob_dict = {'Pyos': ['zombie', 'zombie'], 'Asgarðr': ['bear', 'bird_rukh']
                        , 'Пасюк Лошадкин': ['spermonster', 'pedobear'], 'Insight': ['shadow', 'snail']}

    def join_lobby(self, chat_id, name):
        if self.started:
            return False
        if not any(chat_id in team for team in self.lobby):
            lobby = min(self.lobby, key=lambda x: len(x))
            lobby[chat_id] = (name, units.Human(name).to_dict())
            print(name)
            if name in self.mob_dict:
                for mob in self.mob_dict[name]:
                    self.add_ai(units.units_dict[mob], lobby)
            self.update_lobby()
        else:
            self.error('player_exists')

    def add_ai(self, ai_class, lobby):
        if self.started:
            return False
        self.update_lobby()
        lobby[(ai_class, engine.rand_id())] = (None, ai_class().to_dict())


class Dungeon(Game):
    def __init__(self, chat_id, lang):
        Game.__init__(self, chat_id, lang, team_number=1)
        self.map = None
        self.party = None
        self.fight = None
        self.complexity = None

    def join_lobby(self, chat_id, name):
        if not self.started:
            if not any(chat_id in team for team in self.lobby):
                self.lobby[0][chat_id] = name
                self.update_lobby()
            else:
                self.error('player_exists')

    def start(self):
        self.started = True
        self.update_lobby(keyboard=False)
        self.complexity = len(self.lobby[0])
        self.create_dungeon_map(map_engine.FirstDungeon(self))
        map_engine.dungeons[self.chat_id] = self
        self.add_party(self.chat_id, player_list=self.lobby[0])
        for member in self.party.members:
            map_engine.dungeons[member.chat_id] = self

        bot_methods.send_message(self.chat_id, localization.LangTuple('utils', 'fight_start')
                                 .translate(self.lang))
        self.map.start()

    def lobby_message(self):
        teams = [[v if isinstance(v, str) else v.translate(self.lang) for k, v in team.items()] for team in self.lobby]
        message = localization.GameString(self)
        team_string(teams[0], self, message)
        message.construct()
        return message.result_dict[self.lang]

    def run_fight(self, *args):
        # В качестве аргумента должны быть переданы словари команд в виде
        # [team={chat_id:(name, unit_dict)} or team={ai_class:(ai_class.name, unit_dict)}].
        fight = fight_main.Fight()
        self.fight = fight
        self.fight.form_teams(args)
        results = fight.run()
        return results

    def end_dungeon(self):
        del game_dict[self.id]

    def create_dungeon_map(self, map_type):
        self.map = map_type.create_map()

    def add_party(self, chat_id, player_list):
        self.party = dungeon_main.Party(player_list, chat_id)
        dungeons[chat_id] = self
        for member in self.party.members:
            dungeons[member.chat_id] = self

    # Возвращает текущюю локацию группы
    def current_location(self):
        return self.party.current_location

    # Возвращает клавиатуру с картой
    def generate_map_keyboard(self):
        buttons = [room.return_button() for room in self.party.current_location.get_visible()]
        return dungeon_main.form_keyboard(*buttons, row_width=3)

    def send_movement_map(self):
        keyboard = self.generate_map_keyboard()
        for member in self.party.members:
            member.message_id = bot_methods.send_message(member.chat_id, member.member_string(), reply_markup=keyboard).message_id

    def update_map(self, new=False):
        text = self.party.leader.member_string()
        if self.party.leader.message_id is None:
            self.send_movement_map()
        else:
            for member in self.party.members:
                member.update_map(new=new)

    def delete_map(self):
        if self.party.leader.message_id is not None:
            for member in self.party.members:
                bot_methods.delete_message(message_id=member.message_id, chat_id=member.chat_id)
                member.message_id = None
