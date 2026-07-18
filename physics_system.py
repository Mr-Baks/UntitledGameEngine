from components import *
from entity import *
from event_system import *
from system_manager import System
from query_manager import QueryManager
import numpy as np


class CollisionEvent(Event):
    """Detects and resolves collisions using spatial hash."""
    def __init__(self, e1: Entity, e2: Entity, priority=0, timestamp=None, source=None):
        super().__init__(priority, timestamp, source)
        self.e1 = e1
        self.e2 = e2

class CollisionSystem(System):
    """Performs broad-phase (spatial grid) + narrow-phase (AABB) collision detection and resolution."""

    def __init__(self, event_bus: EventBus):
        super().__init__(Phase.REACTION, 1000, frozenset([Transform, Collider]), None)
        self.event_bus = event_bus
        self._query_manager: QueryManager = None

    def _AABB_intersects(self, e1: Entity, e2: Entity) -> bool:
        """Check if two entities' AABBs are overlapping (narrow-phase test)."""
        t1, c1 = e1.transform, e1.collider
        t2, c2 = e2.transform, e2.collider
        dx = abs(t1.pos[0] - t2.pos[0])
        dy = abs(t1.pos[1] - t2.pos[1])
        return dx < (c1.half_x + c2.half_x) and dy < (c1.half_y + c2.half_y)
    
    def _resolve_collision(self, e1: Entity, e2: Entity) -> None:
        """Resolve penetration and apply impulse based on masses and elasticity."""
        t1, p1, c1 = e1.transform, e1.physics, e1.collider
        t2, p2, c2 = e2.transform, e2.physics, e2.collider

        if p1 is None or p2 is None: return

        dx = t2.pos[0] - t1.pos[0]
        dy = t2.pos[1] - t1.pos[1]
        ox = c1.half_x + c2.half_x - abs(dx)
        oy = c1.half_y + c2.half_y - abs(dy)
        if ox <= 0 or oy <= 0:
            return

        if ox < oy:
            penetration = ox
            normal = np.array([np.sign(dx) if dx != 0 else 0.0, 0.0], dtype=np.float32)
        else:
            penetration = oy
            normal = np.array([0.0, np.sign(dy) if dy != 0 else 0.0], dtype=np.float32)
        if np.all(normal == 0):
            normal = np.array([1.0, 0.0])

        e = min(c1.elasticity, c2.elasticity)

        if p1.is_static:
            t2.pos += normal * penetration
        elif p2.is_static:
            t1.pos -= normal * penetration
        else:
            inv_m1 = 1.0 / p1.mass if p1.mass > 0 else 0.0
            inv_m2 = 1.0 / p2.mass if p2.mass > 0 else 0.0
            total = inv_m1 + inv_m2
            if total > 0:
                c1_ = penetration * (inv_m1 / total)
                c2_ = penetration * (inv_m2 / total)
                t1.pos -= normal * c1_
                t2.pos += normal * c2_

        v_rel = p2.velocity - p1.velocity
        v_rel_n = np.dot(v_rel, normal)
        if v_rel_n >= 0: return

        inv_m1 = 0.0 if p1.is_static else 1.0 / max(p1.mass, 1e-6)
        inv_m2 = 0.0 if p2.is_static else 1.0 / max(p2.mass, 1e-6)
        total_inv = inv_m1 + inv_m2
        if total_inv > 0:
            j = -(1 + e) * v_rel_n / total_inv
            p1.velocity -= j * normal * inv_m1
            p2.velocity += j * normal * inv_m2

    def update(self, _) -> None:
        """Update spatial grid for moved entities and resolve all active collisions."""
        for world in self._query_manager.scene_manager.active_worlds:

            entities = list(world._get_with(Transform, Collider, Physics))
        
            for e in entities:
                if e.transform.dirty and not e.physics.is_static:
                    world.collision_grid.update(e)

            checked = set()
            resolve_count = 0

            for i, e1 in enumerate(entities):
                if not e1.collider.has_collision:
                    continue
                
                potentials = world.collision_grid.get_potential(e1)

                for e2 in potentials:
                    if e2.id <= e1.id:
                        continue
                
                    pair = (e1.id, e2.id)
                    if pair in checked:
                        continue
                    checked.add(pair)

                    if self._AABB_intersects(e1, e2):
                        self._resolve_collision(e1, e2)
                        self.event_bus.emit(Phase.REACTION, CollisionEvent(e1, e2))
                        resolve_count += 1

class PhysicsSystem(System):
    def __init__(self, y_scale: float = 0.5):
        super().__init__(Phase.SIMULATION, 1000, frozenset([Transform, Physics]), None)
        self.y_scale_vec = np.array((1, y_scale), dtype=np.float32)
        self._query_manager: QueryManager = None

    def update(self, delta_time: float) -> None: 
        """Update position and velocity for all non-static entities."""
        dt = np.float32(delta_time) 
        entities = self._query_manager.get_global(*self.required_components)
        
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