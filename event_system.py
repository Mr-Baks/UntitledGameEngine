from typing import Any, Callable, Optional
from abc import ABC
from time import time
from enum import IntEnum


class Phase(IntEnum):
    """Game loop phases"""
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3


class Event(ABC):
    """Base class for all events"""
    __slots__ = ("priority", "timestamp", "source")

    def __init__(self, priority: int = 0, timestamp: Optional[float] = None, source: Optional[Any] = None):
        self.priority = priority
        self.timestamp = time() if timestamp is None else timestamp
        self.source = source

class EventBus:
    """Central event routing system"""

    __slots__ = ("subscribers", "event_queue", "sorted_cache", "dirty")

    def __init__(self):
        self.subscribers = {phase: {} for phase in Phase}
        self.event_queue = {phase: [] for phase in Phase}
        self.sorted_cache = {phase: {} for phase in Phase}
        self.dirty = {phase: set() for phase in Phase}

    def subscribe(self, id: int, phase: Phase, event_type: type[Event], handler: Callable[[Event], None], priority: int = 0):
        """Subscribe handler to event type in a phase"""
        table = self.subscribers[phase].setdefault(event_type, [])
        table.append((priority, id, handler))
        self.dirty[phase].add(event_type)

    def unsubscribe(self, phase: Phase, id: int):
        """Remove all subscriptions for given id in phase"""
        phase_table = self.subscribers[phase]

        for event_type, handlers in phase_table.items():
            new_handlers = [h for h in handlers if h[1] != id]
            if len(new_handlers) != len(handlers):
                phase_table[event_type] = new_handlers
                self.dirty[phase].add(event_type)

    def emit(self, phase: Phase, event: Event):
        """Queue event for processing in phase"""
        self.event_queue[phase].append(event)

    def dispatch(self, phase: Phase):
        """Dispatch all queued events for phase"""
        queue = self.event_queue[phase]
        if not queue:
            return

        self.event_queue[phase] = []

        queue.sort(key=lambda e: (-e.priority, e.timestamp))

        phase_subs = self.subscribers[phase]
        phase_cache = self.sorted_cache[phase]
        dirty = self.dirty[phase]

        for event in queue:
            etype = type(event)

            handlers = phase_subs.get(etype)
            if not handlers:
                continue

            if etype in dirty:
                handlers = sorted(handlers, key=lambda h: -h[0])
                phase_cache[etype] = handlers
                dirty.remove(etype)
            else:
                handlers = phase_cache[etype]

            for _, _, handler in handlers:
                handler(event)
