from collections import defaultdict
from components import *
from entity import *
from event_system import *
import numpy as np


class CollisionGrid:
    """Spatial hash grid for broad-phase collision detection."""
    def __init__(self, cell_size: tuple[int, int] = (5, 5)):
        self.cell_w, self.cell_h = cell_size
        self.cells: dict[tuple[int, int], list[Entity]] = defaultdict(list)
        self.entity_cells: dict[int, set[tuple[int, int]]] = {}

    def _get_cell_keys(self, entity: Entity) -> list[tuple[int, int]]:
        """Calculate all cell coordinates entity overlaps."""
        c = entity.collider
        t = entity.transform
        if c is None or t is None:
            return []

        min_x = t.pos[0] - c.half_x
        min_y = t.pos[1] - c.half_y
        max_x = t.pos[0] + c.half_x
        max_y = t.pos[1] + c.half_y

        x1 = int(min_x // self.cell_w)
        y1 = int(min_y // self.cell_h)
        x2 = int(max_x // self.cell_w) + 1
        y2 = int(max_y // self.cell_h) + 1

        return [(x, y) for y in range(y1, y2) for x in range(x1, x2)]

    def insert(self, entity: Entity) -> None:
        """Add entity to all overlapping cells."""
        eid = id(entity)
        cells = set(self._get_cell_keys(entity))
        self.entity_cells[eid] = cells
        for cell in cells:
            self.cells[cell].append(entity)

    def remove(self, entity: Entity) -> None:
        """Remove entity from all cells it was in."""
        eid = id(entity)
        cells = self.entity_cells.pop(eid, None)
        if not cells:
            return
        for cell in cells:
            bucket = self.cells.get(cell)
            if bucket and entity in bucket:
                bucket.remove(entity)
            if not bucket:
                del self.cells[cell]

    def update(self, entity: Entity) -> None:
        """Update entity's cell membership if position changed."""
        eid = id(entity)
        old_cells = self.entity_cells.get(eid, set())
        new_cells = set(self._get_cell_keys(entity))

        if old_cells == new_cells:
            return  

        for cell in old_cells - new_cells:
            bucket = self.cells.get(cell)
            if bucket and entity in bucket:
                bucket.remove(entity)
            if not bucket:
                del self.cells[cell]

        for cell in new_cells - old_cells:
            self.cells[cell].append(entity)

        self.entity_cells[eid] = new_cells

    def get_nearby(self, entity: Entity) -> Set[Entity]:
        """Return set of entities in neighboring cells (excludes self)."""
        eid = id(entity)
        cells = self.entity_cells.get(eid, ())
        if not cells:
            return set()

        nearby = set()
        for cx, cy in cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    bucket = self.cells.get((cx + dx, cy + dy))
                    if bucket:
                        for e in bucket:
                            if e is not entity:
                                nearby.add(e)
        return nearby

class CollisionEvent(Event):
    """Detects and resolves collisions using spatial hash."""
    def __init__(self, e1: Entity, e2: Entity, priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.e1 = e1
        self.e2 = e2

class CollisionSystem:
    """Detects and resolves collisions using spatial hash."""
    def __init__(self, event_bus: EventBus, cell_size=(5, 5), elasticity: float = 0.8):
        self.collision_grid = CollisionGrid(cell_size)
        self.elasticity = elasticity
        self.event_bus = event_bus

    def process_collision(self, entities: list[Entity]) -> None:
        """Detect overlaps and resolve collisions for given entities using provided grid."""
        processed_pairs = set()

        for e in entities:
            if e.collider and e.collider.has_collision:
                if hasattr(e, 'physics') and not e.physics.is_static:
                    self.collision_grid.update(e)

        for e1 in entities:
            if not e1.collider or not e1.collider.has_collision:
                continue

            for e2 in self.collision_grid.get_nearby(e1):
                if e2 is e1 or not e2.collider or not e2.collider.has_collision:
                    continue

                id1, id2 = id(e1), id(e2)
                pair = (id1, id2) if id1 < id2 else (id2, id1)
                if pair in processed_pairs:
                    continue

                if self._aabb_intersect(e1, e2):
                    processed_pairs.add(pair)
                    self.resolve_collision(e1, e2)
                    self.event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))

    @staticmethod
    def _aabb_intersect(a: Entity, b: Entity) -> bool:
        """Check if two AABBs overlap (centers at transform.pos)."""
        dx = abs(a.transform.pos[0] - b.transform.pos[0])
        dy = abs(a.transform.pos[1] - b.transform.pos[1])
        return (dx < (a.collider.half_x + b.collider.half_x) and
                dy < (a.collider.half_y + b.collider.half_y))

    def resolve_collision(self, e1: Entity, e2: Entity) -> None:
        """Resolve penetration and apply impulse for two colliding entities."""
        pos1 = e1.transform.pos
        pos2 = e2.transform.pos
        c1 = e1.collider
        c2 = e2.collider

        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]

        overlap_x = (c1.half_x + c2.half_x) - abs(dx)
        overlap_y = (c1.half_y + c2.half_y) - abs(dy)

        if overlap_x <= 0 or overlap_y <= 0:
            return

        if overlap_x < overlap_y:
            normal = np.array([1.0, 0.0]) if dx > 0 else np.array([-1.0, 0.0])
            penetration = overlap_x
        else:
            normal = np.array([0.0, 1.0]) if dy > 0 else np.array([0.0, -1.0])
            penetration = overlap_y

        total_mass = e1.physics.mass + e2.physics.mass
        correction = (normal * penetration * 1.1) / total_mass

        rel_vel = e1.physics.velocity - e2.physics.velocity
        vel_along_normal = np.dot(rel_vel, normal)
        if vel_along_normal < 0:
            return

        impulse_scalar = (-(1 + (e1.collider.elasticity + e2.collider.elasticity) / 2) * vel_along_normal)
        impulse_scalar /= (1 / e1.physics.mass + 1 / e2.physics.mass)

        impulse = impulse_scalar * normal
        e1.physics.velocity += impulse / e1.physics.mass
        e2.physics.velocity -= impulse / e2.physics.mass

        if e1.physics.is_static:
            e1.transform.pos -= 0 
            e2.transform.pos += correction / total_mass
        elif e2.physics.is_static:
            e1.transform.pos -= correction / total_mass
            e2.transform.pos += 0
        else:
            e1.transform.pos -= correction / e2.physics.mass
            e2.transform.pos += correction / e1.physics.mass


        
class PhysicsSystem:
    def __init__(self, y_scale: float = 0.5):
        self.y_scale_vec = np.array((1, y_scale), dtype=np.float32)

    def update(self, entities: list[Entity], delta_time: float) -> None: 
        """Update position and velocity for all non-static entities."""
        dt = np.float32(delta_time) 
        for e in entities: 
            p = e.physics
            t = e.transform

            if p.is_static: continue

            p.velocity = p.velocity + p.acceleration * dt 
            vel_magnitude = np.linalg.norm(p.velocity)

            if -0.05 < vel_magnitude < 0.05: 
                p.velocity = np.zeros(2, dtype=np.float32)
                t.dirty = False
            else:
                if vel_magnitude > p.velocity_limit: 
                    p.velocity = (p.velocity / vel_magnitude) * p.velocity_limit

                t.pos = t.pos + p.velocity * dt * self.y_scale_vec
                
                t.dirty = True