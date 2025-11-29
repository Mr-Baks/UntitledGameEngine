from render import Scene
from physics import Object, Static_object
from pynput import keyboard as kb
import numpy as np
import time
from tools import Tools

class Game:
    def __init__(self, scene, on_tick):
        self.scene = scene
        self.player = self.scene.target
        self.on_tick = on_tick
        
        self.listener = kb.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        
        self.keys_pressed = {'w': False, 'a': False, 's': False, 'd': False}

        self.player_vel = np.float32(30)
        
    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char in self.keys_pressed.keys():
                self.keys_pressed[key.char] = True
                self.update_player_movement()
        except AttributeError:
            pass
    
    def on_release(self, key):
        try:
            if hasattr(key, 'char') and key.char in self.keys_pressed.keys():
                self.keys_pressed[key.char] = False
                self.update_player_movement()
        except AttributeError:
            pass
    
    def update_player_movement(self):
        self.player.velocity = np.array([0, 0], dtype=np.float32)
    
        if self.keys_pressed['w']:
                self.player.velocity += np.array([0, self.player_vel], dtype=np.float32)
        if self.keys_pressed['s']:
            self.player.velocity += np.array([0, -self.player_vel], dtype=np.float32)
        if self.keys_pressed['a']:
            self.player.velocity += np.array([-self.player_vel, 0], dtype=np.float32)
        if self.keys_pressed['d']:
            self.player.velocity += np.array([self.player_vel, 0], dtype=np.float32)

    def add_obj(self, obj_params):
        list(self.scene.objects).append(obj_params)
        self.scene.__init__(self.scene.resolution, *self.scene.objects)
    
    def run(self, t: float, fps: float, tickspeed: float):
        for tick in range(int(tickspeed * t)):
            for obj in self.scene.obj_list:
                if isinstance(obj, Object):
                    obj.upd_params(1 / tickspeed, (0, 0))

            for i, obj in enumerate(self.scene.obj_list):
                collided_objects = obj.check_collision(self.scene.obj_list)
                for col_obj in collided_objects:
                    if isinstance(obj, Object): 
                        obj.resolve_collision(col_obj, elasticity=0.8)
            self.on_tick(tick, self.scene.obj_list, self.scene.target, tickspeed)

            if tick % max(1, int(tickspeed / fps)) == 0:
                print(f"Tick: {tick}, target obj pos: {self.scene.target.pos}, velocity: {self.scene.target.velocity}")
                self.scene.print_scene()
                time.sleep(1 / fps)