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
    """Initialize event with optional priority, timestamp and source.
        Args:
            priority: Higher values are processed first (default: 0)
            timestamp: Event creation time (defaults to current time)
            source: Optional object that triggered the event"""
    def __init__(self):
        self.subscribers = {phase: {} for phase in Phase}
        self.event_queue = {phase: [] for phase in Phase}
        self.sorted_cache = {phase: {} for phase in Phase}
        self.dirty = {phase: set() for phase in Phase}

    def subscribe(self, id: int, phase: Phase, event_type: type[Event], handler: Callable[[Event], None], priority: int = 0):
        """Register handler for specific event type in given phase.
        Args:
            id: Unique subscriber identifier (usually entity id)
            phase: Phase during which the event should be processed
            event_type: Type of event to listen for
            handler: Callback function that receives the event
            priority: Higher values processed earlier (default: 0)"""
        table = self.subscribers[phase].setdefault(event_type, [])
        table.append((priority, id, handler))
        self.dirty[phase].add(event_type)

    def unsubscribe(self, phase: Phase, id: int) -> None:
        """Remove all subscriptions for given subscriber id in specified phase.
        Args:
            phase: Phase to clean subscriptions from
            id: Subscriber identifier to remove"""
        phase_table = self.subscribers[phase]

        for event_type, handlers in phase_table.items():
            new_handlers = [h for h in handlers if h[1] != id]
            if len(new_handlers) != len(handlers):
                phase_table[event_type] = new_handlers
                self.dirty[phase].add(event_type)

    def emit(self, phase: Phase, event: Event) -> None:
        """Queue an event for processing in the specified phase.
        Args:
            phase: Target processing phase
            event: Event instance to dispatch"""
        self.event_queue[phase].append(event)
        
    def dispatch(self, phase: Phase) -> None:
        """Process all queued events for the given phase.
        Events are sorted by descending priority and ascending timestamp.
        Handlers are executed in registered priority order.
        Args:
            phase: Phase whose queued events should be dispatched"""
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