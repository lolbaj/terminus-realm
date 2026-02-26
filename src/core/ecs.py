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

    __slots__ = ["entities", "next_id", "components_by_type", "callbacks"]

    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.next_id = 0
        # Track components by type for fast O(1) access:
        # Type[Component] -> eid -> Component
        self.components_by_type: Dict[Type[Component], Dict[int, Component]] = (
            defaultdict(dict)
        )

        # Callback list for system notifications (e.g., spatial index)
        # (change_type, eid, comp_type, component) -> None
        self.callbacks: List[callable] = []

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

        entity = self.entities[eid]

        # Capture components for notification and remove them from type-based storage
        removed_components = []
        for comp_type, component in entity.components.items():
            removed_components.append((comp_type, component))
            if comp_type in self.components_by_type:
                self.components_by_type[comp_type].pop(eid, None)

        # Clear the entity's components
        entity.components.clear()

        # Notify callbacks after removal from storage
        for comp_type, component in removed_components:
            for callback in self.callbacks:
                callback("remove", eid, comp_type, component)

        del self.entities[eid]

    def add_component(self, eid: int, component: Component):
        """Add a component to an entity."""
        if eid not in self.entities:
            raise ValueError(f"Entity {eid} does not exist")

        entity = self.entities[eid]
        comp_type = type(component)

        # Check if updating or adding
        change_type = "update" if comp_type in entity.components else "add"

        # Update entity's component list and type-based storage
        entity.components[comp_type] = component
        self.components_by_type[comp_type][eid] = component

        # Notify callbacks
        for callback in self.callbacks:
            callback(change_type, eid, comp_type, component)

    def notify_component_change(self, eid: int, comp_type: Type[Component]):
        """Manually notify that a component's internal data has changed."""
        if eid in self.entities and comp_type in self.entities[eid].components:
            component = self.entities[eid].components[comp_type]
            for callback in self.callbacks:
                callback("update", eid, comp_type, component)

    def remove_component(self, eid: int, comp_type: Type[Component]):
        """Remove a component from an entity."""
        if eid not in self.entities:
            return

        entity = self.entities[eid]
        if comp_type in entity.components:
            component = entity.components[comp_type]
            del entity.components[comp_type]
            self.components_by_type[comp_type].pop(eid, None)

            # Notify callbacks
            for callback in self.callbacks:
                callback("remove", eid, comp_type, component)

    def get_component(
        self, eid: int, comp_type: Type[Component]
    ) -> Optional[Component]:
        """Get a specific component from an entity (optimized)."""
        return self.components_by_type.get(comp_type, {}).get(eid)

    def has_component(self, eid: int, comp_type: Type[Component]) -> bool:
        """Check if an entity has a specific component."""
        return eid in self.components_by_type.get(comp_type, {})

    def get_entities_with_components(self, *comp_types: Type[Component]) -> List[int]:
        """Get all entities that have all specified components."""
        if not comp_types:
            return []

        # Start with the smallest set of entities if possible, or just the first
        comp_dicts = [self.components_by_type.get(ct, {}) for ct in comp_types]

        # Start with first component's entity IDs
        result = set(comp_dicts[0].keys())

        # Intersect with other components' entity IDs
        for comp_dict in comp_dicts[1:]:
            result &= set(comp_dict.keys())

        return list(result)

    def get_all_entities_with_component(self, comp_type: Type[Component]) -> List[int]:
        """Get all entities that have a specific component."""
        return list(self.components_by_type.get(comp_type, {}).keys())


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
