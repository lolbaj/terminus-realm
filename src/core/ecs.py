"""
Entity Component System (ECS) framework for the roguelike game.
"""

from dataclasses import dataclass
from typing import Dict, List, Type, Optional
from collections import defaultdict


@dataclass
class Component:
    """Base class for all components."""

    # Using slots to reduce memory usage
    __slots__ = []


class Entity:
    """An entity in the game world."""

    __slots__ = ["eid", "components"]

    def __init__(self, eid: int):
        self.eid = eid
        self.components: Dict[Type[Component], Component] = {}


class EntityManager:
    """Manages entities and their components."""

    __slots__ = ["entities", "next_id", "component_to_entities"]

    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.next_id = 0
        # Track which entities have which components
        self.component_to_entities: Dict[Type[Component], set] = defaultdict(set)

    def create_entity(self) -> int:
        """Create a new entity and return its ID."""
        eid = self.next_id
        self.next_id += 1
        self.entities[eid] = Entity(eid)
        return eid

    def destroy_entity(self, eid: int):
        """Destroy an entity and remove all its components."""
        if eid not in self.entities:
            return

        # Remove entity from component mappings
        for comp_type, comp_set in self.component_to_entities.items():
            comp_set.discard(eid)

        del self.entities[eid]

    def add_component(self, eid: int, component: Component):
        """Add a component to an entity."""
        if eid not in self.entities:
            raise ValueError(f"Entity {eid} does not exist")

        entity = self.entities[eid]
        comp_type = type(component)

        # Remove old component if exists
        if comp_type in entity.components:
            # Remove from component mapping
            self.component_to_entities[comp_type].discard(eid)

        # Add new component
        entity.components[comp_type] = component
        self.component_to_entities[comp_type].add(eid)

    def remove_component(self, eid: int, comp_type: Type[Component]):
        """Remove a component from an entity."""
        if eid not in self.entities:
            return

        entity = self.entities[eid]
        if comp_type in entity.components:
            del entity.components[comp_type]
            self.component_to_entities[comp_type].discard(eid)

    def get_component(
        self, eid: int, comp_type: Type[Component]
    ) -> Optional[Component]:
        """Get a specific component from an entity."""
        if eid not in self.entities:
            return None

        return self.entities[eid].components.get(comp_type)

    def has_component(self, eid: int, comp_type: Type[Component]) -> bool:
        """Check if an entity has a specific component."""
        if eid not in self.entities:
            return False

        return comp_type in self.entities[eid].components

    def get_entities_with_components(self, *comp_types: Type[Component]) -> List[int]:
        """Get all entities that have all specified components."""
        if not comp_types:
            return []

        # Start with entities that have the first component
        result = self.component_to_entities[comp_types[0]].copy()

        # Intersect with entities that have other components
        for comp_type in comp_types[1:]:
            result &= self.component_to_entities[comp_type]

        return list(result)

    def get_all_entities_with_component(self, comp_type: Type[Component]) -> List[int]:
        """Get all entities that have a specific component."""
        return list(self.component_to_entities[comp_type])


class System:
    """Base class for all systems."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def update(self, dt: float):
        """Update the system. Override in subclasses."""
        pass


class SystemManager:
    """Manages game systems."""

    def __init__(self, entity_manager: EntityManager):
        self.systems: List[System] = []
        self.entity_manager = entity_manager

    def add_system(self, system: System):
        """Add a system to be managed."""
        self.systems.append(system)

    def update_all(self, dt: float):
        """Update all systems."""
        for system in self.systems:
            system.update(dt)
