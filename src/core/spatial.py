"""
Spatial indexing system for the ECS.
Now supports incremental updates via ECS callbacks.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.ecs import EntityManager


class SpatialIndex:
    """A simple grid-based spatial index for entities with a Position component.
    Maintains index incrementally using EntityManager callbacks.
    """

    def __init__(self, entity_manager: "EntityManager"):
        self.entity_manager = entity_manager
        # (x, y) -> set of entity IDs
        self.pos_to_entities: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
        # entity ID -> (x, y)
        self.entity_to_pos: Dict[int, Tuple[int, int]] = {}

        # Track types for fast filtering
        self.monsters: Set[int] = set()
        self.players: Set[int] = set()
        self.items: Set[int] = set()

        # Register callback
        self.entity_manager.callbacks.append(self.on_component_change)

    def on_component_change(self, change_type, eid, comp_type, component):
        """Handle component changes incrementally."""
        from entities.components import Position, Monster, Player, Item

        if comp_type == Position:
            # Handle Position change
            old_pos = self.entity_to_pos.get(eid)
            new_pos = (component.x, component.y)

            if change_type == "remove":
                if old_pos:
                    self.pos_to_entities[old_pos].discard(eid)
                    if not self.pos_to_entities[old_pos]:
                        del self.pos_to_entities[old_pos]
                    del self.entity_to_pos[eid]
            else:  # add or update
                if old_pos:
                    if old_pos == new_pos:
                        return  # No change
                    self.pos_to_entities[old_pos].discard(eid)
                    if not self.pos_to_entities[old_pos]:
                        del self.pos_to_entities[old_pos]

                self.pos_to_entities[new_pos].add(eid)
                self.entity_to_pos[eid] = new_pos

        elif comp_type == Monster:
            if change_type == "remove":
                self.monsters.discard(eid)
            else:
                self.monsters.add(eid)
        elif comp_type == Player:
            if change_type == "remove":
                self.players.discard(eid)
            else:
                self.players.add(eid)
        elif comp_type == Item:
            if change_type == "remove":
                self.items.discard(eid)
            else:
                self.items.add(eid)

    def rebuild(self):
        """Deprecated: Rebuilding is now incremental.
        Only call if the entire manager is cleared or on initial load."""
        self.pos_to_entities.clear()
        self.entity_to_pos.clear()
        self.monsters.clear()
        self.players.clear()
        self.items.clear()

        from entities.components import Position, Monster, Player, Item

        # Position cache
        pos_components = self.entity_manager.components_by_type.get(Position, {})
        for eid, pos in pos_components.items():
            coords = (pos.x, pos.y)
            self.pos_to_entities[coords].add(eid)
            self.entity_to_pos[eid] = coords

        # Categorize
        self.monsters = set(
            self.entity_manager.components_by_type.get(Monster, {}).keys()
        )
        self.players = set(
            self.entity_manager.components_by_type.get(Player, {}).keys()
        )
        self.items = set(self.entity_manager.components_by_type.get(Item, {}).keys())

    def get_entities_at(self, x: int, y: int) -> Set[int]:
        """Get all entities at a specific position."""
        return self.pos_to_entities.get((x, y), set())

    def get_monsters_at(self, x: int, y: int) -> List[int]:
        """Get all monsters at a specific position."""
        entities = self.get_entities_at(x, y)
        if not entities:
            return []
        return [eid for eid in entities if eid in self.monsters]

    def get_items_at(self, x: int, y: int) -> List[int]:
        """Get all items at a specific position."""
        entities = self.get_entities_at(x, y)
        if not entities:
            return []
        return [eid for eid in entities if eid in self.items]

    def is_occupied(self, x: int, y: int, ignore_items: bool = True) -> bool:
        """Check if a position is occupied by any blocking entity."""
        entities = self.get_entities_at(x, y)
        if not entities:
            return False

        if ignore_items:
            for eid in entities:
                if eid in self.monsters or eid in self.players:
                    return True
            return False

        return len(entities) > 0

    def get_occupied_positions(self) -> Set[Tuple[int, int]]:
        """Get all positions occupied by monsters or players."""
        occupied = set()
        for eid in self.monsters:
            if eid in self.entity_to_pos:
                occupied.add(self.entity_to_pos[eid])
        for eid in self.players:
            if eid in self.entity_to_pos:
                occupied.add(self.entity_to_pos[eid])
        return occupied
