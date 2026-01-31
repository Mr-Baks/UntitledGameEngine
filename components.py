from dataclasses import dataclass
import numpy as np
from typing import Callable, Optional


@dataclass
class Transform:
    """Represents the spatial transformation of an entity in the game world.
     
    Attributes:
        pos: Position vector (x, y) in world coordinates as a numpy array.
    """
    pos: np.ndarray[np.float32]

@dataclass
class Physics:
    """Contains physical properties and state for rigid body simulation.
    
    Attributes:
        mass: Mass of the object in arbitrary units.
        velocity: Current velocity vector as a numpy array.
        acceleration: Current acceleration vector as a numpy array.
        velocity_limit: Maximum allowable magnitude of velocity.
    """
    mass: np.float32
    velocity: np.ndarray[np.float32]
    acceleration: np.ndarray[np.float32]
    velocity_limit: np.float32

@dataclass
class Collider:
    """Defines collision detection properties for an entity.
    
    Attributes:
        hitbox_x: Width of the collision hitbox.
        hitbox_y: Height of the collision hitbox.
        has_collision: Whether this entity participates in collision detection.
                      Defaults to True.
    """
    hitbox_x: int
    hitbox_y: int
    has_collision: bool = True

@dataclass
class Render:
    """Controls rendering and visual representation of an entity.
    
    Attributes:
        is_visible: Whether the entity should be rendered. Defaults to True.
        draw_priority: Determines rendering order (lower values render first).
                      Defaults to 0.
        texture_id: Identifier for the texture to use. None indicates no texture.
                   Defaults to None.
    """
    is_visible: bool = True
    draw_priority: int = 0
    texture_id: str = None
    default_sym: str = '#'

class Script:
    """Attaches customizable behavior callbacks to an entity.
    
    Attributes:
        on_tick: Callback executed each game tick.
        on_frame: Callback executed each game frame.
    
    Note:
        All callbacks should be callable objects (functions, lambdas, etc.)
    """
    def __init__(self):
        self.on_tick = []
        self.on_frame = []

    def add_tick(self, callback: Callable[[float], None]):
        self.on_tick.append(callback)
        return self

    def add_frame(self, callback: Callable[[], None]):
        self.on_frame.append(callback)
        return self
    