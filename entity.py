from components import *
from typing import Dict, Any, Optional, Callable, List


class Entity:
    def __init__(self, id: int):
        self.id = id
        self.components: list[type] = [Transform, Render, Physics, Collider, Script]
        self.components_dict: Dict[type, Any] = {}

    def add_component(self, component):
        """Add a component instance to the entity"""
        comp_type = type(component)
        if comp_type not in self.components:
            self.components.append(comp_type)
        self.components_dict[comp_type] = component
        return self

    def add_components(self, *components):
        for c in components:
            self.add_component(c)
        return self

    def get_component(self, component_type):
        return self.components_dict.get(component_type)

    def has_component(self, component_type):
        return component_type in self.components_dict

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