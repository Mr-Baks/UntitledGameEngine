[![Русский](https://img.shields.io/badge/lang-ru-blue.svg)](README.md)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README_en.md)

# UntitledGameEngine

A flexible 2D game engine for terminal/console environments, built on **Entity-Component-System (ECS)** architecture.
Features spatial hashing for collisions, scene management, UI toolkit, event bus, and full ANSI color rendering.

---

## ✨ Features

- **ECS Core** – Entities are just IDs; logic in systems; data in components.
- **Spatial Hash Grid** – Fast broad-phase collision detection.
- **Scene & SceneGroup** – Isolated worlds, stacking (menus, overlays), lifecycle hooks.
- **UI System** – Screens, buttons, text labels, progress bars with focus handling.
- **Event Bus** – Phase-based event dispatching (Input, Simulation, Reaction, Render).
- **Input Handling** – Cross-platform (Windows/Linux X11) key bindings and polling.
- **Render System** – Textures (from JSON), zooming, camera following, depth sorting.
- **Physics** – Velocity, acceleration, mass, impulses, static bodies.
- **Query Manager** – Cached entity queries, transformers (sorting, filtering).
- **No external rendering libraries** – Pure ANSI escape codes and console output.

---

## 📦 Installation

```bash
pip install numpy keyboard
```

Place the engine files in your project directory.
The engine expects a `textures.json` file (optional) for named textures.

**Note**: On Linux Wayland, the `keyboard` library may require `sudo`. For testing, use `python -m keyboard`.

---

## 🚀 Quick Start

```python
import numpy as np
from game import Game
from entity import Entity
from components import Transform, Physics, Collider, Render, Camera, Script
from render_systems import Scene, SceneGroup
from colors import Colors

# Initialize engine
game = Game(
    resolution=(100, 25),
    fps=60,
    tickspeed=120,
    bucket_step=0.25,
    background_sym=' ',
    textures_path='textures.json'
)

# Input bindings
def jump_action():
    phys = player.physics
    if abs(phys.velocity[1]) < 2.0:
        phys.velocity[1] = -65.0

game.input.bind_key('space', on_press=jump_action)
game.input.bind_key('a')
game.input.bind_key('d')
game.input.bind_key('left')
game.input.bind_key('right')

# Create player entity
player = Entity('player')
player.add_components(
    Transform(pos=np.array([12.0, 20.0], dtype=np.float32)),
    Physics(
        mass=1.0,
        velocity=np.zeros(2, dtype=np.float32),
        acceleration=np.array([0.0, 80.0], dtype=np.float32),
        velocity_limit=65.0
    ),
    Collider(half_x=0.75, half_y=1.1, elasticity=0),
    Render(name='player', draw_priority=100, default_color=Colors.CYAN),
    Camera(offset=np.array([0.0, -2.0], dtype=np.float32), zoom=1.0),
    Script()
)

# Player controller script
def player_tick(e: Entity, g: Game):
    phys = e.physics
    inp = g.input
    on_ground = abs(phys.velocity[1]) < 32.0

    max_speed = 30.0
    ground_accel = 200.0
    air_accel = 20.0
    ground_friction = 1250.0
    air_friction = 280.0

    target_vel_x = 0.0
    if inp.is_pressed('a') or inp.is_pressed('left'):
        target_vel_x = -max_speed
    elif inp.is_pressed('d') or inp.is_pressed('right'):
        target_vel_x = max_speed

    accel = ground_accel if on_ground else air_accel
    friction = ground_friction if on_ground else air_friction

    if target_vel_x != 0:
        if abs(phys.velocity[0]) < abs(target_vel_x):
            phys.velocity[0] += np.sign(target_vel_x) * accel * (1 / 120.0)
        if abs(phys.velocity[0]) > max_speed:
            phys.velocity[0] = np.sign(phys.velocity[0]) * max_speed
    else:
        if abs(phys.velocity[0]) > 8.0:
            phys.velocity[0] -= np.sign(phys.velocity[0]) * friction * (1 / 120.0)
        else:
            phys.velocity[0] = 0.0

player.script.add_tick(player_tick)

# Scene setup
demo_group = SceneGroup('demo_platformer')
level = Scene('level1', priority=0)
demo_group.add(level)
game.scene_manager.register(demo_group)
game.scene_manager.load('demo_platformer', game)

level.add(player)
game.set_player(player)

game.run()
```

---

## 🧱 Core Architecture

### Entity

```python
entity = Entity(name="optional")
entity.add_component(Transform(pos=np.array([0,0], dtype=np.float32)))
entity.add_components(Physics(), Collider(), Render())
```

Entities hold components. Access via properties: `entity.transform`, `entity.physics`, `entity.collider`, `entity.render`, `entity.camera`, `entity.script`.

### Components (built-in)

| Component | Fields |
|-----------|--------|
| `Transform` | `pos: np.ndarray[float32, (2,)]`, `dirty: bool` |
| `Physics` | `mass: float32`, `velocity: np.ndarray`, `acceleration: np.ndarray`, `velocity_limit: float32`, `is_static: bool` |
| `Collider` | `half_x: float`, `half_y: float`, `has_collision: bool`, `elasticity: float` |
| `Render` | `is_visible: bool`, `draw_priority: int`, `name: str \| None`, `default_sym: str`, `default_color: str`, `transparent_sym: str`, `screen_x: int`, `screen_y: int` |
| `Camera` | `offset: np.ndarray`, `zoom: float`, `active: bool` |
| `Script` | `on_tick: list[callable]`, `on_frame: list[callable]` – use `add_tick(cb)` / `add_frame(cb)` |

### World & QueryManager

- `World` stores entities, component index, and collision grid.
- `QueryManager` caches results of `get_global(*component_types)` and `get_scene(scene_name, *component_types)`.
- Use `game.query_manager.get_global(Transform, Render)` to fetch all visible entities.
- Transformers: `query_manager.register_transformer(frozenset([Transform, Render]), sort_fn)` – then `get_transformed(Transform, Render)` returns transformed (e.g., sorted) list.

### Scenes & SceneManager

- `Scene(name, priority, cell_size)` – isolated world with `on_load`, `on_unload`, `on_pause`, `on_resume` callbacks.
- `SceneGroup(name, priority)` – ordered collection of scenes (e.g., UI layer + game layer).
- `SceneManager` handles stacking: `load(name, game)`, `push(name, game)`, `pop(game)`.
- Active worlds are merged automatically for rendering and queries.

### Systems

Systems run in four **phases**:

```python
class Phase(IntEnum):
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3
```

Built-in systems (registered automatically by `Game`):

- `PhysicsSystem` – updates velocities/positions (Phase.SIMULATION, priority=1000).
- `CollisionSystem` – resolves collisions, emits `CollisionEvent` (Phase.REACTION, priority=1000).
- `EntitiesRenderSystem` – draws entities with camera and textures (Phase.RENDER, priority=1000).
- `UISystem` – renders UI screens, handles focus (Phase.RENDER, priority=1000).

### Event Bus

```python
event_bus = game.event_bus
event_bus.subscribe(entity.id, Phase.REACTION, CollisionEvent, on_collision)
event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))
```

Events are queued per phase and dispatched in priority order (highest first), then by timestamp.

### Input

```python
game.input.bind_key('space', on_press=lambda: print("jump"))
game.input.bind_key('a', on_press=move_left, on_release=stop_left)

if game.input.is_pressed('left'): ...
```

`bind_key` returns `self` for chaining. Keys are normalized (`' '` → `'space'`, `'arrow left'` → `'left'`).

### UI Toolkit

```python
from ui_system import UIScreen, UIText, UIButton, UIProgressBar, Align

screen = UIScreen('main', game.compositor.w, game.compositor.h)

btn = UIButton('ok', x=10, y=10, w=12, h=3, text="OK",
               on_action=lambda g: print("clicked"),
               on_focus=lambda g: print("focused"))
screen.add_child(btn)

label = UIText('pos', x=5, y=5, w=30, h=3, text="X: 0 Y: 0", align=Align.LEFT)
screen.add_child(label)

bar = UIProgressBar('hp', x=5, y=10, w=20, h=1, value=0.5)
screen.add_child(bar)

game.ui_system.register_screen(screen)
```

- Focus navigation: `Tab` / `Shift+Tab`, `Enter` / `Space` to activate.
- `UISystem` automatically collects focusable elements.

### Textures

Load from `textures.json`:

```json
{
  "player": [" @ ", "###"],
  "enemy":  ["^v^"]
}
```

Texture manager supports automatic zoom caching (bucketed by `bucket_step`) and default texture generation from collider size + `Render.default_sym`.

---

## 🎮 Example

See `example.py` – a platformer demo with:
- Player with physics, collision, and keyboard control.
- Static platforms.
- Camera following player.
- Scene setup with `SceneManager`.

---

## 🛠️ Advanced Usage

### Custom System

```python
from system_manager import System, Phase
from components import Component

class MyComponent(Component):
    value: float = 0.0

class MySystem(System):
    def __init__(self):
        super().__init__(Phase.SIMULATION, 500, frozenset([MyComponent]))

    def update(self, dt):
        entities = self._query_manager.get_global(MyComponent)
        for e in entities:
            e.mycomponent.value += dt
```

Register: `game.system_manager.register(MySystem(), Phase.SIMULATION)`

### Transformer (cached sorting/filtering)

```python
def sort_by_priority(entities):
    return sorted(entities, key=lambda e: e.render.draw_priority)

game.query_manager.register_transformer(frozenset([Transform, Render]), sort_by_priority)
# Now get_transformed(Transform, Render) returns sorted list
```

### Custom Event

```python
from event_system import Event, EventBus, Phase

class ScoreEvent(Event):
    def __init__(self, points):
        super().__init__(priority=10)
        self.points = points

event_bus = game.event_bus
event_bus.subscribe(0, Phase.REACTION, ScoreEvent, lambda e: print(f"+{e.points}"))
event_bus.emit(Phase.REACTION, ScoreEvent(100))
```

---

## ⚙️ Configuration

`Game(resolution, fps, tickspeed, bucket_step, background_sym, textures_path, presenter)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `resolution` | `(190, 60)` | Width, height in characters |
| `fps` | `30` | Target render frames per second |
| `tickspeed` | `120` | Physics updates per second |
| `bucket_step` | `0.25` | Zoom cache granularity (1/step) |
| `background_sym` | `' '` | Character for empty areas |
| `textures_path` | `'textures.json'` | JSON file with named textures |
| `presenter` | `ConsolePresenter()` | Output handler (e.g., to file) |

---

## 📝 Notes

- All positions/velocities are `numpy.float32` arrays of length 2.
- Set `entity.transform.dirty = True` after manually moving an entity to update the collision grid.
- `UISystem` automatically registers focusable elements; call `ui_system.set_focus(element)` to set focus programmatically.
- For Wayland on Linux, `keyboard` library may need `sudo` – test with `python -m keyboard`.
- `keyboard` hook runs in a separate thread; `Input.stop()` or `game.input.stop()` cleans up on exit.

---

## 📄 License

This engine is provided under the MIT License.
Feel free to use, modify, and distribute.