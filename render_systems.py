from components import *
from entity import Entity
from typing import Optional, Type, Callable, Any
import json
import sys
from enum import Enum
from abc import ABC, abstractmethod
from copy import copy
from event_system import Event, EventBus, Phase
from query_manager import World, QueryManager
from system_manager import RenderSystem, Compositor
from colors import Colors
        
rmvd = False
class Scene:
    """Single scene containing its own isolated world and lifecycle hooks."""

    __slots__ = ('name', 'priority', 'world', 'on_load', 'on_unload', 'on_pause', 'on_resume', 'paused', 'active', '_scene_manager', 'entities', '_pending_entities')

    def __init__(self, name: str, priority: int = 0, cell_size: tuple[float, float] = (5, 5)):
        self.name = name
        self.priority = priority
        self.world = World(cell_size=cell_size)
        self.entities: dict[str, Entity] = {}

        self._scene_manager: Optional[SceneManager] = None
        self._pending_entities: set[Entity] = set()

        self.on_load = []
        self.on_unload = []
        self.on_pause = []
        self.on_resume = []

        self.paused = False
        self.active = False

    def add(self, entity: Entity) -> Scene:
        """Add entity to this scene."""
        if self._scene_manager is not None:
            self.world._add_entity(entity)
            self._scene_manager.query_manager.on_entity_action(entity)
            self._scene_manager.scenes[self.name] = self
        else:
            self._pending_entities.add(entity)

        if entity.name is not None: 
            if entity.name in self.entities:
                self.entities[entity.name + f'__{entity.id}'] = entity
            else:
                self.entities[entity.name] = entity
        
        return self 

    def remove(self, entity: Optional[Entity] = None, entity_id: int = None, entity_name: str = None) -> Optional[Entity]:
        """Remove entity from scene by id or name."""
        if entity is not None:
            eid = entity.id
        elif entity_id is not None:
            eid = entity_id
        elif entity_name is not None and entity_name in self.entities:
            eid = self.entities[entity_name].id
        else:
            return None
        global rmvd
        removed = self.world._remove_entity(eid)
        
        if removed is None:
            for e in list(self._pending_entities):
                if e.id == eid:
                    self._pending_entities.remove(e)
                    removed = e
                    break

        if removed is not None:
            if removed.name and removed.name in self.entities:
                self.entities.pop(removed.name)

            if self._scene_manager and self._scene_manager.query_manager:
                self._scene_manager.query_manager.on_entity_action(removed)

        return removed

    def get_with(self, *component_types) -> set[Entity]:
        """Return entities that have all specified component types."""
        if not component_types:
            return self.world.entities

        sets = []
        for t in component_types:
            if t not in self.world.component_index:
                return set()
            sets.append(self.world.component_index[t])

        sets.sort(key=len)

        result = sets[0].copy()
        for s in sets[1:]:
            result &= s

        return result

    def get(self, name: str) -> Optional[Entity]:
        """Return entities with that name."""
        return self.entities.get(name)

    def _flush_pending(self) -> None:
        self._scene_manager.active_worlds.append(self.world)

        if not self._pending_entities:
            return

        for entity in self._pending_entities:
            self.add(entity)

        self._pending_entities.clear()
        
