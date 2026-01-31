import time
from game import *
from components import *
from entity import *
import numpy as np
from numpy import array as npa
from random import randint as ri

class StatsScript:
    def __init__(self):
        self.last_print = time.time()
        self.frames = 0
        self.ticks = 0
        self.last_time = time.time()

    def on_tick(self, entity, game):
        self.ticks += 1

    def on_frame(self, entity, game):
        self.frames += 1
        now = time.time()

        if now - self.last_print >= 0.5:
            dt = now - self.last_time
            fps = self.frames / dt
            tps = self.ticks / dt

            print(
                f"[STATS] "
                f"FPS: {fps:6.1f} | "
                f"TPS: {tps:6.1f} | "
                f"Entities: {len(game.world.entities)}"
            )

            self.frames = 0
            self.ticks = 0
            self.last_time = now
            self.last_print = now 

def spawn_test_entities(game):
    for i in range(1000):
        t = Transform(pos=npa((i % 100, i // 100), dtype=np.float32))
        p = Physics(
            velocity=npa((ri(1, 10), ri(1, 10)), dtype=np.float32),
            mass=np.float32(ri(1, 200)),
            acceleration=npa((0.0, 0.0), dtype=np.float32),
            velocity_limit=np.float32(200)
        )
        c = Collider(hitbox_x=ri(3, 10), hitbox_y=ri(3, 10))
        s = Script()
        r = Render()

        e = Entity(i).add_components(t, p, c, s, r)
        game.world.add_entity(e)

def create_stats_entity(game):
    stats = StatsScript()
    s = Script()
    s.on_tick.append(stats.on_tick)
    s.on_frame.append(stats.on_frame)

    e = Entity(-1).add_components(Transform(pos=npa((0, 0))), s)
    game.set_player(e)
    game.world.add_entity(e)
game = Game(resolution=(120, 40), fps=20, tickspeed=25)

spawn_test_entities(game)
create_stats_entity(game)

game.run()
