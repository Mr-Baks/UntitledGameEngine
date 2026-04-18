[![Русский](https://img.shields.io/badge/lang-ru-blue.svg)](README.md)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README_en.md)
# UntitledGameEngine

Гибкий 2D-игровой движок для терминала/консоли, построенный на архитектуре **Entity-Component-System (ECS)**.  
Особенности: пространственное хеширование для столкновений, управление сценами, UI-тулкит, шина событий и полноцветный ANSI-вывод.

---

## ✨ Возможности

- **ECS ядро** – Сущности — это просто ID; логика в системах; данные в компонентах.
- **Пространственная хеш-сетка** – Быстрое грубое обнаружение столкновений.
- **Сцены и SceneGroup** – Изолированные миры, наложение (меню, оверлеи), хуки жизненного цикла.
- **UI Система** – Экраны, кнопки, текстовые метки, индикаторы прогресса с обработкой фокуса.
- **Шина событий** – Отправка событий по фазам (Input, Simulation, Reaction, Render).
- **Обработка ввода** – Кроссплатформенные привязки клавиш и опрос состояния.
- **Система рендеринга** – Текстуры (из JSON), масштабирование, камера, сортировка по глубине.
- **Физика** – Скорость, ускорение, масса, импульсы, статические тела.
- **Менеджер запросов** – Кэширование запросов сущностей, трансформеры (сортировка, фильтрация).
- **Нет внешних библиотек для рендеринга** – Чистые ANSI escape-последовательности и вывод в консоль.

---

## 📦 Установка

```bash
pip install numpy keyboard
```

Поместите файлы движка в папку вашего проекта.  
Движок ожидает файл `textures.json` (опционально) для именованных текстур.

---

## 🚀 Быстрый старт

```python
from game import Game
from entity import Entity
from components import *
import numpy as np

# Инициализация движка
game = Game(resolution=(120, 40), fps=30, tickspeed=60)

# Создание сущности игрока
player = Entity().add_components(
    Transform(pos=np.array([0.0, 0.0], dtype=np.float32)),
    Physics(mass=1.0, velocity=np.zeros(2), acceleration=np.zeros(2)),
    Collider(half_x=0.5, half_y=0.5),
    Render(default_sym='@', name='player'),
    Camera(offset=np.zeros(2), zoom=1.0)
)

# Простой скрипт управления
def move(entity, game):
    acc = np.zeros(2)
    if game.input.is_pressed('w'): acc[1] -= 10
    if game.input.is_pressed('s'): acc[1] += 10
    if game.input.is_pressed('a'): acc[0] -= 10
    if game.input.is_pressed('d'): acc[0] += 10
    entity.physics.acceleration = acc

player.add_component(Script().add_tick(move))

# Настройка сцены
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

## 🧱 Основная архитектура

### Сущность (Entity)
```python
entity = Entity(name="опционально")
entity.add_component(Transform(pos=np.array([0,0])))
```
Сущности хранят компоненты. Доступ через `entity.transform`, `entity.physics` и т.д.

### Компоненты (встроенные)

| Компонент | Поля |
|-----------|------|
| `Transform` | `pos: np.ndarray`, `dirty: bool` |
| `Physics` | `mass`, `velocity`, `acceleration`, `velocity_limit`, `is_static` |
| `Collider` | `half_x`, `half_y`, `has_collision`, `elasticity` |
| `Render` | `is_visible`, `draw_priority`, `name`, `default_sym`, `default_color`, `transparent_sym` |
| `Camera` | `offset`, `zoom`, `active`, `mode` |
| `Script` | колбэки `on_tick` / `on_frame` |

### World и QueryManager
- `World` хранит сущности, индекс компонентов и сетку столкновений.
- `QueryManager` кэширует результаты `get_global(*component_types)` и `get_scene(scene_name, *types)`.
- Используйте `game.query_manager.get_global(Transform, Render)` для получения всех видимых сущностей.

### Сцены и SceneManager
- `Scene` – изолированный мир с хуками `on_load/unload/pause/resume`.
- `SceneGroup` – упорядоченная коллекция сцен (например, слой UI + игровой слой).
- `SceneManager` управляет стекированием (`load`, `push`, `pop`).
- Активные миры автоматически объединяются для рендеринга.

### Системы
Системы работают в четырёх **фазах**:
```python
class Phase(IntEnum):
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3
```
Встроенные системы:
- `PhysicsSystem` – обновляет позиции/скорости (фаза SIMULATION).
- `CollisionSystem` – разрешает столкновения, генерирует `CollisionEvent` (фаза REACTION).
- `EntitiesRenderSystem` – отрисовывает сущности с камерой и текстурами (фаза RENDER).
- `UISystem` – рендерит UI-экраны, обрабатывает фокус (фаза RENDER).

### Шина событий (EventBus)
```python
event_bus = game.event_bus
event_bus.subscribe(entity.id, Phase.REACTION, CollisionEvent, on_collision)
event_bus.emit(Phase.INPUT, MyCustomEvent())
```
События ставятся в очередь по фазам и обрабатываются в порядке приоритета.

### Ввод (Input)
```python
game.input.bind_key('space', on_press=lambda: print("прыжок"))
if game.input.is_pressed('left'): ...
```

### UI-тулкит
- `UIScreen` – корневой контейнер (занимает весь экран).
- `UIText` – многострочный текст с выравниванием и переносом слов.
- `UIButton` – фокусируемая кнопка с колбэками.
- `UIProgressBar` – горизонтальный индикатор заполнения.
- Навигация по фокусу: `Tab` / `Shift+Tab`, `Enter` / `Space` для активации.

```python
screen = UIScreen('main', (80, 25))
btn = UIButton('ok', x=10, y=10, w=12, h=3, text="OK", on_action=lambda g: print("нажата"))
screen.add_child(btn)
game.ui_system.register_screen(screen)
```

### Текстуры
Загрузка из `textures.json`:
```json
{
  "player": [" @ ", "###"],
  "enemy":  ["^v^"]
}
```
Менеджер текстур поддерживает кэширование масштабирования и создание стандартных текстур на основе размера коллайдера.

---

## 🎮 Пример: полная структура игры

Смотрите `example.py` в репозитории – он создаёт:
- Игрока с физикой, столкновениями и управлением с клавиатуры.
- 100 случайно движущихся объектов.
- UI-экран с двумя кнопками и текстовой меткой, показывающей позицию игрока.
- Настройку сцен с правильным использованием `SceneManager`.

---

## 🛠️ Продвинутое использование

### Пользовательская система
```python
from system_manager import System

class MySystem(System):
    def __init__(self):
        super().__init__(phase=Phase.SIMULATION, priority=500,
                         required_components=frozenset([MyComponent]))
    def update(self, dt):
        entities = self._query_manager.get_global(MyComponent)
        for e in entities:
            # ваша логика
```

### Трансформер (кэшированная сортировка/фильтрация)
```python
def sort_by_priority(entities):
    return sorted(entities, key=lambda e: e.render.draw_priority)

query_manager.register_transformer(frozenset([Transform, Render]), sort_by_priority)
# Теперь get_transformed(Transform, Render) возвращает отсортированный список
```

### Пользовательское событие
```python
class ScoreEvent(Event):
    def __init__(self, points):
        super().__init__(priority=10)
        self.points = points

event_bus.subscribe(0, Phase.REACTION, ScoreEvent, lambda e: print(f"+{e.points}"))
event_bus.emit(Phase.REACTION, ScoreEvent(100))
```

---

## ⚙️ Конфигурация

`Game(resolution, fps, tickspeed, bucket_step, background_sym, textures_path, presenter)`

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `resolution` | `(190,60)` | Ширина, высота в символах |
| `fps` | `30` | Целевая частота кадров рендеринга |
| `tickspeed` | `120` | Обновлений физики в секунду |
| `bucket_step` | `0.25` | Точность кэширования масштаба |
| `background_sym` | `' '` | Символ для пустых областей |
| `textures_path` | `'textures.json'` | JSON-файл с текстурами |
| `presenter` | `ConsolePresenter()` | Обработчик вывода (например, в файл) |

---

## 📝 Примечания

- Все позиции и скорости — `numpy.float32` массивы длины 2.
- Используйте `entity.transform.dirty = True` после ручного перемещения сущности, чтобы обновить сетку столкновений.
- `UISystem` автоматически регистрирует фокусируемые элементы; вы можете вызвать `ui_system.set_focus(element)`.
- Для Wayland на Linux библиотека `keyboard` может требовать `sudo` – для теста используйте `python -m keyboard`.

---

## 📄 Лицензия

Движок распространяется под лицензией MIT.  
Вы можете свободно использовать, модифицировать и распространять.