import numpy as np
from tools import Tools

class Static_object:
    def __init__(self, pos: tuple, hitbox_x: float, hitbox_y: float, mass: float = 1.0, has_collision=True):
        self.pos = np.array(pos, dtype=np.float32)
        self.mass = np.float32(max(-10e8, mass))
        self.hitbox_x = np.array(hitbox_x, dtype=np.float32)
        self.hitbox_y = np.array(hitbox_y, dtype=np.float32)
        self.has_collision = has_collision

    def check_obj_collision(self, obj):
        obj_x_min = self.pos[0]
        obj_x_max = self.hitbox_x + self.pos[0]
        obj_y_min = self.pos[1]
        obj_y_max = self.hitbox_y + self.pos[1]
        oth_obj_x_min = obj.pos[0]
        oth_obj_x_max = obj.hitbox_x + obj.pos[0]
        oth_obj_y_min = obj.pos[1]
        oth_obj_y_max = obj.hitbox_y + obj.pos[1]
        
        if (obj_x_max >= oth_obj_x_min and obj_x_min <= oth_obj_x_max and 
            obj_y_max >= oth_obj_y_min and obj_y_min <= oth_obj_y_max):
            return True

    def check_collision(self, objects: list):
        collided_objects = []
        for obj in objects:
            if obj == self: 
                continue
            if self.check_obj_collision(obj): collided_objects.append(obj)

        return collided_objects

class Object(Static_object):
    def __init__(self, pos: tuple, velocity: tuple, acceleration: tuple, hitbox_x: float, hitbox_y: float, vel_limit=5.0, acc_limit=1.0, mass=1.0, has_collision=True):
        super().__init__(pos, hitbox_x, hitbox_y, mass=mass, has_collision=has_collision)
        self.velocity = np.array(velocity, dtype=np.float32)
        self.acceleration = np.array(acceleration, dtype=np.float32)
        self.vel_limit = np.float32(vel_limit)
        self.acc_limit = np.float32(acc_limit)

    def upd_params(self, t: float, force: tuple):
        t = np.float32(t)
        force = np.array(force, dtype=np.float32)

        self.acceleration += force / self.mass
        acc_magnitude = np.linalg.norm(self.acceleration)
        if acc_magnitude > self.acc_limit:
            self.acceleration = (self.acceleration / acc_magnitude) * self.acc_limit
        
        self.velocity += self.acceleration * t 
        vel_magnitude = np.linalg.norm(self.velocity)
        if vel_magnitude > self.vel_limit:
            self.velocity = (self.velocity / vel_magnitude) * self.vel_limit

        self.pos += self.velocity * t * Tools.to_float((1, 0.5))

        return self
    
    def resolve_collision(self, other_obj, elasticity=-0.8):
        if not self.has_collision or not other_obj.has_collision: return
        elasticity = np.float32(elasticity)

        overlap_x = min(self.hitbox_x + self.pos[0], other_obj.hitbox_x + other_obj.pos[0]) - max(self.pos[0], other_obj.pos[0])
        overlap_y = min(self.hitbox_y + self.pos[1], other_obj.hitbox_y + other_obj.pos[1]) - max(self.pos[1], other_obj.pos[1])
        
        if overlap_x < overlap_y:
            normal = np.array([1.0, 0.0]) if self.pos[0] < other_obj.pos[0] else np.array([-1.0, 0.0])
            penetration = overlap_x
        else:
            normal = np.array([0.0, 1.0]) if self.pos[1] < other_obj.pos[1] else np.array([0.0, -1.0])
            penetration = overlap_y

        correction = normal * penetration
        
        if not isinstance(other_obj, Object):
            self.pos += correction * 2
            self.velocity = self.velocity - 2 * np.dot(self.velocity, normal) * normal * elasticity
            return
        
        self.pos -= correction
        other_obj.pos += correction

        relative_velocity = self.velocity - other_obj.velocity
        velocity_norm = np.dot(relative_velocity, normal)
        
        if velocity_norm < 0:
            return
            
        impulse_scalar = -(1 + elasticity) * velocity_norm
        impulse_scalar /= (1 / self.mass + 1 / other_obj.mass)
        
        impulse = impulse_scalar * normal
        # print(impulse / self.mass)
        self.velocity += impulse / self.mass
        other_obj.velocity -= impulse / other_obj.mass