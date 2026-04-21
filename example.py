import numpy as np
from game import Game
from components import Transform, Physics, Collider, Render, Script, Camera
from entity import Entity
from render_systems import Scene, SceneGroup
from ui_system import UIScreen, UIText, UIProgressBar, UIButton, Align
from colors import Colors


def main():
    game = Game(resolution=(100, 25), fps=60, tickspeed=120, bucket_step=0.25)

    def jump_action():
        phys = player.physics
        if abs(phys.velocity[1]) < 2.0:
            phys.velocity[1] = -65.0

    game.input.bind_key('space', on_press=jump_action)
    game.input.bind_key('a')
    game.input.bind_key('d')
    game.input.bind_key('left')
    game.input.bind_key('right')

    demo_group = SceneGroup("demo_platformer")
    level = Scene("level1", priority=0)
    demo_group.add(level)
    game.scene_manager.register(demo_group)

    global player
    player = Entity("player")
    player.add_components(
        Transform(pos=np.array([12.0, 20.0], dtype=np.float32)),
        Physics(
            mass=1.0,
            velocity=np.zeros(2, dtype=np.float32),
            acceleration=np.array([0.0, 80.0], dtype=np.float32), 
            velocity_limit=65.0
        ),
        Collider(half_x=0.75, half_y=1.1, elasticity=0),
        Render(draw_priority=100, default_color=Colors.CYAN),
        Camera(offset=np.array([0.0, -2.0], dtype=np.float32), zoom=1),
        Script()
    )

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
    level.add(player)

    def add_platform(name: str, x: float, y: float, half_x: float, half_y: float = 0.5):
        plat = Entity(name)
        plat.add_components(
            Transform(pos=np.array([x, y], dtype=np.float32)),
            Physics(is_static=True),
            Collider(half_x=half_x, half_y=half_y),
            Render(default_sym='═', default_color=Colors.WHITE, draw_priority=0)
        )
        level.add(plat)

    add_platform("ground", 45.0, 34.0, 48.0)
    add_platform("plat1", 18.0, 26.0, 7.0)
    add_platform("plat2", 38.0, 21.0, 6.0)
    add_platform("plat3", 65.0, 18.0, 9.0)
    add_platform("plat4", 85.0, 27.0, 5.0)
    add_platform("high", 55.0, 12.0, 4.0)

    enemy = Entity("enemy")
    enemy.add_components(
        Transform(pos=np.array([65.0, 16.0], dtype=np.float32)),
        Physics(
            mass=1.0,
            velocity=np.array([-55.0, 0.0], dtype=np.float32),
            acceleration=np.array([0.0, 480.0], dtype=np.float32),
            velocity_limit=65.0
        ),
        Collider(half_x=0.9, half_y=0.9),
        Render(default_sym='Z', default_color=Colors.RED, draw_priority=50),
        Script()
    )

    def enemy_tick(e: Entity, _):
        pos = e.transform.pos
        vel = e.physics.velocity

        left_bound = 52.0
        right_bound = 78.0

        if (vel[0] < 0 and pos[0] <= left_bound) or (vel[0] > 0 and pos[0] >= right_bound):
            vel[0] *= -1.0
            pos[0] += np.sign(vel[0]) * 0.3

    enemy.script.add_tick(enemy_tick)
    level.add(enemy)

    coins = []

    def create_coin(x: float, y: float):
        coin = Entity(f"coin_{x:.1f}")
        coin.add_components(
            Transform(pos=np.array([x, y], dtype=np.float32)),
            Collider(half_x=0.4, half_y=0.4),
            Render(default_sym='○', default_color=Colors.YELLOW, draw_priority=80),
            Script()
        )
        coins.append(coin)
        level.add(coin)
        return coin

    create_coin(20.0, 23.0)
    create_coin(40.0, 18.0)
    create_coin(70.0, 15.0)
    create_coin(57.0, 9.0)
    create_coin(88.0, 24.0)

    def coin_tick(e: Entity, g: Game):
        if np.linalg.norm(e.transform.pos - player.transform.pos) < 1.8:
            g.score += 10
            e.render.is_visible = False
            level.remove(e)

    for coin in coins:
        coin.script.add_tick(coin_tick)

    game.set_player(player)

    ui_screen = UIScreen("hud", (100, 40))
    game.ui_system.register_screen(ui_screen)

    score_text = UIText(name="score", x=60, y=1, w=35, h=1, text="Score: 0000", align=Align.LEFT)

    def quit_action(g: Game):
        g.is_running = False
        print("\033[?25h")

    quit_btn = UIButton(name="quit_btn", x=86, y=1, w=12, h=3, text="QUIT", color=Colors.RED, on_action=quit_action)

    ui_screen.add_child(score_text)
    ui_screen.add_child(quit_btn)

    game.score = 0

    updater = Entity("ui_updater")
    updater.add_component(Script())

    def ui_frame(_, g: Game):
        for e in g.query_manager.get_global(Transform):
            if 'coin' in e.name: print('COIN')
            if e.id == 10: print('!!!')
        score_text.text = f"Score: {g.score:04d}"

    updater.script.add_frame(ui_frame)
    level.add(updater)

    game.scene_manager.load("demo_platformer", game)
    game.run()


if __name__ == "__main__":
    main()