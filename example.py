from game import Game
from physics import Object
from render import Scene
import numpy as np
from tools import Tools
from ui import *


ui = UI(
    (100, 25),
    Label((0, 10), 30, 3, '!COUNTER!'),
    Button((19, 0), 11, 5, '+1', on_click=plus),
    Button((0, 0), 11, 5, '-1', on_click=minus),
    Label((10, 5), 10, 5, '1500'), 
    ProgressBar((0, -5), 30, 3, 'progress!')
)

c = 1
def on_tick(tick, obj_list, target, tickspeed):
    global c
    radius = 7
    # obj_list[1].pos = Tools.to_float((np.sin(tick / 100) * radius / 0.5, np.cos(tick / 200) * radius))
    if obj_list[-1].check_obj_collision(obj_list[1]):
        obj_list[-1].pos += Tools.to_float((5, 5))
        ui.main_loop()
    if tick % tickspeed * c == 0:
        c += 1
    # print('second', c)
        

scene = Scene((180, 25),
    {
        'pos': (0, 0),
        'hitbox_x': 4,
        'hitbox_y': 1,
        'type': 'mobile',
        'velocity': (0, 0),
        'acceleration': (0, 0),
        'vel_limit': 30,
        'acc_limit': 15,
        'mass': 10,
        "texture":"g",
        "draw_priority": 2,
        "target": True
    },
    {
        'pos': (0, 4),
        'hitbox_x': 4,
        'hitbox_y': 0.5,
        'type': 'mobile',
        'velocity': (0, 0),
        'acceleration': (0, 0),
        'vel_limit': 15,
        'acc_limit': 15,
        'mass': 10,
        "texture":"pen",
        "draw_priority": 1,
    },
    {
        'pos': (9, 4),
        'hitbox_x': 10,
        'hitbox_y': 4,
        'type': 'mobile',
        'velocity': (0, 0),
        'acceleration': (0, 0),
        'vel_limit': 15,
        'acc_limit': 15,
        'mass': 10,
        "texture":"col",
        "draw_priority": 1,
        "has_collision": False
    },
)
game = Game(scene, on_tick)
game.run(600, 15, 100)