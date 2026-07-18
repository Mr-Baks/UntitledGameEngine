[![Русский](https://img.shields.io/badge/lang-ru-blue.svg)](README.md)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README_en.md)

# UntitledGameEngine

Гибкий 2D-игровой движок для терминальных/консольных сред, построенный на архитектуре **Сущность-Компонент-Система (ECS)**.
Включает пространственное хеширование для коллизий, управление сценами, UI-тулкит, шину событий и полноценную ANSI-цветопередачу.

---

## ✨ Возможности

- **Ядро ECS** – сущности — это просто ID; логика в системах; данные в компонентах.
- **Пространственная хеш-сетка** – быстрая широкофазная проверка коллизий.
- **Сцены и группы сцен** – изолированные миры, наложение (меню, оверлеи), хуки жизненного цикла.
- **UI-система** – экраны, кнопки, текстовые метки, индикаторы прогресса с управлением фокусом.
- **Шина событий** – фазовая диспетчеризация событий (ввод, симуляция, реакция, рендер).
- **Обработка ввода** – кроссплатформенная (Windows/Linux X11) привязка клавиш и опрос состояния.
- **Система рендеринга** – текстуры (из JSON), масштабирование, следование камеры, сортировка по глубине.
- **Физика** – скорость, ускорение, масса, импульсы, статические тела.
- **Менеджер запросов** – кэшируемые запросы сущностей, трансформеры (сортировка, фильтрация).
- **Нет внешних библиотек рендеринга** – чистые ANSI-escape-последовательности и вывод в консоль.

---

## 📦 Установка

```bash
pip install numpy keyboard
```

Поместите файлы движка в директорию вашего проекта.
Движок ожидает файл `textures.json` (опционально) для именованных текстур.

**Примечание**: на Linux Wayland библиотека `keyboard` может требовать `sudo`. Для тестирования используйте `python -m keyboard`.

---

## 🚀 Быстрый старт

```python
import numpy as np
from game import Game
from entity import Entity
from components import Transform, Physics, Collider, Render, Camera, Script
from render_systems import Scene, SceneGroup
from colors import Colors

# Инициализация движка
game = Game(
    resolution=(100, 25),
    fps=60,
    tickspeed=120,
    bucket_step=0.25,
    background_sym=' ',
    textures_path='textures.json'
)

# Привязка ввода
def jump_action():
    phys = player.physics
    if abs(phys.velocity[1]) < 2.0:
        phys.velocity[1] = -65.0

game.input.bind_key('space', on_press=jump_action)
game.input.bind_key('a')
game.input.bind_key('d')
game.input.bind_key('left')
game.input.bind_key('right')

# Создание сущности игрока
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

# Скрипт управления игроком
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

# Настройка сцены
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

## 🧱 Основная архитектура

### Сущность (Entity)

```python
entity = Entity(name="optional")
entity.add_component(Transform(pos=np.array([0,0], dtype=np.float32)))
entity.add_components(Physics(), Collider(), Render())
```

Сущности хранят компоненты. Доступ через свойства: `entity.transform`, `entity.physics`, `entity.collider`, `entity.render`, `entity.camera`, `entity.script`.

### Компоненты (встроенные)

| Компонент | Поля |
|-----------|------|
| `Transform` | `pos: np.ndarray[float32, (2,)]`, `dirty: bool` |
| `Physics` | `mass: float32`, `velocity: np.ndarray`, `acceleration: np.ndarray`, `velocity_limit: float32`, `is_static: bool` |
| `Collider` | `half_x: float`, `half_y: float`, `has_collision: bool`, `elasticity: float` |
| `Render` | `is_visible: bool`, `draw_priority: int`, `name: str \| None`, `default_sym: str`, `default_color: str`, `transparent_sym: str`, `screen_x: int`, `screen_y: int` |
| `Camera` | `offset: np.ndarray`, `zoom: float`, `active: bool` |
| `Script` | `on_tick: list[callable]`, `on_frame: list[callable]` – используйте `add_tick(cb)` / `add_frame(cb)` |

### Мир (World) и Менеджер запросов (QueryManager)

- `World` хранит сущности, индекс компонентов и сетку коллизий.
- `QueryManager` кэширует результаты `get_global(*component_types)` и `get_scene(scene_name, *component_types)`.
- Используйте `game.query_manager.get_global(Transform, Render)` для получения всех видимых сущностей.
- Трансформеры: `query_manager.register_transformer(frozenset([Transform, Render]), sort_fn)` – затем `get_transformed(Transform, Render)` возвращает преобразованный (например, отсортированный) список.

### Сцены (Scene) и Менеджер сцен (SceneManager)

- `Scene(name, priority, cell_size)` – изолированный мир с колбэками `on_load`, `on_unload`, `on_pause`, `on_resume`.
- `SceneGroup(name, priority)` – упорядоченная коллекция сцен (например, UI-слой + игровой слой).
- `SceneManager` управляет стеками: `load(name, game)`, `push(name, game)`, `pop(game)`.
- Активные миры автоматически объединяются для рендеринга и запросов.

### Системы

Системы выполняются в четырех **фазах**:

```python
class Phase(IntEnum):
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3
```

Встроенные системы (регистрируются автоматически `Game`):

- `PhysicsSystem` – обновляет скорости/позиции (Phase.SIMULATION, приоритет=1000).
- `CollisionSystem` – разрешает коллизии, генерирует `CollisionEvent` (Phase.REACTION, приоритет=1000).
- `EntitiesRenderSystem` – отрисовывает сущности с учётом камеры и текстур (Phase.RENDER, приоритет=1000).
- `UISystem` – рендерит UI-экраны, управляет фокусом (Phase.RENDER, приоритет=1000).

### Шина событий (Event Bus)

```python
event_bus = game.event_bus
event_bus.subscribe(entity.id, Phase.REACTION, CollisionEvent, on_collision)
event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))
```

События ставятся в очередь по фазам и диспетчеризуются в порядке приоритета (сначала высшие), затем по времени.

### Ввод (Input)

```python
game.input.bind_key('space', on_press=lambda: print("jump"))
game.input.bind_key('a', on_press=move_left, on_release=stop_left)

