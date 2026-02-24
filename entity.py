from typing import Set, Dict, Type, Any, Optional
from components import Transform, Physics, Collider, Render, Camera, Script


class Entity:
    """Basic ECS entity. ID + collection of components."""

    __slots__ = ('id', 'components', 'components_dict')

    def __init__(self, id: int):
        self.id = id
        self.components: Set[Type] = set()
        self.components_dict: Dict[Type, Any] = {}

    def add_component(self, component: Any) -> 'Entity':
        """Add one component (fluent)."""
        comp_type = type(component)
        self.components.add(comp_type)
        self.components_dict[comp_type] = component
        return self

    def add_components(self, *components: Any) -> 'Entity':
        """Add multiple components at once (fluent)."""
        for c in components:
            self.add_component(c)
        return self

    def get_component[T](self, component_type: Type[T]) -> Optional[T]:
        """Get component by type or None."""
        return self.components_dict.get(component_type)

    def has_component(self, component_type: Type) -> bool:
        """Check if entity has component of given type."""
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
    def camera(self) -> Optional[Camera]:
        return self.get_component(Camera)

    @property
    def script(self) -> Optional[Script]:
        return self.get_component(Script)