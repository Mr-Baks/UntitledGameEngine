from components import *
from entity import Entity
from typing import Optional
import json
from copy import copy


HIGHLIGHTS = {'default': ('+', '-', '|'),  
              'empty': (' ', ' ', ' '), 
              'focused': ('#', '=', 'I')}

class SceneRenderSystem:
    """Handles rendering of entities to a console-based screen with camera tracking.
    This system manages texture loading, entity rendering with draw priorities
    """
    
    def __init__(self, resolution: tuple[int]):
        self.target_entity = None
        self.resolution = resolution
        self.symbol = '#'
        self.last_entities_poses = {}
        self.last_screen = []
        self.entity_list_cache = {}
        self.load_textures()

    def load_textures(self):
        """Loads texture definitions from textures.json file"""
        with open('textures.json', 'r+') as f:
            self.textures = json.load(f)

    def set_target(self, target: Entity):
        """Sets the target entity that the camera will follow"""
        self.target_entity = target
    
    def _render_entity(self, screen: list[list[str]], entity: Entity, 
                       target_x: int, target_y: int):
        """Renders a single entity onto the screen buffer"""
        collider = entity.collider
        render = entity.render
        transform = entity.transform

        if render is None or transform is None or not render.is_visible: 
            return

        if self.textures.get(str(render.texture_id)) is None:
            if collider is None: return
            if render.texture_id is None: render.texture_id = str(entity.id)
            self.textures[str(render.texture_id)] = [self.symbol * collider.hitbox_x for _ in range(collider.hitbox_y)]
        texture = self.textures[str(render.texture_id)]

        screen_x = target_x + round(transform.pos[0])
        screen_y = target_y - round(transform.pos[1])

        for y, row in enumerate(texture):
            for x, _ in enumerate(row):
                sym_x = screen_x + x
                sym_y = screen_y - y
                if 0 <= sym_x < self.resolution[0] and 0 <= sym_y < self.resolution[1]:
                    screen[sym_y][sym_x] = texture[y][x]

    def print_screen(self, entities_list: list[Entity], frame_style: str = 'default'):
        """Renders and prints the complete screen to the console"""
        highlight = HIGHLIGHTS.get(frame_style, HIGHLIGHTS['default'])
        screen = self.render(entities_list)

        border = highlight[0] + highlight[1] * self.resolution[0] + highlight[0]
        print(border)
        for row in screen:
            print(highlight[2] + ''.join(row) + highlight[2])
        print(border)

    def render(self, entities_list: list[Entity], screen: Optional[list[list[str]]] = None) -> list[list]:
        """Renders all visible entities to a screen buffer. Returns 2D list representing the rendered screen with all entities drawn"""
        if screen is None: 
            screen = [[' ' for _ in range(self.resolution[0])] for _ in range(self.resolution[1])]
        
        entities_list = copy(entities_list)
        for e in entities_list: 
            if e.render is None or e.transform is None: 
                entities_list.remove(e)

        current_e_list_cache = {}
        entities_poses = {}
    
        for e in entities_list:
            e_hash = id(e)
            current_e_list_cache[e_hash] = e.render.draw_priority
            entities_poses[e_hash] = tuple(e.transform.pos.tolist())
    
        if self.last_entities_poses == entities_poses and self.entity_list_cache == current_e_list_cache:
            return self.last_screen
        else:
            self.last_entities_poses = entities_poses.copy()
            self.sorted_entities_list = sorted(entities_list, key=lambda e: e.render.draw_priority)
            self.entity_list_cache = current_e_list_cache.copy()

        entities_list = self.sorted_entities_list

        if self.target_entity is None:
            center_x, center_y = (0, 0)
        else:
            target_pos = self.target_entity.transform.pos + np.array(
                (0, 0) if self.target_entity.collider is None else 
                (self.target_entity.collider.hitbox_x, self.target_entity.collider.hitbox_y)
            ) // 2
            center_x = self.resolution[0] // 2 - round(target_pos[0])
            center_y = self.resolution[1] // 2 + round(target_pos[1])

        for e in entities_list:
            self._render_entity(screen, e, center_x, center_y)

        self.last_screen = screen
        return screen