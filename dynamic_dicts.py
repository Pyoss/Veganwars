
class DynamicDict(dict):
    def __init__(self, name):
        dict.__init__(self)
        self.name = name

dungeons = DynamicDict('dungeons')


fight_dict = DynamicDict('fight_dict')
unit_talk = DynamicDict('unit_talk')


lobby_list = DynamicDict('lobby_list')
occupied_list = []

dicts = [dungeons, fight_dict, unit_talk, lobby_list]


def print_dicts():
    for dic in dicts:
        print(dic.name + ': ' + str(dic))
