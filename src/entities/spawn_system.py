"""
Spawning system for NPCs and monsters in the roguelike game.
"""

import random
import math
from core.ecs import EntityManager
from entities.entities import EntityFactory
from entities.components import Position
from world.map import GameMap
from world.persistent_world import get_persistent_world


class SpawnSystem:
    """System for spawning NPCs and monsters."""

    def __init__(self, entity_manager: EntityManager, entity_factory: EntityFactory):
        self.entity_manager = entity_manager
        self.entity_factory = entity_factory
        self.persistent_world = get_persistent_world()
        self.global_spawn_rates = {
            "goblin": 0.3,
            "orc": 0.15,
            "spider": 0.25,
            "skeleton": 0.15,
            "bat": 0.15,
        }

    def _get_occupied_positions(self) -> set:
        """Helper to get a set of all occupied positions."""
        occupied = set()
        for eid in self.entity_manager.entities:
            pos = self.entity_manager.get_component(eid, Position)
            if pos:
                occupied.add((pos.x, pos.y))
        return occupied

    def spawn_monsters_in_room(
        self,
        game_map: GameMap,
        room_x1: int,
        room_y1: int,
        room_x2: int,
        room_y2: int,
        num_monsters: int = 1,
    ):
        """Spawn monsters in a specific room area."""
        spawned = []
        occupied = self._get_occupied_positions()

        for _ in range(num_monsters):
            # Find a walkable position in the room
            valid_positions = []
            for y in range(room_y1 + 1, room_y2):
                for x in range(room_x1 + 1, room_x2):
                    if game_map.is_walkable(x, y) and (x, y) not in occupied:
                        valid_positions.append((x, y))

            if valid_positions:
                x, y = random.choice(valid_positions)
                occupied.add((x, y))  # Mark as occupied for next monster in same call

                # Choose a monster type based on spawn rates
                monster_type = self._choose_monster_type()

                # Create the monster
                monster_id = self.entity_factory.create_monster(x, y, monster_type)
                spawned.append(monster_id)

        return spawned

    def spawn_monsters_around_player(
        self,
        game_map: GameMap,
        player_x: int,
        player_y: int,
        radius: int = 10,
        num_monsters: int = 3,
    ):
        """Spawn monsters around the player within a certain radius."""
        spawned = []
        occupied = self._get_occupied_positions()

        for _ in range(num_monsters):
            # Find a position near the player
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(radius * 0.3, radius)

            x = int(player_x + distance * round(math.cos(angle)))
            y = int(player_y + distance * round(math.sin(angle)))

            # Make sure the position is within bounds and walkable
            if (
                0 <= x < game_map.width
                and 0 <= y < game_map.height
                and game_map.is_walkable(x, y)
                and (x, y) not in occupied
            ):
                occupied.add((x, y))
                monster_type = self._choose_monster_type(
                    x, y
                )  # Use biome-specific spawning
                monster_id = self.entity_factory.create_monster(x, y, monster_type)
                spawned.append(monster_id)

        return spawned

    def _choose_monster_type(self, x: int = None, y: int = None) -> str:
        """Choose a monster type based on spawn rates and biome if coordinates provided."""
        # If coordinates are provided, use biome-specific creatures
        if x is not None and y is not None:
            biome = self.persistent_world.get_biome(x, y)
            creatures = self.persistent_world.get_creatures_for_biome(biome)

            # If in a special area, adjust spawn rates
            area = self.persistent_world.get_area_at(x, y)
            if area and area.area_type == "town":
                # Towns have ONLY peaceful NPCs
                return random.choice(["guard", "merchant", "citizen", "dog"])
            else:
                # Use biome-specific creatures
                return random.choice(creatures)
        else:
            # Use global spawn rates if no coordinates provided
            choices = list(self.global_spawn_rates.keys())
            weights = list(self.global_spawn_rates.values())
            return random.choices(choices, weights=weights)[0]

    def spawn_level_monsters(
        self, game_map: GameMap, chunk_x: int, chunk_y: int, num_monsters: int = 5
    ):
        """Spawn monsters throughout the level."""
        spawned = []
        occupied = self._get_occupied_positions()

        # Find all walkable positions
        walkable_positions = []
        for y in range(game_map.height):
            for x in range(game_map.width):
                if game_map.is_walkable(x, y) and (x, y) not in occupied:
                    walkable_positions.append((x, y))

        # Spawn monsters at random walkable positions
        for _ in range(min(num_monsters, len(walkable_positions))):
            if walkable_positions:
                x, y = random.choice(walkable_positions)
                walkable_positions.remove((x, y))

                # Calculate world coordinates for correct biome lookup
                # Note: With full map, chunk_x/y might be irrelevant or 0,0
                # But we keep it compatible
                world_x = x  # Assuming global coords for full map
                world_y = y

                monster_type = self._choose_monster_type(world_x, world_y)
                monster_id = self.entity_factory.create_monster(x, y, monster_type)
                spawned.append(monster_id)

        return spawned
