from typing import Any, Callable, Optional
from abc import ABC
from time import time
from copy import copy
from enum import IntEnum


class Phase(IntEnum):
    """Game loop phases."""
    INPUT = 0
    SIMULATION = 1
    REACTION = 2
    RENDER = 3


class Event(ABC):
    """Base class for all events."""

    def __init__(
        self,
        priority: int = 0,
        timestamp: Optional[float] = None,
        source: Optional[Any] = None
    ):
        self.priority = priority
        self.timestamp = time() if timestamp is None else timestamp
        self.source = source


class EventBus:
    """Central event routing system."""

    def __init__(self):
        self.subscribers = {phase: [] for phase in Phase}
        self.event_queue = {phase: [] for phase in Phase}

    def subscribe(
        self,
        id: int,
        phase: Phase,
        event_type: type[Event],
        handler: Callable[[Event], None],
        priority: int = 0
    ):
        """Subscribe handler to event type in a phase."""
        self.subscribers[phase].append({
            'event_type': event_type,
            'id': id,
            'priority': priority,
            'handler': handler
        })

    def unsubscribe(self, phase: Phase, id: int):
        """Remove all subscriptions for given id in phase."""
        self.subscribers[phase] = [
            sub for sub in self.subscribers[phase]
            if sub['id'] != id
        ]

    def emit(self, phase: Phase, event: Event):
        """Queue event for processing in phase."""
        self.event_queue[phase].append(event)

    def dispatch(self, phase: Phase):
        """Dispatch all queued events for phase."""
        events = copy(self.event_queue[phase])
        self.event_queue[phase] = []

        subs = copy(self.subscribers[phase])

        events.sort(key=lambda e: (-e.priority, e.timestamp))
        subs.sort(key=lambda s: -s['priority'])

        for e in events:
            for sub in subs:
                if isinstance(e, sub['event_type']):
                    sub['handler'](e)
