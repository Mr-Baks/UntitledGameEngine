from typing import Callable, Optional, Any
from abc import ABC

class Event(ABC): 
    def __init__(self, id: int, on_event: Callable, data: Any, created_at: float, priority: int = 0, source: Optional[Any] = None):
        self.id = id
        self.on_event = on_event
        self.data = data
        self.created_at = created_at
        self.priority = priority
        self.source = source

class EventBus:
    def __init__(self):
        self.subscribers = {
            0:[],
            1:[],
            2:[],
            3:[]
        }
        self.events_queue = {
            0:[],
            1:[],
            2:[],
            3:[]
        }
        
    def subscribe(self, phase: int, event: Event):
        """
        Phases:
            0: input 
            1: simulation 
            2: reaction 
            3: render
        """
        if self.subscribers.get(event) is None: 
            self.subscribers[event] = []

        for i, sub in enumerate(self.subscribers[phase]):
            if event.priority >= sub.priority: 
                self.subscribers[phase][event].insert(i, event)
                return
            
        if len(self.subscribers[phase][event]) == 0: self.subscribers[phase].append(event)

    def unsubscribe(self, id: int, phase: int):
        for event in self.subscribers[phase]:
            if event.id == id: 
                self.subscribers[phase].remove(event)
                return
            
    def emit(self, phase: int, event: Event):
        for sub in self.subscribers[phase]:
            if isinstance(sub, event): 
                for i, e in enumerate(self.events_queue[phase]):
                    if event.priority >= e.priority:
                        self.events_queue[phase].insert(i, e.on_event)
                        return
                
                if len(self.events_queue[phase]) == 0: self.events_queue[phase].append(e.on_event)
