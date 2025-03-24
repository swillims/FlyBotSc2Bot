from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer, Human

from flyBot import flyBot

import random

# names from my maps folder
""" names for quick copy paste
"Equilibrium512AIE"
"Goldenaura512AIE"
"Gresvan512AIE"
"HardLead512AIE"
"Oceanborn512AIE"
"SiteDelta512AIE"
"""

#myMaps = ["Equilibrium512AIE","Goldenaura512AIE","Gresvan512AIE","HardLead512AIE","Oceanborn512AIE","SiteDelta512AIE"]
#myMap = random.choice(myMaps)

myMap = "Equilibrium512AIE"

factions = [Race.Terran,Race.Zerg,Race.Protoss,Race.Random]

enemyFaction = random.choice(factions)

b = Bot(Race.Protoss, flyBot())
c = Computer(enemyFaction, Difficulty.VeryHard)

run_game(
    maps.get(myMap),
    [b,c],
    realtime=False
)
"""
run_game(
    maps.get(myMap),
    [Human(enemyFaction),b],
    realtime=True
)
"""