class SceneGroup:
    """Group of scenes rendered together, ordered by scene priority."""

    __slots__ = ('name', 'priority', '_scene_manager', 'scenes_dirty', 'scenes')

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
        self._scene_manager = None
        self.scenes_dirty = True
        self.scenes = []

    def add(self, scene: Scene) -> self:
        """Add a scene and keep scenes sorted by priority."""
        self.scenes.append(scene)
        self.scenes_dirty = True

        if self._scene_manager is not None:
            scene._scene_manager = self._scene_manager
            scene._flush_pending()
        
        return self

    def get(self, name: Optional[str]) -> Optional[Scene]:
        """Get scene by name."""
        if self.scenes_dirty:
            self.scenes.sort(key=lambda s: -s.priority)
            if self._scene_manager is not None:
                for s in self.scenes:
                    s._scene_manager = self._scene_manager
        
        if name is None: return self.scenes

        for s in self.scenes:
            if name == s.name: return s

    def remove(self, name: str) -> Optional[Scene]:
        """Remove a scene by name and return remaining scenes."""
        removed = self.get(name)
        self.scenes.remove(removed)
        self.scenes_dirty = True

        return removed

    def load(self, game):
        """Activate all scenes and call on_load callbacks."""
        for s in self.scenes:
            s.active = True
            s.paused = False
            for cb in s.on_load:
                cb(s, game)

    def unload(self, game):
        """Deactivate all scenes and call on_unload callbacks."""
        for s in self.scenes:
            s.active = False
            s.paused = False
            for cb in s.on_unload:
                cb(s, game)

    def pause(self, game):
        """Pause all active scenes and call on_pause callbacks."""
        for s in self.scenes:
            if not s.active:
                continue
            s.paused = True
            for cb in s.on_pause:
                cb(s, game)

    def resume(self, game):
        """Resume all active scenes and call on_resume callbacks."""
        for s in self.scenes:
            if not s.active:
                continue
            s.paused = False
            for cb in s.on_resume:
                cb(s, game)

class SceneManager:
    """Manages scene groups, active worlds and entity queries across scenes."""

    def __init__(self):
        self.levels = {}
        self.active_worlds = []
        self.scenes: dict[str, Scene] = {}

        self.stack = []
        self.stack_dirty = True

        self.query_manager = None

    def register(self, group: SceneGroup) -> self:
        """Register scene group."""
        self.levels[group.name] = group

        for scene in group.scenes:
            scene._scene_manager = self
            scene._flush_pending()
        
        return self

    def load(self, name: str, game: Optional[Any] = None) -> None:
        """Load scene group by name (unload previous stack)."""
        while self.stack:
            group = self.stack.pop()
            group.unload(game)

        group = self.levels[name]

        self.stack.append(group)
        group.load(game)

        self.stack_dirty = True

        for scene in self.scenes.values():
            scene._flush_pending()
        
        self.query_manager.clear()

    def push(self, name, game=None):
        if self.stack:
            self.stack[-1].pause(game)

        group = self.levels[name]

        self.stack.append(group)
        group.load(game)

        self.stack_dirty = True

    def pop(self, game=None):
        if not self.stack:
            return

        group = self.stack.pop()
        group.unload(game)

        if self.stack:
            self.stack[-1].resume(game)

        self.stack_dirty = True
            
    def get(self, scene_name: str) -> [Optional[Scene]]:
        return self.scenes.get(scene_name)

    def _rebuild_active_worlds(self):
        worlds = []
        scenes = {}

        for group in self.stack:
            for scene in group.scenes:
                if scene.active and not scene.paused:
                    worlds.append(scene.world)
                    self.scenes[scene.name] = scene

        self.active_worlds = worlds
        self.scenes = scenes
        self.stack_dirty = False

class Texture:
    """Texture data container."""

    __slots__ = ('name', 'pixels', 'w', 'h', 'transparent_sym', 'default_color')

    def __init__(self, name: str, pixels: list[str] | list[list[tuple[str, str]]], transparent_sym: Optional[str] = '`', default_color: str = Colors.WHITE):
        self.name = name
        self.pixels = []
        self.h = len(pixels)
        self.w = len(pixels[0]) if pixels else 0
        self.transparent_sym = transparent_sym
        self.default_color = default_color

        if pixels:
            if pixels[0] and type(pixels[0][0]) == tuple:
                self.pixels = pixels
            else:
                self._parse_pixels(pixels)
        
    def _parse_pixels(self, pixels: list[str]) -> None:
        for row_str in pixels:
            processed_row = []
            i = 0
            current_color = self.default_color
            row_str = row_str.replace('\\033', '\033').replace('\\x1b', '\x1b')

            while i < len(row_str):
                if row_str[i:i+2] == '\033[':
                    end = row_str.find('m', i)
                    if end != -1:
                        current_color = row_str[i+2:end]
                        i = end + 1
                        continue

                sym = row_str[i]
                processed_row.append((sym[0], current_color))
                i += 1

            self.pixels.append(processed_row)

    def zoom(self, factor: float) -> list[list[tuple[str, str]]]:
        """Return a nearest-neighbor scaled version of the texture. Does not mutate the original texture."""
        if factor == 1.0:
            return self.pixels

        new_w = max(1, int(self.w * factor))
        new_h = max(1, int(self.h * factor))

        sx = self.w / new_w
        sy = self.h / new_h

        new_pixels = []

        for y in range(new_h):
            src_y = int(y * sy)
            line = self.pixels[src_y]
            new_line = []

            for x in range(new_w):
                src_x = int(x * sx)
                new_line.append(line[src_x])

            new_pixels.append(new_line)

        return new_pixels

