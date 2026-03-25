from entity import Entity
from components import Component, Transform, Collider
from typing import Any, Callable, Optional
from collections import defaultdict
import numpy as np


class CollisionGrid:
    """Spatial hash grid for fast broad-phase collision queries using axis-aligned bounding boxes."""
    def __init__(self, cell_size: tuple[float, float] = (5.0, 5.0)):
        self.cell_size = np.array(cell_size, dtype=np.float32)
        self.cells: dict[tuple[int, int], set[Entity]] = defaultdict(set)
        self.entity_cells: dict[Entity, list[tuple[int, int]]] = {}

    def _get_cells(self, pos: np.ndarray, half_x: float, half_y: float) -> list[tuple[int, int]]:
        """Return list of all grid cells overlapped by the entity's AABB."""
        min_p = pos - np.array([half_x, half_y])
        max_p = pos + np.array([half_x, half_y])
        min_cell = tuple(np.floor(min_p / self.cell_size).astype(int))
        max_cell = tuple(np.floor(max_p / self.cell_size).astype(int))

        cells = []
        for y in range(min_cell[1], max_cell[1] + 1):
            for x in range(min_cell[0], max_cell[0] + 1):
                cells.append((x, y))
        return cells

    def insert(self, entity: Entity) -> None:
        """Add entity to all grid cells it overlaps."""
        if not entity.has_component(Transform) or not entity.has_component(Collider):
            return
        c = entity.collider
        if not c.has_collision:
            return

        cells = self._get_cells(entity.transform.pos, c.half_x, c.half_y)
        for cell in cells:
            self.cells[cell].add(entity)
        self.entity_cells[entity] = cells

    def remove(self, entity: Entity) -> None:
        """Remove entity from all cells it was previously occupying."""
        if entity in self.entity_cells:
            for cell in self.entity_cells[entity]:
                self.cells[cell].discard(entity)
            del self.entity_cells[entity]

    def update(self, entity: Entity) -> None:
        """Remove and re-insert entity. Used when position or size has changed."""
        if not entity.transform.dirty: return
        self.remove(entity)
        self.insert(entity)

    def get_potential(self, entity: Entity) -> set[Entity]:
        """Return set of entities that share at least one grid cell with the given entity."""
        seen = {}
        for cell in self.entity_cells.get(entity, ()):
            for e in self.cells[cell]:
                if e is not entity and e.id not in seen:
                    seen[e.id] = e
        return set(seen.values())

class World:
    """Container for all entities and pre-filtered entity lists for systems."""

    __slots__ = ('entities', 'collision_grid', 'component_index')

    def __init__(self, cell_size: tuple[int, int] = (5, 5)):
        self.entities = set()
        self.collision_grid = CollisionGrid(cell_size)
        self.component_index = {}

    def _add_entity(self, entity: Entity) -> None:
        """Add entity to world and update all relevant caches and grids."""
        self.entities.add(entity)
        self.collision_grid.insert(entity)

        index = self.component_index

        for c in entity.components:
            if index.get(c) is None: index[c] = {entity}
            else: index[c].add(entity)

    def _get_entity(self, id: int) -> Optional[Entity]:
        """Return entity by id or None if not found."""
        for e in self.entities:
            if e.id == id:
                return e
        return None

    def _remove_entity(self, id: int) -> Optional[Entity]:
        """Remove entity from world and all caches/grids."""
        removed = self._get_entity(id)

        if removed is not None: 
            self.collision_grid.remove(removed)
            self.entities.remove(removed)

        return removed

    def _get_with(self, *component_types) -> set:
        """Return entities that have all specified component types."""
        if not component_types:
            return self.entities

        sets = []
        for t in component_types:
            if t not in self.component_index:
                return set()
            sets.append(self.component_index[t])

        sets.sort(key=len)

        result = sets[0].copy()
        for s in sets[1:]:
            result &= s

        return result

class QueryManager:
    def __init__(self, scene_manager: 'SceneManager'):
        self.scene_manager = scene_manager
        
        self.global_cache: dict[frozenset[type], set[Entity]] = {}
        self.global_dirty: dict[frozenset[type], bool] = {}

        self.scene_cache: dict[str, dict[frozenset[type], set[Entity]]] = {}
        self.scene_dirty: dict[str, dict[frozenset[type], bool]] = {}

        self.transformers: dict[frozenset[type], Callable[[set[Entity]], Any]] = {}
        self.transformed_cache: dict[frozenset[type], Any] = {}
        self.transformed_dirty: dict[frozenset[type], bool] = {}

    def get_global(self, *component_types: type[Component]) -> set[Entity]:
        key = frozenset(component_types)
        if key not in self.global_dirty or self.global_dirty[key]:
            result = set()
            for world in self.scene_manager.active_worlds:
                result |= world._get_with(*component_types)
            self.global_cache[key] = result
            self.global_dirty[key] = False
        return self.global_cache[key]
    
    def get_global_scene(self, *component_types: type[Component]) -> dict[str, set[Entity]]:
        scene_ents = {}
        for sn in self.scene_manager.scenes.keys():
            scene_ents[sn] = self.get_scene(sn, *component_types)
        return scene_ents

    def get_scene(self, scene_name: str, *component_types: type[Component]) -> set[Entity]:
        if scene_name not in self.scene_cache:
            self.scene_cache[scene_name] = {}
            self.scene_dirty[scene_name] = {}

        key = frozenset(component_types)
        if key not in self.scene_dirty[scene_name] or self.scene_dirty[scene_name][key]:
            scene = self.scene_manager.get(scene_name)
            result = scene.world._get_with(*component_types) if scene else set()
            self.scene_cache[scene_name][key] = result
            self.scene_dirty[scene_name][key] = False
        return self.scene_cache[scene_name][key]

    def get_transformed(self, *component_types: type[Component]) -> Any:
        key = frozenset(component_types)
        entities = list(self.get_global(*component_types))

        if key not in self.transformers:
            return entities

        if key not in self.transformed_dirty or self.transformed_dirty[key]:
            self.transformed_cache[key] = self.transformers[key](entities)
            self.transformed_dirty[key] = False

        return self.transformed_cache[key]

    def register_transformer(self, components: frozenset[type], transformer: Callable[[set[Entity]], Any]):
        self.transformers[components] = transformer
        self.transformed_dirty[components] = True  

    def invalidate(self, component_type: type = None, scene_name: str = None) -> None:
        if component_type is None:
            self.global_dirty = {k: True for k in self.global_cache}
            self.transformed_dirty = {k: True for k in self.transformed_cache}
        else:
            for k in list(self.global_cache.keys()):
                if component_type in k:
                    self.global_dirty[k] = True
            for k in list(self.transformed_cache.keys()):
                if component_type in k:
                    self.transformed_dirty[k] = True

        if component_type is None:
            for scene_dirty in self.scene_dirty.values():
                scene_dirty = {k: True for k in scene_dirty}
        else:
            if scene_name and scene_name in self.scene_dirty:
                for k in list(self.scene_dirty[scene_name].keys()):
                    if component_type in k:
                        self.scene_dirty[scene_name][k] = True
            else:
                for scene_dirty in self.scene_dirty.values():
                    for k in list(scene_dirty.keys()):
                        if component_type in k:
                            scene_dirty[k] = True

    def on_entity_action(self, entity: Entity) -> None:
        for c in entity.components:
            self.invalidate(component_type=c)

    def clear(self) -> None:
        self.global_cache.clear()
        self.global_dirty.clear()
        self.scene_cache.clear()
        self.scene_dirty.clear()
        self.transformed_cache.clear()
        self.transformed_dirty.clear()