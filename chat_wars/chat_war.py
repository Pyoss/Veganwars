
class GlobalWar:
    def __init__(self):
        self.stage = 'peace'
        self.stage_choices = ['peace', 'siege', 'marauder']
        self.war_actors = {}

    def start_siege(self):
        self.announce_siege()
        self.stage = 'siege'

    def start_attack(self):
        self.announce_attack()
        self.stage = 'attack'

current_war = GlobalWar()

