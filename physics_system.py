from collections import defaultdict
from components import *
from entity import *
from event_system import *
import numpy as np


class CollisionGrid:
    """Spatial hash grid for broad-phase collision detection.

    Each entity occupies one or more cells depending on its hitbox size.
    Nearby entities are retrieved by looking at the entity's cells and adjacent cells.
    """

    def __init__(self, cell_size: tuple[int, int]):
        self.cell_w, self.cell_h = cell_size
        self.cells_table: dict[tuple[int, int], list[Entity]] = defaultdict(list)
        self.entities_table: dict[int, list[tuple[int, int]]] = {}

    def _get_cell_keys(self, entity: Entity):
        """Compute the set of grid cells that the entity occupies."""
        c = entity.collider
        t = entity.transform
        if c is None or t is None:
            return []

        x1 = int(t.pos[0] // self.cell_w)
        y1 = int(t.pos[1] // self.cell_h)
        x2 = int((t.pos[0] + c.hitbox_x) // self.cell_w) + 1
        y2 = int((t.pos[1] + c.hitbox_y) // self.cell_h) + 1

        return [(x, y) for y in range(y1, y2) for x in range(x1, x2)]

    def set_cells_table(self, entities: list[Entity]):
        """Populate cells_table and entities_table with all entities."""
        self.cells_table.clear()
        self.entities_table.clear()

        for e in entities:
            eid = id(e)
            cell_list = []
            self.entities_table[eid] = cell_list

            for k in self._get_cell_keys(e):
                self.cells_table[k].append(e)
                cell_list.append(k)

    def get_nearby(self, entity: Entity):
        """Return a set of entities that are in the same or neighboring cells."""
        eid = id(entity)
        cells = self.entities_table.get(eid)
        if not cells:
            return set()

        nearby = set()
        for cx, cy in cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    bucket = self.cells_table.get((cx + dx, cy + dy))
                    if not bucket:
                        continue
                    for e in bucket:
                        if e is not entity:
                            nearby.add(e)
        return nearby

class CollisionEvent(Event):
    """Event emitted when two entities collide."""
    def __init__(self, e1: Entity, e2: Entity, priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.e1 = e1
        self.e2 = e2

class CollisionSystem:
    """Collision detection and resolution system using spatial hashing."""

    def __init__(self, event_bus: EventBus, cell_size=(2, 2), elasticity: float = 0.8):
        self.collision_grid = CollisionGrid(cell_size)
        self.elasticity = elasticity
        self.event_bus = event_bus

    def process_collision(self, entities: list[Entity]):
        """Detect and resolve collisions among all given entities."""
        self.collision_grid.set_cells_table(entities)
        processed_pairs = set()

        for e1 in entities:
            if not e1.collider.has_collision:
                continue

            id1 = id(e1)
            for e2 in self.collision_grid.get_nearby(e1):
                if not e2.collider.has_collision:
                    continue

                id2 = id(e2)
                pair = (id1, id2) if id1 < id2 else (id2, id1)
                if pair in processed_pairs:
                    continue

                if self._aabb_intersect(e1, e2):
                    processed_pairs.add(pair)
                    self.resolve_collision(e1, e2)
                    self.event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))

    @staticmethod
    def _aabb_intersect(a: Entity, b: Entity) -> bool:
        """Check if two entities' axis-aligned bounding boxes intersect."""
        ax1, ay1 = a.transform.pos
        ax2 = ax1 + a.collider.hitbox_x
        ay2 = ay1 + a.collider.hitbox_y

        bx1, by1 = b.transform.pos
        bx2 = bx1 + b.collider.hitbox_x
        by2 = by1 + b.collider.hitbox_y

        return ax1 <= bx2 and ax2 >= bx1 and ay1 <= by2 and ay2 >= by1

    def resolve_collision(self, entity1: Entity, entity2: Entity):
        """Resolve collision between two entities using positional correction and impulse."""
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

class PhysicsSystem:
    def update(self, entities: list[Entity], delta_time: float): 
        """Update states of entities per delta time""" 
        for e in entities: 
            t = np.float32(delta_time) 

            e.physics.velocity = e.physics.velocity + e.physics.acceleration * t 

            vel_magnitude = np.linalg.norm(e.physics.velocity) 
            if vel_magnitude > e.physics.velocity_limit: 
                e.physics.velocity = (e.physics.velocity / vel_magnitude) * e.physics.velocity_limit 

            e.transform.pos = e.transform.pos + e.physics.velocity * t * np.array((1, 0.5), dtype=np.float32)