from game import Game
from entity import Entity
from components import *
from render_systems import Scene, SceneGroup
import numpy as np
from ui_system import UIText, UIScreen, UIButton

game = Game(
    resolution = (100, 30),     # ширина × высота в символах
    fps        = 1,
    tickspeed  = 120,           # частота физики (обычно выше fps)
    background_sym = '.',
    textures_path = 'textures.json'
)

# === Создаём игрока с правильными float32 ===
player = Entity().add_components(
    Transform(pos=np.array([0, 0], dtype=np.float32)),
    Physics(
        mass=np.float32(1.0),
        velocity=np.zeros(2, dtype=np.float32) + 1,
        acceleration=np.zeros(2, dtype=np.float32),
        velocity_limit=np.float32(15.0)
    ),
    Collider(half_x=4, half_y=7, elasticity=0.7),
    Render(default_sym='A', name='player', draw_priority=10, is_visible=True),
    Camera(offset=np.array([0., 0.], dtype=np.float32), zoom=1, active=True)
)

# === Скрипт управления ===
def player_controller(entity: Entity, game: Game):
    physics = entity.physics
    if physics is None:
        return

    accel = 25.0          # сила ускорения (настраивается легко)
    friction = 0.85       # трение/торможение при отсутствии ввода

    input_accel = np.zeros(2, dtype=np.float32)

    if game.input.is_pressed('a'):
        input_accel[0] -= accel
    if game.input.is_pressed('d'):
        input_accel[0] += accel
    if game.input.is_pressed('w'):
        input_accel[1] -= accel
    if game.input.is_pressed('s'):
        input_accel[1] += accel

    # Применяем управляющую силу
    physics.acceleration = input_accel

    # Простое трение, когда нет нажатия (чтобы игрок не скользил вечно)
    if np.all(input_accel == 0):
        physics.velocity *= friction

player.add_component(Script().add_tick(player_controller))

# === Полный цикл сцен (обязательно, потому что QueryManager и RenderSystem работают только через active_worlds) ===
main_scene = Scene("main_level", priority=10, cell_size=(5, 5))

level_group = SceneGroup("level1", priority=0)
level_group.add(main_scene)                # группы позволяют stacking (меню поверх уровня и т.д.)

game.scene_manager.register(level_group)   # подключает сцены к менеджеру, flush_pending и т.д.
game.scene_manager.load("level1", game)    # активирует, вызывает on_load, rebuild_active_worlds

main_scene.add(player)                     # добавляем в world + уведомляем query_manager
game.set_player(player)                    # привязывает камеру к RenderSystem

screen = UIScreen('main', (60, 20))
game.ui_system.register_screen(screen)

text = UIText('text', 3, 3, 10, 3, 'just a text')
screen.add_child(text)

def click1(_):
    text.text = 'clicked!'

button1 = UIButton('button', 3, 8, 12, 4, 'just a button', on_action=click1)
screen.add_child(button1)

def click2(_):
    button1.color = Colors.GREEN
    button1.text = 'its green'

button2 = UIButton('another_button', 16, 8, 12, 4, 'click me', on_action=click2)
screen.add_child(button2)

game.run()