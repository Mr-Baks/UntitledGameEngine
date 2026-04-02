from abc import ABC, abstractmethod
from components import Component
from typing import Optional, Callable
from query_manager import QueryManager
from event_system import Phase


class System(ABC):
    """Base class for all systems."""
    def __init__(self, phase: int, priority: int, required_components: frozenset[Component], transformer: Optional[Callable] = None):
        self.priority = priority
        self.required_components = required_components
        self.transformer = transformer
        self._query_manager: QueryManager = None

    @abstractmethod
    def update(dt: float) -> None:
        """Main update method. dt is always passed, but some systems may ignore it"""
        pass

class RenderSystem(System):
    def __init__(self, phase: int, priority: int, required_components: frozenset[Component], compositor: Compositor, transformer: Optional[Callable] = None):
        super().__init__(phase, priority, required_components, transformer=transformer)
        self._compositor = compositor
        self.w, self.h = compositor.w, compositor.h
        self.bg_byte = compositor.bg_byte
        self.stride = compositor.stride
        self.size = compositor.size
        self.buffer = bytearray(self.size)
        self.update_mask = [False for _ in range(self.size)]

    def put_sym(self, x: int, y: int, sym: str) -> None:
        """Put single symbol at screen coordinates (clipped)."""
        if not (0 <= y < self.h and 0 <= x < self.w):
            return
        if ord(sym) > 255:
            sym = '#'
        self.buffer[y * self.stride + x] = ord(sym)
        self.buffer_dirty = True

    def get_sym(self, x: int, y: int) -> str:
        """Get symbol from back buffer at coordinates."""
        return str(self.buffer[y * self.stride + x])

    def clear(self) -> None:
        """Fill back buffer with background symbol."""
        self.buffer[:] = bytes([self.bg_byte]) * self.size
        for y in range(self.h):
            self.buffer[y * self.stride + self.w] = 10

class SystemManager:
    """Manages registration, ordering and execution of all systems. Systems are grouped by phase and sorted by priority within each phase."""
    def __init__(self, query_manager: QueryManager, phases_count: int = 4):
        self._query_manager = query_manager
        self.systems: dict[int, list[System]] = {i: [] for i in range(phases_count)}
        self.phases_count = phases_count

    def register(self, system: System, phase: int) -> None:
        """Register a system instance into the correct phase."""
        system._query_manager = self._query_manager
        if system.transformer is not None:
            self._query_manager.register_transformer(system.required_components, system.transformer)
        systems = self.systems[phase]
        systems.append(system)
        systems.sort(key=lambda s: -s.priority)

    def update_phase(self, phase: int, dt: float) -> None:
        """Execute all systems in the given phase."""
        for s in self.systems[phase]:
            s.update(dt)

    def update_all(self, dt: int) -> None:
        """Run all phases in order (0 → phases_count-1)."""
        for p in range(4):
            self.update_phase(p, dt)

    def remove(self, system_type: type[System], phase: int) -> list[System]:
        """Remove all instances of the given system type in the phase."""
        removed = []
        systems =  self.systems[p]

        for s in systems:
            if isinstance(s, system_type):
                systems.remove(s)
                removed.append(s)

        return removed

    def get(self, system_type: type[System], phase: int) -> Optional[System]:
        """Get system by type in the phase."""
        for s in self.systems[phase]:
            if isinstance(s, system_type): return s
        
        return None

    def clear(self):
        """Remove all registered systems"""
        for p in range(self.phases_count):
            self.systems[p].clear()
            