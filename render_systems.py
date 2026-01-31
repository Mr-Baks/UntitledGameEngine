from components import *
from entity import Entity
from typing import Optional
import json
from copy import copy
from event_system import Event, EventBus, Phase
        

class World:
    def __init__(self):
        self.entities = []
        self.renderables = []
        self.collidables = []
        self.physics_entities = []
        self.entities_with_on_tick = []
        self.entities_with_on_frame = []

    def add_entity(self, entity: Entity):
        self.entities.append(entity)

        if entity.transform is not None:
            if entity.render is not None:
                self.renderables.append(entity)

            if entity.physics is not None:
                self.physics_entities.append(entity)

            if entity.collider is not None:
                self.collidables.append(entity)

        script = entity.script
        if script is not None:
            if script.on_tick is not []:
                self.entities_with_on_tick.append(entity)

            if script.on_frame is not []:
                self.entities_with_on_frame.append(entity)

        return self

    def get_entity(self, id: int) -> Optional[Entity]:
        for e in self.entities:
            if e.id == id:
                return e
        return None

    def remove_entity(self, id: int) -> Optional[Entity]:
        removed = self.get_entity(id)

        if removed is None:
            return None

        self.entities.remove(removed)
        if removed in self.renderables:
            self.renderables.remove(removed)

        if removed in self.collidables:
            self.collidables.remove(removed)

        if removed in self.physics_entities:
            self.physics_entities.remove(removed)

        if removed in self.entities_with_on_tick:
            self.entities_with_on_tick.remove(removed)

        if removed in self.entities_with_on_frame:
            self.entities_with_on_frame.remove(removed)

        return removed

class SceneRenderSystem:
    """Handles rendering of entities to a console-based screen with camera tracking. This system manages texture loading, entity rendering with draw priorities"""
    def __init__(self, resolution: tuple[int], event_bus: EventBus):
        self.target_entity = None
        self.resolution = resolution
        self.event_bus = event_bus
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
    
    def _render_entity(self, screen: list[list[str]], entity: Entity, target_x: int, target_y: int):
        """Renders a single entity into the screen buffer"""
        collider = entity.collider
        render = entity.render
        transform = entity.transform

        if self.textures.get(str(render.texture_id)) is None:
            if collider is None: return
            if render.texture_id is None: render.texture_id = str(entity.id)
            self.textures[str(render.texture_id)] = [render.default_sym * collider.hitbox_x for _ in range(collider.hitbox_y)]
        texture = self.textures[str(render.texture_id)]

        screen_x = target_x + round(transform.pos[0])
        screen_y = target_y - round(transform.pos[1])

        for y, row in enumerate(texture):
            for x, _ in enumerate(row):
                sym_x = screen_x + x
                sym_y = screen_y - y
                if 0 <= sym_x < self.resolution[0] and 0 <= sym_y < self.resolution[1]:
                    screen[sym_y][sym_x] = texture[y][x]

    def print_screen(self, entities_list: list[Entity], frame_style: str = 'default', screen: Optional[list[list[str]]] = None):
        """Renders and prints the complete screen to the console"""
        highlight = ('+', '-', '|')
        screen = self.render(entities_list, screen=screen)

        border = highlight[0] + highlight[1] * self.resolution[0] + highlight[0]
        print(border)
        for row in screen:
            print(highlight[2] + ''.join(row) + highlight[2])
        print(border)

    def render(self, entities_list: list[Entity], screen: Optional[list[list[str]]] = None) -> list[list]:
        """Renders all visible entities to a screen buffer. Returns 2D list representing the rendered screen with all entities drawn """
        if screen is None: 
            screen = [[' ' for _ in range(self.resolution[0])] for _ in range(self.resolution[1])]
        entities_list = [e for e in entities_list if e.render is not None and e.transform is not None]

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
                (self.target_entity.collider.hitbox_x, self.target_entity.collider.hitbox_y)) // 2
            center_x = self.resolution[0] // 2 - round(target_pos[0])
            center_y = self.resolution[1] // 2 + round(target_pos[1])

        for e in entities_list:
            self._render_entity(screen, e, center_x, center_y)

        self.last_screen = screen
        return screen