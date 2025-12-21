from components import *
from entity import *
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

class CollisionSystem:
    def __init__(self, cell_size: tuple[float] = (2, 2), elasticity: float = 0.8):
        self.collision_grid = CollisionGrid(cell_size)
        self.elasticity = elasticity         

    def resolve_collision(self, entity1: Entity, entity2: Entity):
        """Resolve collision between 2 entities"""
        overlap_x = min(entity1.collider.hitbox_x + entity1.transform.pos[0], entity2.collider.hitbox_x + entity2.transform.pos[0]) - max(entity1.transform.pos[0], entity2.transform.pos[0])
        overlap_y = min(entity1.collider.hitbox_y + entity1.transform.pos[1], entity2.collider.hitbox_y + entity2.transform.pos[1]) - max(entity1.transform.pos[1], entity2.transform.pos[1])
        
        if overlap_x < overlap_y:
            normal = np.array([1.0, 0.0]) if entity1.transform.pos[0] < entity2.transform.pos[0] else np.array([-1.0, 0.0])
            penetration = overlap_x
        else:
            normal = np.array([0.0, 1.0]) if entity1.transform.pos[1] < entity2.transform.pos[1] else np.array([0.0, -1.0])
            penetration = overlap_y

        correction = normal * penetration
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

        if entity1.script is not None: entity1.script.on_collision(entity1, entity2)
        if entity2.script is not None: entity2.script.on_collision(entity2, entity1)

    def check_collision(self, entity: Entity) -> list[Entity]:
        """Check all collisions at entity"""
        if entity.collider is None or not entity.collider.has_collision: return []

        collided = []
        for e in self.collision_grid.get_nearby(entity):
            if not e.collider.has_collision: continue
            
            obj_x_min = entity.transform.pos[0]
            obj_x_max = entity.collider.hitbox_x + entity.transform.pos[0]
            obj_y_min = entity.transform.pos[1]
            obj_y_max = entity.collider.hitbox_y + entity.transform.pos[1]

            oth_obj_x_min = e.transform.pos[0]
            oth_obj_x_max = e.collider.hitbox_x + e.transform.pos[0]
            oth_obj_y_min = e.transform.pos[1]
            oth_obj_y_max = e.collider.hitbox_y + e.transform.pos[1]
        
            if (obj_x_max >= oth_obj_x_min and obj_x_min <= oth_obj_x_max and obj_y_max >= oth_obj_y_min and obj_y_min <= oth_obj_y_max):
                collided.append(e)
        return collided
    
    def process_collision(self, entities: list[Entity]):
        """Process all collisions in entities's list"""
        processed_pairs = set()
    
        for e1 in entities:
            if e1.collider is None: continue
            for e2 in self.check_collision(e1):
                if e2.collider is None: continue
                pair_id = tuple(sorted([id(e1), id(e2)]))
            
                if pair_id not in processed_pairs:
                    self.resolve_collision(e1, e2)
                    processed_pairs.add(pair_id)
                    if e1.script is not None: e1.script.on_collision(e1, e2)
                    if e2.script is not None: e1.script.on_collision(e2, e1)

class PhysicsSystem:
    def update(self, entities: list[Entity], delta_time: float, collision_system: CollisionSystem):
        """Update states of entities per delta time"""
        for e in entities:
            if e.transform is None or e.physics is None: continue

            t = np.float32(delta_time)
        
            e.physics.velocity = e.physics.velocity + e.physics.acceleration * t 
            vel_magnitude = np.linalg.norm(e.physics.velocity)
            if vel_magnitude > e.physics.velocity_limit:
                e.physics.velocity = (e.physics.velocity / vel_magnitude) * e.physics.velocity_limit

            e.transform.pos = e.transform.pos + e.physics.velocity * t * np.array((1, 0.5), dtype=np.float32)
        collision_system.collision_grid.set_cells_table(entities)