class TextureManager:
    """Handles texture loading, default generation, zoom caching and bbox caching."""

    def __init__(self, bucket_step: float = 0.25):
        """Initialize texture storage and zoom bucket cache."""
        self.textures: dict[str, Texture] = {}
        self.zoom_cache = {}
        self.bbox_cache: dict[str, tuple[int, int]] = {}
        self.bucket_step = 1 / bucket_step

    def load(self, path: str = 'textures.json'):
        """Load textures from a JSON file."""
        with open(path, 'r') as f:
            for name, pixels in json.load(f).items():
                self._register(Texture(name, pixels))

    def _register(self, texture: Texture):
        """Register a texture and cache its bounding box."""
        self.textures[texture.name] = texture
        self.bbox_cache[texture.name] = (texture.w, texture.h)

    def get(self, entity: Entity, zoom: float = 1) -> Texture:
        """Return a zoomed texture for the entity, using bucketed zoom caching."""
        if entity.render.name is None:
            self._set_default(entity, zoom)

        name = entity.render.name
        bucket = round(zoom * self.bucket_step) / self.bucket_step

        key = (name, bucket)
        if key in self.zoom_cache:
            return self.zoom_cache[key]

        tex = Texture(f'{name}_zoomed_{bucket}', self.textures[name].zoom(bucket))
        self.zoom_cache[key] = tex

        return tex

    def _set_default(self, entity: Entity, zoom: int):
        """Generate and register a default texture based on collider sizeand render default symbol."""
        if entity.collider is None:
            w, h = (1, 1)
        else:
            w = max(1, round(entity.collider.half_x * 2))
            h = max(1, round(entity.collider.half_y * 2))
        sym = entity.render.default_sym

        name = f'auto_{w}x{h}_{sym}'
        entity.render.name = name
        
        if not name in self.textures:
            tex = Texture(name, [sym * w for _ in range(h)], default_color=entity.render.default_color)
            self._register(tex)

    def get_bbox(self, entity: Entity, zoom: int = 1) -> tuple[int, int]:
        """Return the scaled bounding box of the entity's texture."""
        if entity.render.name is None:
            self._set_default(entity, zoom)

        bbox = self.bbox_cache[entity.render.name]
        return (int(bbox[0] * zoom), int(bbox[1] * zoom))

def render_sort(ents):
    return sorted(ents, key=lambda e: e.render.draw_priority)

