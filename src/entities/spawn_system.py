"""
Spawning system for NPCs and monsters in the roguelike game.
"""

import random
import math
from core.ecs import EntityManager
from entities.entities import EntityFactory
from world.map import GameMap
from world.persistent_world import get_persistent_world


class SpawnSystem:
    """System for spawning NPCs and monsters."""

    def __init__(
        self,
        entity_manager: EntityManager,
        entity_factory: EntityFactory,
        spatial_index=None,
    ):
        self.entity_manager = entity_manager
        self.entity_factory = entity_factory
        self.spatial_index = spatial_index
        self.persistent_world = get_persistent_world()
        self.global_spawn_rates = {
            "goblin": 0.3,
            "orc": 0.15,
            "spider": 0.25,
            "skeleton": 0.15,
            "bat": 0.15,
        }

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

        # Find all walkable positions in the room once
        valid_positions = []
        for y in range(room_y1 + 1, room_y2):
            for x in range(room_x1 + 1, room_x2):
                if game_map.is_walkable(x, y):
                    if not self.spatial_index or not self.spatial_index.is_occupied(
                        x, y
                    ):
                        valid_positions.append((x, y))

        if not valid_positions:
            return []

        # Randomly sample without replacement if possible
        count = min(num_monsters, len(valid_positions))
        samples = random.sample(valid_positions, count)

        for x, y in samples:
            # Choose a monster type based on spawn rates
            monster_type = self._choose_monster_type(x, y)

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

        # Try up to num_monsters * 2 times to find valid spots
        for _ in range(num_monsters * 2):
            if len(spawned) >= num_monsters:
                break

            # Find a position near the player
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(radius * 0.3, radius)

            x = int(player_x + distance * math.cos(angle))
            y = int(player_y + distance * math.sin(angle))

            # Make sure the position is within bounds and walkable
            if (
                0 <= x < game_map.width
                and 0 <= y < game_map.height
                and game_map.is_walkable(x, y)
            ):
                if not self.spatial_index or not self.spatial_index.is_occupied(x, y):
                    monster_type = self._choose_monster_type(x, y)
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

        # Find all walkable positions
        walkable_positions = []
        for y in range(game_map.height):
            for x in range(game_map.width):
                if game_map.is_walkable(x, y):
                    if not self.spatial_index or not self.spatial_index.is_occupied(
                        x, y
                    ):
                        walkable_positions.append((x, y))

        if not walkable_positions:
            return []

        # Spawn monsters at random walkable positions
        count = min(num_monsters, len(walkable_positions))
        samples = random.sample(walkable_positions, count)

        for x, y in samples:
            # Calculate world coordinates for correct biome lookup
            world_x = x
            world_y = y

            monster_type = self._choose_monster_type(world_x, world_y)
            monster_id = self.entity_factory.create_monster(x, y, monster_type)
            spawned.append(monster_id)

        return spawned