if game.input.is_pressed('left'): ...
```

`bind_key` возвращает `self` для цепочек вызовов. Клавиши нормализуются (`' '` → `'space'`, `'arrow left'` → `'left'`).

### UI-тулкит

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

- Навигация по фокусу: `Tab` / `Shift+Tab`, `Enter` / `Space` для активации.
- `UISystem` автоматически собирает элементы, способные принимать фокус.

### Текстуры

Загрузка из `textures.json`:

```json
{
  "player": [" @ ", "###"],
  "enemy":  ["^v^"]
}
```

Менеджер текстур поддерживает автоматическое кэширование масштабированных версий (с шагом `bucket_step`) и генерацию текстуры по умолчанию из размера коллайдера + `Render.default_sym`.

---

## 🎮 Пример

См. `example.py` – демо-платформер с:
- Игроком с физикой, коллизиями и управлением с клавиатуры.
- Статическими платформами.
- Следованием камеры за игроком.
- Настройкой сцены через `SceneManager`.

---

## 🛠️ Продвинутое использование

### Пользовательская система

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

Регистрация: `game.system_manager.register(MySystem(), Phase.SIMULATION)`

### Трансформер (кэшируемая сортировка/фильтрация)

```python
def sort_by_priority(entities):
    return sorted(entities, key=lambda e: e.render.draw_priority)

game.query_manager.register_transformer(frozenset([Transform, Render]), sort_by_priority)
# Теперь get_transformed(Transform, Render) возвращает отсортированный список
```

### Пользовательское событие

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

## ⚙️ Конфигурация

`Game(resolution, fps, tickspeed, bucket_step, background_sym, textures_path, presenter)`

| Параметр | Значение по умолчанию | Описание |
|-----------|----------------------|----------|
| `resolution` | `(190, 60)` | Ширина, высота в символах |
| `fps` | `30` | Целевая частота кадров рендеринга |
| `tickspeed` | `120` | Обновлений физики в секунду |
| `bucket_step` | `0.25` | Гранулярность кэша масштабирования (1/шаг) |
| `background_sym` | `' '` | Символ для пустых областей |
| `textures_path` | `'textures.json'` | JSON-файл с именованными текстурами |
| `presenter` | `ConsolePresenter()` | Обработчик вывода (например, в файл) |

---

## 📝 Примечания

- Все позиции/скорости — массивы `numpy.float32` длины 2.
- Установите `entity.transform.dirty = True` после ручного перемещения сущности для обновления сетки коллизий.
- `UISystem` автоматически регистрирует элементы, способные принимать фокус; для программной установки фокуса вызовите `ui_system.set_focus(element)`.
- Для Wayland на Linux библиотека `keyboard` может требовать `sudo` – тестируйте через `python -m keyboard`.
- Хук `keyboard` выполняется в отдельном потоке; `Input.stop()` или `game.input.stop()` корректно завершают работу при выходе.

---

## 📄 Лицензия

Данный движок распространяется под лицензией MIT.
Вы можете свободно использовать, модифицировать и распространять его.