from components import *
from entity import *
from event_system import *
import numpy as np


class CollisionGrid:
    """Simple spatial grid for optimization"""
    def __init__(self, cell_size: tuple[int]):
        self.cell_size = np.array(cell_size)
        self.cells_table = {}
        self.entities_table = {}

    def _get_cell_keys(self, entity: Entity):
        """Marks up spatial grid"""
        if entity.collider is None: return
        start = entity.transform.pos // self.cell_size
        end = (entity.transform.pos + np.array((entity.collider.hitbox_x, entity.collider.hitbox_y))) // self.cell_size + 1
        start, end = start.astype(int), end.astype(int)

        for cell_y in range(start[1], end[1]):
            for cell_x in range(start[0], end[0]): 
                yield (cell_x, cell_y)

    def set_cells_table(self, entities: list[Entity]):
        """Sets dictionaries with entities and their cells"""
        self.cells_table = {}
        self.entities_table = {}
        
        for e in entities:
            if self.entities_table.get(e) is None: self.entities_table[e] = []
            for k in self._get_cell_keys(e):
                if self.cells_table.get(k) is None: self.cells_table[k] = []
                self.cells_table[k].append(e)
                self.entities_table[e].append(k)
    
    def get_nearby(self, entity: Entity): 
        """Returns nearby entities with entity"""
        nearby_entities = set()
        checked = set()
        for cell in self.entities_table[entity]:
            for x in range(-1, 2):
                for y in range(-1, 2):
                    nearby_cell = (cell[0] + x, cell[1] + y)
                    if self.cells_table.get(nearby_cell) is None or nearby_cell in checked: continue
                    checked.add(nearby_cell)
                    for e in self.cells_table[nearby_cell]: 
                        if e != entity and not e in nearby_entities: nearby_entities.add(e)
        return list(nearby_entities)

class DetectCollisionEvent(Event):
    def __init__(self, entities: list[Entity], priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.entities = entities

class ProcessCollisionEvent(Event):
    def __init__(self, collided_pairs: set[tuple[Entity, Entity]], priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.collided_pairs = collided_pairs

class CollisionEvent(Event):
    def __init__(self, e1: Entity, e2: Entity, priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.e1 = e1
        self.e2 = e2

class CollisionSystem:
    def __init__(self, event_bus: EventBus, cell_size: tuple[float]=(2, 2), elasticity: float=0.8):
        self.collision_grid = CollisionGrid(cell_size)
        self.elasticity = elasticity
        self.event_bus = event_bus

        event_bus.subscribe(id=1, phase=Phase.SIMULATION, event_type=DetectCollisionEvent, handler=self._handle_detect_col_event)
        event_bus.subscribe(id=2, phase=Phase.REACTION, event_type=ProcessCollisionEvent, handler=self._handle_process_col_event, priority=1)

    def _handle_detect_col_event(self, event: DetectCollisionEvent):
        entities = event.entities
        self.collision_grid.set_cells_table(entities)

        collided_pairs = set()

        for e1 in entities:
            if e1.collider is None or e1.transform is None or e1.physics is None or not e1.collider.has_collision:
                continue

            for e2 in self._check_entity_collision(e1):
                pair = tuple(sorted((e1, e2), key=id))
                collided_pairs.add(pair)

        if collided_pairs:
            self.event_bus.emit(Phase.REACTION, ProcessCollisionEvent(collided_pairs))

    def _handle_process_col_event(self, event: ProcessCollisionEvent):
        for e1, e2 in event.collided_pairs:
            self.resolve_collision(e1, e2)
            self.event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))

    def _check_entity_collision(self, entity: Entity) -> list[Entity]:
        if entity not in self.collision_grid.entities_table:
            return []

        collided = []

        for other in self.collision_grid.get_nearby(entity):
            if other.collider is None or other.transform is None or other.physics is None or not other.collider.has_collision:
                continue
            if self._aabb_intersect(entity, other):
                collided.append(other)

        return collided

    def _aabb_intersect(self, a: Entity, b: Entity) -> bool:
        ax1, ay1 = a.transform.pos
        ax2 = ax1 + a.collider.hitbox_x
        ay2 = ay1 + a.collider.hitbox_y

        bx1, by1 = b.transform.pos
        bx2 = bx1 + b.collider.hitbox_x
        by2 = by1 + b.collider.hitbox_y

        return ax1 <= bx2 and ax2 >= bx1 and ay1 <= by2 and ay2 >= by1

    def resolve_collision(self, entity1: Entity, entity2: Entity):
        overlap_x = min(entity1.transform.pos[0] + entity1.collider.hitbox_x, entity2.transform.pos[0] + entity2.collider.hitbox_x) - max(entity1.transform.pos[0], entity2.transform.pos[0])
        overlap_y = min(entity1.transform.pos[1] + entity1.collider.hitbox_y, entity2.transform.pos[1] + entity2.collider.hitbox_y) - max(entity1.transform.pos[1], entity2.transform.pos[1])

        if overlap_x < overlap_y:
            normal = np.array([1.0, 0.0]) if entity1.transform.pos[0] < entity2.transform.pos[0] else np.array([-1.0, 0.0])
            penetration = overlap_x
        else:
            normal = np.array([0.0, 1.0]) if entity1.transform.pos[1] < entity2.transform.pos[1] else np.array([0.0, -1.0])
            penetration = overlap_y

        correction = normal * penetration * 0.5
        entity1.transform.pos -= correction
        entity2.transform.pos += correction

        relative_velocity = entity1.physics.velocity - entity2.physics.velocity
        velocity_norm = np.dot(relative_velocity, normal)

        if velocity_norm < 0:
            return

        impulse_scalar = -(1 + self.elasticity) * velocity_norm
        impulse_scalar /= (1 / entity1.physics.mass + 1 / entity2.physics.mass)

        impulse = impulse_scalar * normal
        entity1.physics.velocity += impulse / entity1.physics.mass
        entity2.physics.velocity -= impulse / entity2.physics.mass

class PhysicsUpdateEvent(Event):
    def __init__(self, entities: list[Entity], delta_time: float, priority = 0, timestamp = None, source = None):
        super().__init__(priority, timestamp, source)
        self.entities = entities
        self.delta_time = delta_time

class PhysicsSystem:
    def __init__(self, event_bus: EventBus):
        event_bus.subscribe(0, Phase.SIMULATION, PhysicsUpdateEvent, self._handle_upd_event)

    def _handle_upd_event(self, event: PhysicsUpdateEvent):
        self.update(event.entities, event.delta_time)

    def update(self, entities: list[Entity], delta_time: float):
        """Update states of entities per delta time"""
        for e in entities:
            if e.transform is None or e.physics is None: continue

            t = np.float32(delta_time)
        
            e.physics.velocity = e.physics.velocity + e.physics.acceleration * t 
            vel_magnitude = np.linalg.norm(e.physics.velocity)
            if vel_magnitude > e.physics.velocity_limit:
                e.physics.velocity = (e.physics.velocity / vel_magnitude) * e.physics.velocity_limit

            e.transform.pos = e.transform.pos + e.physics.velocity * t * np.array((1, 0.5), dtype=np.float32)

