from typing import Dict, Any, Optional
from components import *

class Entity:
    def __init__(self, id: int):
        self.id = id
        self.components = [Transform, Render, Physics, Script, Collider]
        self.components_dict: Dict[type, Any] = {}
    
    def get_type(self, component):
        for c in self.components:
            if isinstance(component, c): return c
        else: return None

    def add_component(self, component):
        """Add an object of component to entity"""
        self.components_dict[self.get_type(component)] = component
        return self
    
    def get_component(self, component_type):
        return self.components_dict.get(component_type)
    
    def has_component(self, component_type):
        return component_type in self.components
    
    @property
    def transform(self) -> Optional[Transform]:
        return self.get_component(Transform)
    
    @property
    def physics(self) -> Optional[Physics]:
        return self.get_component(Physics)
    
    @property
    def collider(self) -> Optional[Collider]:
        return self.get_component(Collider)
    
    @property
    def render(self) -> Optional[Render]:
        return self.get_component(Render)
    
    @property
    def script(self) -> Optional[Script]:
        return self.get_component(Script)