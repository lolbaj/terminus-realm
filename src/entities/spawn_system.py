"""
Spawning system for NPCs and monsters in the roguelike game.
"""

import random
import math
from core.ecs import EntityManager
from entities.entities import EntityFactory
from world.map import GameMap
from world.persistent_world import get_persistent_world


# Enhanced biome-specific creature types with weights
BIOME_WEIGHTS = {
    "forest": {"goblin": 40, "wolf": 30, "bear": 10, "skeleton": 10, "bat": 10},
    "dense_forest": {"giant_spider": 40, "treant": 20, "centaur": 10, "wood_elf": 30},
    "plains": {"goblin": 50, "bandit": 20, "rabbit": 15, "deer": 15},
    "grassland": {"goblin": 40, "wolf": 20, "boar": 30, "bandit": 10},
    "desert": {"skeleton": 40, "scorpion": 30, "giant_ant": 20, "desert_bandit": 10},
    "oasis_desert": {"sphinx": 5, "mummy": 40, "desert_cat": 25, "sandworm": 30},
    "mountain": {"yeti": 10, "giant": 10, "mountain_goblin": 50, "stone_golem": 30},
    "mountain_cave": {"cave_bear": 20, "giant_rat": 40, "cave_spider": 30, "mineral_slug": 10},
    "hill": {"goblin": 40, "bandit": 30, "wild_boar": 20, "hawk": 10},
    "swamp": {"giant_frog": 30, "swamp_zombie": 40, "poison_frog": 20, "swamp_moss": 10},
    "jungle": {"jaguar": 25, "poison_spider": 35, "jungle_guardian": 15, "venom_snake": 25},
    "ocean": {"piranha": 50, "sea_snake": 30, "water_elemental": 15, "kraken_spawn": 5},
    "snow": {"ice_slime": 40, "snow_wolf": 30, "yeti": 10, "ice_golem": 20},
    "volcanic": {"fire_imp": 40, "lava_golem": 20, "fire_elemental": 30, "lava_slime": 10},
    "town": {"guard": 40, "merchant": 20, "citizen": 30, "dog": 10},
}

# Monsters that typically spawn in groups
GROUP_SPAWN_CHANCE = {
    "goblin": 0.4,
    "wolf": 0.3,
    "skeleton": 0.25,
    "spider": 0.2,
    "giant_ant": 0.5,
}


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
        player_level: int = 1,
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
                    
                    # Handle group spawning
                    group_size = 1
                    if monster_type in GROUP_SPAWN_CHANCE and random.random() < GROUP_SPAWN_CHANCE[monster_type]:
                        group_size = random.randint(2, 4)
                        
                    for i in range(group_size):
                        if len(spawned) >= num_monsters:
                            break
                            
                        # Slight offset for group members
                        gx, gy = x, y
                        if i > 0:
                            gx += random.randint(-1, 1)
                            gy += random.randint(-1, 1)
                            
                        if (0 <= gx < game_map.width and 0 <= gy < game_map.height and 
                            game_map.is_walkable(gx, gy) and 
                            (not self.spatial_index or not self.spatial_index.is_occupied(gx, gy))):
                            
                            # Elite chance (3%)
                            is_elite = random.random() < 0.03
                            
                            monster_id = self.entity_factory.create_monster(
                                gx, gy, monster_type, is_elite=is_elite, player_level=player_level
                            )
                            spawned.append(monster_id)

        return spawned

    def _choose_monster_type(self, x: int = None, y: int = None) -> str:
        """Choose a monster type based on weighted spawn rates and biome."""
        if x is not None and y is not None:
            biome = self.persistent_world.get_biome(x, y)
            
            # Use BIOME_WEIGHTS if available
            if biome in BIOME_WEIGHTS:
                weights_dict = BIOME_WEIGHTS[biome]
                choices = list(weights_dict.keys())
                weights = list(weights_dict.values())
                return random.choices(choices, weights=weights)[0]
                
            # Fallback to PersistentWorld creature list
            creatures = self.persistent_world.get_creatures_for_biome(biome)
            if creatures:
                return random.choice(creatures)
                
        # Use global spawn rates as last fallback
        choices = list(self.global_spawn_rates.keys())
        weights = list(self.global_spawn_rates.values())
        return random.choices(choices, weights=weights)[0]

    def spawn_level_monsters(
        self, game_map: GameMap, chunk_x: int, chunk_y: int, num_monsters: int = 5, player_level: int = 1
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
            world_x = x
            world_y = y

            monster_type = self._choose_monster_type(world_x, world_y)
            
            # Elite chance (2% for level initial spawn)
            is_elite = random.random() < 0.02
            
            monster_id = self.entity_factory.create_monster(
                x, y, monster_type, is_elite=is_elite, player_level=player_level
            )
            spawned.append(monster_id)

        return spawned
