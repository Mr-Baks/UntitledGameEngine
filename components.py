from dataclasses import dataclass, field
import numpy as np
from typing import Callable, List
from abc import ABC
from colors import Colors


@dataclass 
class Component(ABC):
    pass

@dataclass
class Transform(Component):
    """Entity position in world coordinates."""
    pos: np.ndarray 
    dirty: bool = True

@dataclass
class Physics(Component):
    """Physical properties and motion state of an entity."""
    mass: np.float32 = np.float32(1.0)
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    velocity_limit: np.float32 = np.float32(100.0)
    is_static: bool = False

@dataclass
class Collider(Component):
    """Axis-aligned bounding box used for collision detection.
    Center is at Transform.pos."""
    half_x: float = 0.5
    half_y: float = 0.5
    has_collision: bool = True
    elasticity: float = 0.8

@dataclass
class Render(Component):
    """Visual representation properties of an entity."""
    is_visible: bool = True
    draw_priority: int = 0
    name: str | None = None
    default_sym: str = '#'
    default_color: str = Colors.WHITE
    transparent_sym: str = '\u8841'
    screen_x: int = 0
    screen_y: int = 0

@dataclass
class Camera(Component):
    """Camera properties attached to an entity."""
    offset: np.ndarray = field(default_factory=np.zeros(2, dtype=np.float32))
    zoom: float = 1.0
    active: bool = True

class Script:
    """Container for custom per-entity update callbacks."""
    def __init__(self) -> None:
        self.on_tick: List[Callable[['Entity', 'Game'], None]] = []
        self.on_frame: List[Callable[['Entity', 'Game'], None]] = []

    def add_tick(self, callback: Callable[['Entity', 'Game'], None]) -> 'Script':
        """Register callback to be called every physics tick.
        Args:
            callback: Function(entity: Entity, game: Game) -> None"""
        self.on_tick.append(callback)
        return self

    def add_frame(self, callback: Callable[['Entity', 'Game'], None]) -> 'Script':
        """Register callback to be called every render frame.
        Args:
            callback: Function(entity: Entity, game: Game) -> None"""
        self.on_frame.append(callback)
        return self

