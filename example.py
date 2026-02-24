from game import *


id_count = 0
def get_id():
    global id_count
    id_count += 1
    return id_count

npa = lambda *z: np.array(z, dtype=np.float32)

def debug(e: Entity, g: Game):
    print(e.physics.velocity)

def spawn_platform(x, y, w, h, game: Game, scene: Scene):
    e = Entity(get_id()).add_components(Transform(npa(x, y)), Render(), Collider(w / 2, h / 2), Physics(np.float32(100000), npa(0, 0), npa(0, 0), is_static=True))
    game.scene_manager.add_entity(scene, e)

def spawn_player(x, y, game: Game, scene: Scene):
    e = Entity(get_id()).add_components(Transform(npa(x, y)), Render(name='player'), Collider(6, 1.5), Physics(np.float32(20), npa(0, 0), npa(0, 0)), Camera(npa(0, 0)), Script().add_frame(debug))
    game.scene_manager.add_entity(scene, e)
    return e

g = Game((120, 20), 20, 40, background_sym=' ')

sg = SceneGroup('main')
s = Scene('main')
s2 = Scene('not_main')
sg.add(s).add(s2)

g.scene_manager.register(sg)
g.scene_manager.load('main')

spawn_platform(20, 0, 10, 3, g, s2)
spawn_platform(0, 10, 1000, 3, g, s2)

player = spawn_player(0, 0, g, s)
g.set_player(player)

def move_r_p():
    player.physics.velocity += npa(15, 0)

def move_r_r():
    player.physics.velocity -= npa(15, 0)

def move_l_p():
    player.physics.velocity += npa(-15, 0)

def move_l_r():
    player.physics.velocity -= npa(-15, 0)

def move_u_p():
    player.physics.velocity += npa(0, -15)

def move_u_r():
    player.physics.velocity -= npa(0, -15)

def move_d_p():
    player.physics.velocity += npa(0, 15)

def move_d_r():
    player.physics.velocity -= npa(0, 15)

def reset():
    player.physics.velocity *= 0

def zoom_plus():
    g.player.camera.zoom *= 1.1

def zoom_minus():
    g.player.camera.zoom /= 1.1

g.input.bind_key('d', on_press=move_r_p, on_release=move_r_r)
g.input.bind_key('a', on_press=move_l_p, on_release=move_l_r)
g.input.bind_key('w', on_press=move_u_p, on_release=move_u_r)
g.input.bind_key('s', on_press=move_d_p, on_release=move_d_r)
g.input.bind_key('z', on_press=zoom_plus)
g.input.bind_key('x', on_press=zoom_minus)
g.input.bind_key('r', on_press=reset)

g.render_system.main_camera.camera.zoom = 1

g.run()