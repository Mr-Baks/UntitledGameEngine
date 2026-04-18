[![Русский](https://img.shields.io/badge/lang-ru-blue.svg)](README.md)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README_en.md)
# UntitledGameEngine

A flexible 2D game engine for terminal/console environments, built on **Entity-Component-System (ECS)** architecture.  
It features spatial hashing for collisions, scene management, UI toolkit, event bus, and full ANSI color rendering.

---

## ✨ Features

- **ECS Core** – Entities are just IDs; logic is in systems; data in components.
- **Spatial Hash Grid** – Fast broad-phase collision detection.
- **Scene & SceneGroup** – Isolated worlds, stacking (menus, overlays), lifecycle hooks.
- **UI System** – Screens, buttons, text labels, progress bars with focus handling.
- **Event Bus** – Phase‑based event dispatching (Input, Simulation, Reaction, Render).
- **Input Handling** – Cross‑platform (Windows/Linux) key bindings and polling.
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

---

## 🚀 Quick Start

```python
from game import Game
from entity import Entity
from components import *
import numpy as np

# Initialize engine
game = Game(resolution=(120, 40), fps=30, tickspeed=60)

# Create player entity
player = Entity().add_components(
    Transform(pos=np.array([0.0, 0.0], dtype=np.float32)),
    Physics(mass=1.0, velocity=np.zeros(2), acceleration=np.zeros(2)),
    Collider(half_x=0.5, half_y=0.5),
    Render(default_sym='@', name='player'),
    Camera(offset=np.zeros(2), zoom=1.0)
)

# Simple controller script
def move(entity, game):
    acc = np.zeros(2)
    if game.input.is_pressed('w'): acc[1] -= 10
    if game.input.is_pressed('s'): acc[1] += 10
    if game.input.is_pressed('a'): acc[0] -= 10
    if game.input.is_pressed('d'): acc[0] += 10
    entity.physics.acceleration = acc

player.add_component(Script().add_tick(move))

# Set up scene
from render_systems import Scene, SceneGroup
scene = Scene("main")
scene.add(player)
group = SceneGroup("game")
group.add(scene)
game.scene_manager.register(group)
game.scene_manager.load("game")
game.set_player(player)

game.run()
```

---

## 🧱 Core Architecture

### Entity
```python
entity = Entity(name="optional")
entity.add_component(Transform(pos=np.array([0,0])))
```
Entities hold components. Access via `entity.transform`, `entity.physics`, etc.

### Component (built‑in)
| Component | Fields |
|-----------|--------|
| `Transform` | `pos: np.ndarray`, `dirty: bool` |
| `Physics` | `mass`, `velocity`, `acceleration`, `velocity_limit`, `is_static` |
| `Collider` | `half_x`, `half_y`, `has_collision`, `elasticity` |
| `Render` | `is_visible`, `draw_priority`, `name`, `default_sym`, `default_color`, `transparent_sym` |
| `Camera` | `offset`, `zoom`, `active`, `mode` |
| `Script` | `on_tick` / `on_frame` callbacks |

### World & QueryManager
- `World` stores entities, component index, and collision grid.
- `QueryManager` caches results of `get_global(*component_types)` and `get_scene(scene_name, *types)`.
- Use `game.query_manager.get_global(Transform, Render)` to fetch all visible entities.

### Scenes & SceneManager
- `Scene` – isolated world with `on_load/unload/pause/resume` hooks.
- `SceneGroup` – ordered collection of scenes (e.g. UI layer + game layer).
- `SceneManager` handles stacking (`load`, `push`, `pop`).
- Active worlds are merged automatically for rendering.

### Systems
Systems run in four **phases**:
```python
class Phase(IntEnum):
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3
```
Built‑in systems:
- `PhysicsSystem` – updates velocities/positions (Phase.SIMULATION).
- `CollisionSystem` – resolves collisions, emits `CollisionEvent` (Phase.REACTION).
- `EntitiesRenderSystem` – draws entities with camera and textures (Phase.RENDER).
- `UISystem` – renders UI screens, handles focus (Phase.RENDER).

### Event Bus
```python
event_bus = game.event_bus
event_bus.subscribe(entity.id, Phase.REACTION, CollisionEvent, on_collision)
event_bus.emit(Phase.INPUT, MyCustomEvent())
```
Events are queued per phase and dispatched in priority order.

### Input
```python
game.input.bind_key('space', on_press=lambda: print("jump"))
if game.input.is_pressed('left'): ...
```

### UI Toolkit
- `UIScreen` – root container (fills whole screen).
- `UIText` – multi‑line text with alignment and word wrap.
- `UIButton` – focusable button with action callbacks.
- `UIProgressBar` – horizontal fill bar.
- Focus navigation: `Tab` / `Shift+Tab`, `Enter` / `Space` to activate.

```python
screen = UIScreen('main', (80, 25))
btn = UIButton('ok', x=10, y=10, w=12, h=3, text="OK", on_action=lambda g: print("clicked"))
screen.add_child(btn)
game.ui_system.register_screen(screen)
```

### Textures
Load from `textures.json`:
```json
{
  "player": [" @ ", "###"],
  "enemy":  ["^v^"]
}
```
Texture manager supports automatic zoom caching and default textures from collider size.

---

## 🎮 Example: Full Game Structure

See `example.py` in the repository – it creates:
- Player with physics, collision, and keyboard control.
- 100 random moving objects.
- UI screen with two buttons and a text label showing player position.
- Scene setup with proper `SceneManager` usage.

---

## 🛠️ Advanced Usage

### Custom System
```python
from system_manager import System

class MySystem(System):
    def __init__(self):
        super().__init__(phase=Phase.SIMULATION, priority=500,
                         required_components=frozenset([MyComponent]))
    def update(self, dt):
        entities = self._query_manager.get_global(MyComponent)
        for e in entities:
            # custom logic
```

### Transformer (cached sorting/filtering)
```python
def sort_by_priority(entities):
    return sorted(entities, key=lambda e: e.render.draw_priority)

query_manager.register_transformer(frozenset([Transform, Render]), sort_by_priority)
# Now get_transformed(Transform, Render) returns sorted list
```

### Custom Event
```python
class ScoreEvent(Event):
    def __init__(self, points):
        super().__init__(priority=10)
        self.points = points

event_bus.subscribe(0, Phase.REACTION, ScoreEvent, lambda e: print(f"+{e.points}"))
event_bus.emit(Phase.REACTION, ScoreEvent(100))
```

---

## ⚙️ Configuration

`Game(resolution, fps, tickspeed, bucket_step, background_sym, textures_path, presenter)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `resolution` | `(190,60)` | Width, height in characters |
| `fps` | `30` | Target render frames per second |
| `tickspeed` | `120` | Physics updates per second |
| `bucket_step` | `0.25` | Zoom cache granularity |
| `background_sym` | `' '` | Character for empty areas |
| `textures_path` | `'textures.json'` | JSON file with named textures |
| `presenter` | `ConsolePresenter()` | Output handler (e.g. to file) |

---

## 📝 Notes

- All positions/velocities are `numpy.float32` arrays of length 2.
- Use `entity.transform.dirty = True` after manually moving an entity to update the collision grid.
- `UISystem` automatically registers focusable elements; you can call `ui_system.set_focus(element)`.
- For Wayland on Linux, the `keyboard` library may need `sudo` – use `python -m keyboard` to test.

---

## 📄 License

This engine is provided under the MIT License.  
Feel free to use, modify, and distribute.