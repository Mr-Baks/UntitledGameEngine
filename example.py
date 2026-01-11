import numpy as np
import random
from typing import List, Tuple
from entity import Entity
from components import Transform, Physics, Collider, Render
from event_system import EventBus, Phase
from game import Game, Input
import time
from game import *


g = Game((80, 25), 5, 60)
npf = np.float32
npa = lambda tpl: np.array(tpl, dtype=npf)
rnd = random.randint
syms = '@#$%&FWBgZ'

for i in range(50):
    g.add_entity(Entity(i).add_components(Transform(npa((0, 0))), Physics(npf(rnd(1, 100)), npa((rnd(-10, 10))), npa((0, 0)), npf(100)), Render(default_sym=random.choice(syms)), Collider(rnd(1, 10), rnd(1, 10))))

g.set_player(g.get_entity(0))

def on_frame(event: FrameEvent):
    game = event.game
    print('AAAA')
    if game.frame_count // game.fps % 2 == 0:
        game.set_player(random.choice(game.entities_list))
    player = game.player
    if player.transform is not None: print(player.transform.pos)
    if player.physics is not None: print(player.physics)

g.event_bus.subscribe(1000, Phase.REACTION, FrameEvent, on_frame)

g.run()