from entity import Entity
from components import *
from render_systems import SceneRenderSystem
from physic_system import CollisionSystem, PhysicsSystem
from pynput import keyboard as kb
import time
from typing import Optional, Callable
import threading

class Input:
    """Handles keyboard input with binding, press detection, and callback support.
    
    This class manages keyboard input using pynput, allowing for key binding
    with press/release callbacks, hold functionality, and real-time key state tracking.
    """
    
    def __init__(self):
        """Initializes the Input handler with empty key bindings."""
        self.keys = {}
        self.keys_pressed = {}
        self.listener = None
        self.setup_input()
        self.lock = threading.Lock()
        
    def bind_key(self, key: str, on_press: Optional[Callable] = None, 
                 on_release: Optional[Callable] = None, 
                 hold_interval: Optional[float] = None):
        """Binds a function to key press/release events.
        
        Args:
            key: String identifier for the key (e.g., 'a', 'space', 'enter').
            on_press: Callback function executed when key is pressed.
                     Defaults to None.
            on_release: Callback function executed when key is released.
                       Defaults to None.
            hold_interval: Time interval (seconds) for repeated calls while key is held.
                          If None, no hold repetition occurs. Defaults to None.
        
        Returns:
            self: Allows for method chaining.
        """
        with self.lock:
            self.keys[key] = {
                'is_pressed': False,
                'on_press': on_press,
                'on_release': on_release,
                'hold_interval': hold_interval,
                'last_hold_time': 0
            }
            self.keys_pressed[key] = False
            
        return self
    
    def unbind_key(self, key: str):
        """Removes all bindings for a specific key"""
        with self.lock:
            if key in self.keys:
                del self.keys[key]
            if key in self.keys_pressed:
                del self.keys_pressed[key]
    
    def setup_input(self):
        """Initializes and starts the keyboard listener in a daemon thread."""
        self.listener = kb.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.daemon = True 
        self.listener.start()
    
    def on_press(self, key):
        """Handles key press events from the keyboard listener"""
        try:
            key_str = self._get_key_string(key)
            
            if key_str and key_str in self.keys:
                with self.lock:
                    if not self.keys[key_str]['is_pressed']:
                        self.keys[key_str]['is_pressed'] = True
                        self.keys_pressed[key_str] = True
                        
                        callback = self.keys[key_str]['on_press']
                        if callback:
                            callback()
                            
        except Exception as e:
            print(f"Error in on_press: {e}")
    
    def on_release(self, key):
        """Handles key release events from the keyboard listener"""
        try:
            key_str = self._get_key_string(key)
            
            if key_str and key_str in self.keys:
                with self.lock:
                    if self.keys[key_str]['is_pressed']:
                        self.keys[key_str]['is_pressed'] = False
                        self.keys_pressed[key_str] = False
                        
                        callback = self.keys[key_str]['on_release']
                        if callback:
                            callback()
                            
        except Exception as e:
            print(f"Error in on_release: {e}")
    
    def _get_key_string(self, key):
        """Converts pynput key object to a standardized string representation"""
        try:
            if hasattr(key, 'char') and key.char:
                return key.char
            elif hasattr(key, 'name'):
                special_keys = {
                    'space': ' ',
                    'enter': '\n',
                    'tab': '\t'
                }
                return special_keys.get(key.name, key.name)
            elif hasattr(key, 'vk'):
                return f'vk_{key.vk}'
        except:
            return None
        
        return str(key).replace("'", "")
    
    def is_pressed(self, key: str) -> bool:
        """Checks if a specific key is currently pressed"""
        return self.keys_pressed.get(key, False)
    
    def get_pressed_keys(self):
        """Returns a list of all currently pressed keys"""
        with self.lock:
            return [key for key, pressed in self.keys_pressed.items() if pressed]
    
    def clear_bindings(self):
        """Removes all key bindings and resets the input state"""
        with self.lock:
            self.keys.clear()
            self.keys_pressed.clear()
    
    def stop(self):
        """Stops the keyboard listener"""
        if self.listener:
            self.listener.stop()
    
    def __del__(self):
        """Destructor that ensures the keyboard listener is stopped"""
        self.stop()
    