class EntitiesRenderSystem(RenderSystem):
    def __init__(self, compositor: Compositor, scene_manager: SceneManager, textures_path: str = 'textures.json', bucket_step: float = 0.25):
        super().__init__(Phase.RENDER, 1000, frozenset([Transform, Render]), compositor, transformer=render_sort)
        self.renderables = []
        self.visibles = []
        self.clear()

        self.main_camera = None
        self.last_cam_state = None

        self.stack_dirty = True
        self.camera_dirty = True
        self.full_redraw = True

        self.scene_manager = scene_manager
        self.compositor = compositor
        self._query_manager: QueryManager = None
        self.texture_manager = TextureManager(bucket_step=bucket_step)
        self.texture_manager.load(path=textures_path)

    def set_camera(self, camera: Entity) -> None:
        """Set main camera entity (must have Camera component)."""
        if camera.camera is not None: 
            self.main_camera = camera
            self.scene_manager.main_camera = camera

    def _entity_aabb(self, entity: Entity) -> tuple[float, float, float, float]:
        """Calculate world-space AABB of entity's rendered texture."""
        t = entity.transform

        w, h = self.texture_manager.get_bbox(entity, self.main_camera.camera.zoom) 

        half_w = w // 2
        half_h = h // 2

        left = t.pos[0] - half_w
        right = t.pos[0] + half_w
        bottom = t.pos[1] - half_h
        top = t.pos[1] + half_h

        return left, right, bottom, top

    def collect_visibles(self, renderables: list[Entity], cam_x: int, cam_y: int) -> list[Entity]:
        """Collect entities visible in current camera frustum."""
        self.visibles.clear()

        zoom = self.main_camera.camera.zoom if self.main_camera else 1.0

        half_world_w = self.w / (2 * zoom)
        half_world_h = self.h / (2 * zoom)

        cam_rect = (
            cam_x - half_world_w,
            cam_x + half_world_w,
            cam_y - half_world_h,
            cam_y + half_world_h,
        )

        for e in renderables:
            if not e.render.is_visible:
                continue

            left, right, bottom, top = self._entity_aabb(e) 

            if right < cam_rect[0] or left > cam_rect[1] or top < cam_rect[2] or bottom > cam_rect[3]:
                continue

            self.visibles.append(e)

        return self.visibles

    def _render_entity(self, entity: Entity, cam_x: int = 0, cam_y: int = 0) -> None:
        """Draw single entity to back buffer using its texture and screen position."""
        r = entity.render
        t = entity.transform
        tex = self.texture_manager.get(entity, self.main_camera.camera.zoom)

        if t.dirty or self.camera_dirty:
            r.screen_x = round((t.pos[0] - cam_x) * self.main_camera.camera.zoom + (self.w - tex.w) / 2)
            r.screen_y = round((t.pos[1] - cam_y) * self.main_camera.camera.zoom + (self.h - tex.h) / 2)
        for y, row in enumerate(tex.pixels):
            sy = r.screen_y + y
            if sy < 0 or sy >= self.h: continue
            for x, sym in enumerate(row):
                sx = r.screen_x + x
                if sx < 0 or sx >= self.w: continue
                if sym[0] != r.transparent_sym:
                    self.put_sym(sx, sy, sym[0], color=sym[1])
                    self.update_mask[sy][sx] = True
                else:
                    self.update_mask[sy][sx] = False
    
    def render(self) -> list[list[tuple[str, str]]]:
        """Perform rendering pass: collect visibles, draw to back buffer, return reference to it."""
        if self.main_camera is None:
            return self.buffer
        self._query_manager.invalidate()
        self.renderables = self._query_manager.get_transformed(Transform, Render)

        cam_pos = self.main_camera.camera.offset + self.main_camera.transform.pos
        cam_x = int(cam_pos[0])
        cam_y = int(cam_pos[1])

        cam_state = (cam_x, cam_y, self.main_camera.camera.zoom)
        if cam_state != self.last_cam_state:
            self.camera_dirty = True
            self.last_cam_state = cam_state

        if self.scene_manager.stack_dirty:
            self.full_redraw = True
            self.scene_manager._rebuild_active_worlds()
            self.scene_manager.stack_dirty = False

        self.collect_visibles(self.renderables, cam_x, cam_y)
        if self.camera_dirty:
            self.full_redraw = True
        else:
            for e in self.visibles:
                if e.transform.dirty:
                    self.full_redraw = True
                    break

        if self.full_redraw:
            self.clear()

            for e in self.visibles:
                self._render_entity(e, cam_x, cam_y)

            self.camera_dirty = False
            self.full_redraw = False

        return self.buffer

    def compose(self) -> list[str]:
        """Convert current back buffer to printable string lines (for console output)."""
        lines = []
        for row in self.buffer:
            line = ''.join(sym for sym, _ in row)
            lines.append(line)
        return lines

    def update(self, _):
        self.render()
        self._compositor.merge(self.buffer, self.update_mask)

