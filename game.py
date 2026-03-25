from entity import Entity
from components import *
from render_systems import *
from physics_system import *
from event_system import *
from query_manager import QueryManager
from system_manager import SystemManager
import keyboard
import time
from typing import Optional, Callable


class Input:
    """Cross-platform input system for the game engine (Windows + Linux Xorg/Wayland)"""
    def __init__(self):
        self.pressed: set[str] = set()
        """Currently pressed keys (normalized names: 'a', 'space', 'left', etc.)."""

        self.bindings: Dict[str, Dict[str, Callable]] = {}
        """Mapping: normalized_key → {'on_press': func, 'on_release': func, ...}"""

        self.running = True

        keyboard.hook(self._on_keyboard_event)

    def _normalize_key(self, key: str) -> str:
        """Internal: convert user-friendly key names to canonical form."""
        if not isinstance(key, str):
            return str(key).lower().strip()
        k = key.lower().strip()
        return 'space' if k in (' ', 'space') else k

    def _normalize_event_name(self, name: str) -> str:
        """Internal: normalize name received from keyboard library."""
        if not name:
            return ''
        n = str(name).lower().strip()
        if 'arrow' in n:
            n = n.replace(' arrow', '')
        return n

    def _on_keyboard_event(self, event: keyboard.KeyboardEvent):
        internal_key = self._normalize_event_name(event.name)
        if not internal_key:
            return

        if event.event_type == 'down':
            if internal_key not in self.pressed:
                self.pressed.add(internal_key)
                binding = self.bindings.get(internal_key)
                if binding and binding.get('on_press'):
                    binding['on_press']()

        elif event.event_type == 'up':
            self.pressed.discard(internal_key)
            binding = self.bindings.get(internal_key)
            if binding and binding.get('on_release'):
                binding['on_release']()

    def bind_key(self,
                 key: str,
                 on_press: Optional[Callable[[], None]] = None,
                 on_release: Optional[Callable[[], None]] = None,
                 hold_interval: Optional[float] = None) -> 'Input':
        """Bind callbacks to a key press/release.
        Args:
            key: Any user-friendly name: 'a', 'd', ' ', 'left', 'space', 'esc', etc.
            on_press: Called immediately when key goes down (once per press).
            on_release: Called when key goes up.
            hold_interval: Reserved for future "hold" actions (e.g. auto-fire).
        Returns:
            self (fluent interface)"""
        internal_key = self._normalize_key(key)
        self.bindings[internal_key] = {
            'on_press': on_press,
            'on_release': on_release,
            'hold_interval': hold_interval,
        }
        return self

    def is_pressed(self, key: str) -> bool:
        """Check if a key is currently held down (polling style)."""
        internal_key = self._normalize_key(key)
        return internal_key in self.pressed

    def get_pressed_keys(self) -> list[str]:
        """Return list of all currently pressed keys (for debug or advanced input)."""
        return list(self.pressed)

    def clear_bindings(self) -> None:
        """Remove all key bindings. Useful for scene transitions or menus."""
        self.bindings.clear()

    def stop(self) -> None:
        """Gracefully stop the input listener."""
        keyboard.unhook(self._on_keyboard_event)
        self.running = False

    def __del__(self):
        """Ensure cleanup even if someone forgets to call stop()."""
        self.stop()

class Game:
    """Main class of the console-based 2D game engine built on ECS architecture. Initialize core engine subsystems.
        Args:
            resolution: Screen dimensions in characters (width, height).
            fps: Target frame rate for rendering (frames per second).
            tickspeed: Target update rate for physics simulation (ticks per second).
            elasticity: Default coefficient of restitution for collisions (bounciness).
            bucket_step: Controls granularity of zoom texture caching.
            background_sym: Character used to fill empty space on screen.
            textures_path: Path to JSON file containing named texture definitions.
        """
    
    def __init__(self, resolution: tuple[int], fps: int, tickspeed: int, elasticity: float = 0.8, bucket_step: float = 0.25, background_sym: str = ' ', textures_path: str = 'textures.json'):
        self.resolution = resolution
        self.fps = fps
        self.tickspeed = tickspeed
        self.tick = 0
        self.frame = 0

        self.event_bus = EventBus()
        self.input = Input()
        self.scene_manager = SceneManager()
        self.query_manager = QueryManager(self.scene_manager)
        self.scene_manager.query_manager = self.query_manager
        self.system_manager = SystemManager(self.query_manager)

        self.collision_system = CollisionSystem(self.event_bus)
        self.render_system = RenderSystem(resolution, self.scene_manager, bucket_step=bucket_step, background_sym=background_sym, textures_path=textures_path)
        self.physics_system = PhysicsSystem()

        self.system_manager.register(self.physics_system, Phase.SIMULATION)
        self.system_manager.register(self.collision_system, Phase.REACTION)
        self.system_manager.register(self.render_system, Phase.RENDER)

    def set_player(self, entity: Entity):
        """Set given entity as the player-controlled character.
        Attaches main camera to this entity."""
        if entity.transform is None or entity.camera is None: return

        self.render_system.set_camera(entity)
        self.player = entity

    def run(self):
        """Start main game loop.
        Runs fixed-timestep physics simulation and variable-rate rendering
        until the loop is manually stopped."""
        last_time = time.time()
        accumulator = 0.0
        fixed_dt = 1.0 / self.tickspeed
        self.is_running = True

        event_bus = self.event_bus
        scene_manager = self.scene_manager

        physics = self.physics_system
        collision = self.collision_system
        render = self.render_system
        input_sys = self.input


        while self.is_running:
            now = time.time()
            dt = now - last_time
            last_time = now
            accumulator += dt

            event_bus.dispatch(Phase.INPUT)

            while accumulator >= fixed_dt:
                self.tick += 1
                self.system_manager.update_phase(Phase.SIMULATION, dt)
                self.system_manager.update_phase(Phase.REACTION, dt)
                accumulator -= fixed_dt

                for e in self.query_manager.get_global(Script):
                    for cb in e.script.on_tick:
                        cb(e, self)

            for e in self.query_manager.get_global(Script):
                for cb in e.script.on_frame:
                    cb(e, self)
            
            self.frame += 1

            self.system_manager.update_phase(Phase.RENDER, dt)

            self._limit_fps(now)

            for phase in Phase:
                event_bus.dispatch(phase)

    def _limit_fps(self, current_time):
        """Sleep if necessary to maintain target frame rate."""
        target_frame_time = 1.0 / (1 + self.fps)
        elapsed = time.time() - current_time
    
        if elapsed < target_frame_time:
            sleep_time = target_frame_time - elapsed
            if sleep_time > 0.001:
                time.sleep(sleep_time)