class Game:
    """Main game engine class that manages the game loop, entities, and systems.
    
    This class orchestrates the entire game simulation, including physics,
    collision detection, rendering, and input handling.
    
    Attributes:
        resolution: Screen resolution as (width, height) tuple.
        fps: Target frames per second for rendering.
        tickspeed: Target ticks per second for physics simulation.
        tick: Current tick count.
        frame_count: Current frame count.
        elasticity: Bounciness coefficient for collision resolution.
        entities_list: List of all active entities in the game.
        on_frame: Optional callback executed each frame.
        on_tick: Optional callback executed each tick.
        input: Input handler instance.
        physics_system: Physics simulation system.
        collision_system: Collision detection and resolution system.
        render_system: Rendering system.
        player: The currently controlled player entity.
        is_running: Flag indicating if the game loop is active.
    """
    
    def __init__(self, resolution: tuple[int], fps: int, tickspeed: int, elasticity: float = 0.8, on_tick: Optional[Callable] = None, on_frame: Optional[Callable] = None):
        self.resolution = resolution
        self.fps = fps
        self.tickspeed = tickspeed
        self.tick = 0
        self.frame_count = 0
        self.elasticity = elasticity
        self.entities_list = []
        self.on_frame = on_frame
        self.on_tick = on_tick

        self.input = Input()
        self.physics_system = PhysicsSystem()
        self.collision_system = CollisionSystem(cell_size=(3, 3))
        self.render_system = SceneRenderSystem(resolution)

    def add_entity(self, entity: Entity):
        """Adds an entity to the game world"""
        self.entities_list.append(entity)
        if entity.script is not None: entity.script.on_init(self)
        return self
    
    def get_entity(self, id: int) -> Optional[Entity]:
        """Retrieves an entity by ID"""
        for e in self.entities_list:
            if e.id == id: return e
        return None
    
    def set_player(self, entity: Entity):
        """Sets an entity as the player-controlled character"""
        if entity.transform is None: 
            return
        self.render_system.set_target(entity)
        self.player = entity

    def remove_entity(self, id: int):
        """Removes an entity from game world by ID"""
        for e in self.entities_list:
            if e.script is not None: e.script.on_remove(self)
            if e.id == id: self.entities_list.remove(e)

    def run(self):
        """Starts the main game loop.
        
        The loop follows a fixed timestep pattern for physics simulation
        with variable rendering frames. It continuously updates physics,
        processes collisions, and renders frames until the game is stopped.
        """
        last_time = time.time()
        tick_accumulator = 0
        fixed_delta_time = 1 / self.tickspeed
        self.is_running = True
    
        while self.is_running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time
            tick_accumulator += delta_time
        
            if self.on_tick is not None: 
                self.on_tick(self)
        
            while tick_accumulator >= fixed_delta_time:
                self.tick += 1
            
                self.collision_system.collision_grid.set_cells_table(self.entities_list)
                self.physics_system.update(self.entities_list, fixed_delta_time, self.collision_system)
                self.collision_system.process_collision(self.entities_list)

                for e in self.entities_list:
                    if e.script is not None: e.script.on_tick(self)
            
                tick_accumulator -= fixed_delta_time
        
            tick_accumulator = min(0.2, tick_accumulator)

            self.frame_count += 1
            if self.on_frame is not None: 
                self.on_frame(self)
            for e in self.entities_list:
                if e.script is not None: e.script.on_frame(self)
            self.render_system.print_screen(self.entities_list)
        
            self._limit_fps(current_time)

    def _limit_fps(self, current_time):
        """Accurately limits the frame rate to the target FPS"""
        target_frame_time = 1.0 / self.fps
        elapsed = time.time() - current_time
    
        if elapsed < target_frame_time:
            sleep_time = target_frame_time - elapsed
            if sleep_time > 0.001:
                time.sleep(sleep_time * 0.9)
            while time.time() - current_time < target_frame_time:
                pass