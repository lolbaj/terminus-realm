"""
Persistent world generation system for the roguelike game.
Generates a large persistent world once and saves it for consistent loading.
"""

import numpy as np
import pickle
import os
from typing import Dict, Tuple, List, Optional
from config import CONFIG
from world.map import (
    GameMap,
    TILE_WALL,
    TILE_WATER,
    TILE_GRASS,
    TILE_TREE,
    TILE_PAVEMENT,
    TILE_DOOR,
    TILE_SAND,
    TILE_CACTUS,
    TILE_LAVA,
    TILE_ICE,
    TILE_ASH,
    TILE_STAIRS_DOWN,
    TILE_STAIRS_UP,
)
from world.generator import (
    generate_perlin_noise,
)
from world.static_maps import STATIC_CHUNKS


class WorldArea:
    """Represents a specific area of the world with its characteristics."""

    def __init__(
        self, x: int, y: int, width: int, height: int, area_type: str = "wilderness"
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.area_type = (
            area_type  # "town", "forest", "desert", "mountain", "dungeon", etc.
        )
        self.map: Optional[GameMap] = None
        self.biome = "temperate"  # Default biome
        self.features = []  # Special features in this area


# Define biome-specific creature types
BIOME_CREATURES = {
    "forest": ["goblin", "elf", "wolf", "bear"],
    "dense_forest": ["giant_spider", "treant", "centaur", "wood_elf"],
    "plains": ["goblin", "bandit", "rabbit", "deer"],
    "grassland": ["goblin", "wolf", "boar", "bandit"],
    "desert": ["skeleton", "scorpion", "giant_ant", "desert_bandit"],
    "oasis_desert": ["sphinx", "mummy", "desert_cat", "sandworm"],
    "mountain": ["yeti", "giant", "mountain_goblin", "stone_golem"],
    "mountain_cave": ["cave_bear", "giant_rat", "cave_spider", "mineral_slug"],
    "hill": ["goblin", "bandit", "wild_boar", "hawk"],
    "swamp": ["giant_frog", "swamp_zombie", "poison_frog", "swamp_moss"],
    "jungle": ["jaguar", "poison_spider", "jungle_guardian", "venom_snake"],
    "ocean": ["piranha", "sea_snake", "water_elemental", "kraken_spawn"],
    "snow": ["ice_slime", "snow_wolf", "yeti", "ice_golem"],
    "volcanic": ["fire_imp", "lava_golem", "fire_elemental", "lava_slime"],
    "town": [
        "guard",
        "merchant",
        "citizen",
        "dog",
    ],  # NPCs rather than hostile creatures
}


class PersistentWorld:
    """Manages a large persistent world that is generated once and reused."""

    def __init__(
        self,
        world_seed: int = 12345,
        world_width: int = CONFIG.world_width,
        world_height: int = CONFIG.world_height,
    ):
        self.world_seed = world_seed
        self.world_width = world_width
        self.world_height = world_height
        self.center_x = self.world_width // 2
        self.center_y = self.world_height // 2
        self.areas: Dict[Tuple[int, int], WorldArea] = {}
        self.world_map: Optional[np.ndarray] = None
        self.biome_map: Optional[np.ndarray] = None
        self.area_map: Optional[np.ndarray] = None  # Maps each tile to its area type
        self.world_file = "src/data/saves/persistent_world.pkl"

        # Entity data from static maps
        self.preplaced_entities: List[Dict] = []

        # Player start position from static maps
        self.player_start_pos: Optional[Tuple[int, int]] = None

        # Create saves directory if it doesn't exist
        os.makedirs(os.path.dirname(self.world_file), exist_ok=True)

    def generate_world(self):
        """Generate the entire persistent world."""
        print("Generating persistent world...")

        # Set the seed for reproducible generation
        np.random.seed(self.world_seed)

        # Generate the base world map using noise
        elevation_map = generate_perlin_noise(
            self.world_width, self.world_height, scale=50.0, octaves=4
        )
        moisture_map = generate_perlin_noise(
            self.world_width, self.world_height, scale=40.0, octaves=3
        )

        # Create the main world map based on elevation and moisture
        self.world_map = np.full(
            (self.world_height, self.world_width), TILE_WALL, dtype=np.uint8
        )

        # Assign biomes based on elevation and moisture
        self.biome_map = np.full(
            (self.world_height, self.world_width), "void", dtype=object
        )

        # Vectorized Biome Assignment (Optimized for speed)

        # 1. Water (Ocean)
        mask_water = elevation_map < 0.2
        self.world_map[mask_water] = TILE_WATER
        self.biome_map[mask_water] = "ocean"

        # Land mask (everything else)
        mask_land = ~mask_water

        # 2. Low Elevation (0.2 <= elev < 0.3)
        mask_low = mask_land & (elevation_map < 0.3)

        # Low - Desert
        mask_low_desert = mask_low & (moisture_map < 0.3)
        self.world_map[mask_low_desert] = TILE_GRASS
        self.biome_map[mask_low_desert] = "desert"

        # Low - Plains
        mask_low_plains = mask_low & (moisture_map >= 0.3) & (moisture_map < 0.6)
        self.world_map[mask_low_plains] = TILE_GRASS
        self.biome_map[mask_low_plains] = "plains"

        # Low - Swamp
        mask_low_swamp = mask_low & (moisture_map >= 0.6)
        self.world_map[mask_low_swamp] = TILE_GRASS
        self.biome_map[mask_low_swamp] = "swamp"

        # 3. Mid Elevation (0.3 <= elev < 0.7)
        mask_mid = mask_land & (elevation_map >= 0.3) & (elevation_map < 0.7)

        # Mid - Grassland
        mask_mid_grassland = mask_mid & (moisture_map < 0.3)
        self.world_map[mask_mid_grassland] = TILE_GRASS
        self.biome_map[mask_mid_grassland] = "grassland"

        # Mid - Forest
        mask_mid_forest = mask_mid & (moisture_map >= 0.3) & (moisture_map < 0.6)
        self.world_map[mask_mid_forest] = TILE_GRASS
        self.biome_map[mask_mid_forest] = "forest"

        # Forest Trees (10% chance)
        # Create random mask for trees within forest
        tree_chance = np.random.random((self.world_height, self.world_width))
        mask_trees = mask_mid_forest & (tree_chance < 0.1)
        self.world_map[mask_trees] = TILE_TREE

        # Mid - Jungle
        mask_mid_jungle = mask_mid & (moisture_map >= 0.6)
        self.world_map[mask_mid_jungle] = TILE_GRASS
        self.biome_map[mask_mid_jungle] = "jungle"

        # 4. High Elevation (elev >= 0.7)
        mask_high = mask_land & (elevation_map >= 0.7)

        # High - Mountain
        mask_high_mountain = mask_high & (moisture_map < 0.5)
        self.world_map[mask_high_mountain] = TILE_WALL
        self.biome_map[mask_high_mountain] = "mountain"

        # High - Hill
        mask_high_hill = mask_high & (moisture_map >= 0.5)
        self.world_map[mask_high_hill] = TILE_GRASS
        self.biome_map[mask_high_hill] = "hill"

        # Define special areas (towns, dungeons, etc.)
        self._define_special_areas(elevation_map, moisture_map)

        # Apply STATIC_CHUNKS (overwriting procedural generation)
        chunk_size = 50  # Fixed size for static chunks
        self.preplaced_entities = []

        # Legend mapping for static chunks
        char_map = {
            "#": TILE_WALL,
            ".": TILE_PAVEMENT,
            "+": TILE_DOOR,
            "~": TILE_WATER,
            ",": TILE_GRASS,
            "T": TILE_TREE,
            "S": TILE_SAND,
            "C": TILE_CACTUS,
            "^": TILE_WALL,
            "=": TILE_LAVA,
            "*": TILE_ICE,
            "I": TILE_ICE,
            "P": TILE_PAVEMENT,
            "A": TILE_ASH,
            ">": TILE_STAIRS_DOWN,
            "<": TILE_STAIRS_UP,
        }
        
        # Entity char mapping
        entity_map = {
            "g": ("monster", "goblin"), "o": ("monster", "orc"), "k": ("monster", "skeleton"),
            "r": ("monster", "spider"), "b": ("monster", "bat"), "U": ("monster", "guard"),
            "m": ("monster", "merchant"), "h": ("monster", "citizen"), "d": ("monster", "dog"),
            "w": ("monster", "wolf"), "E": ("monster", "bear"), "q": ("monster", "scorpion"),
            "n": ("monster", "giant_ant"), "j": ("monster", "ice_slime"), "y": ("monster", "yeti"),
            "p": ("monster", "fire_imp"), "v": ("monster", "lava_golem"),
            "!": ("item", "health_potion"), "/": ("item", "sword"), "[": ("item", "shield"),
            "(": ("item", "iron_helmet"), ")": ("item", "leather_helmet"),
            "{": ("item", "iron_chainmail"), "}": ("item", "leather_tunic"),
            "_": ("item", "iron_greaves"), "-": ("item", "leather_boots"),
        }

        for (cx, cy), map_data in STATIC_CHUNKS.items():
            layout, fg_layout = map_data if isinstance(map_data, tuple) else (map_data, None)
            
            start_x = cx * chunk_size + self.center_x
            start_y = cy * chunk_size + self.center_y

            # 1. Process Background Tiles
            for r, row in enumerate(layout):
                for c, char in enumerate(row):
                    wx = start_x + c
                    wy = start_y + r

                    if 0 <= wx < self.world_width and 0 <= wy < self.world_height:
                        # Handle Player Start
                        if char == "@":
                            self.player_start_pos = (wx, wy)
                            char = "."  # Treat as floor

                        # Set biome to town for town-like tiles, or special biomes
                        if char in ("#", ".", "+", "P"):
                            self.biome_map[wy, wx] = "town"
                        elif char == "S":
                            self.biome_map[wy, wx] = "desert"
                        elif char == "I" or char == "*":
                            self.biome_map[wy, wx] = "snow"
                        elif char == "=" or char == "A":
                            self.biome_map[wy, wx] = "volcanic"

                        # Set tile type
                        tile_type = char_map.get(char, TILE_PAVEMENT)
                        self.world_map[wy, wx] = tile_type
            
            # 2. Process Foreground Entities
            if fg_layout:
                for r, row in enumerate(fg_layout):
                    for c, char in enumerate(row):
                        if char in entity_map:
                            wx, wy = start_x + c, start_y + r
                            e_type, e_subtype = entity_map[char]
                            self.preplaced_entities.append({
                                "type": e_type,
                                "subtype": e_subtype,
                                "x": wx,
                                "y": wy
                            })
                # Save the world to file
        self.save_world()
        print(
            f"Persistent world generated and saved! Size: {self.world_width}x{self.world_height}"
        )

    def _define_special_areas(
        self, elevation_map: np.ndarray, moisture_map: np.ndarray
    ):
        """Define special areas like towns, dungeons, etc. Optimized for speed."""
        # Adjust sampling step based on world size
        step = max(5, self.world_width // 100)

        # 1. Find suitable locations for a town (flat, moderate moisture)
        suitable_spots = []
        for y in range(20, self.world_height - 20, step):
            for x in range(20, self.world_width - 20, step):
                elev = elevation_map[y, x]
                moist = moisture_map[y, x]

                # Flatness and climate check
                if (0.3 < elev < 0.6) and (0.3 < moist < 0.7):
                    # Coarse flatness check (4 neighbors)
                    if (
                        abs(elevation_map[y - 2, x] - elev) < 0.1
                        and abs(elevation_map[y + 2, x] - elev) < 0.1
                        and abs(elevation_map[y, x - 2] - elev) < 0.1
                        and abs(elevation_map[y, x + 2] - elev) < 0.1
                    ):
                        suitable_spots.append((x, y))

        town_count = 0
        if suitable_spots:
            # Pick a few random spots from the suitable ones
            num_towns = min(5, len(suitable_spots))
            indices = np.random.choice(len(suitable_spots), num_towns, replace=False)
            for idx in indices:
                tx, ty = suitable_spots[idx]
                town_area = WorldArea(tx - 15, ty - 15, 30, 30, "town")
                town_area.biome = "town"
                self.areas[(tx - 15, ty - 15)] = town_area
                town_count += 1

        # 2. Define other special areas using a much larger step for speed
        area_step = step * 4
        dungeon_count = 0
        forest_count = 0
        desert_count = 0

        for y in range(30, self.world_height - 30, area_step):
            for x in range(30, self.world_width - 30, area_step):
                elev = elevation_map[y, x]
                moist = moisture_map[y, x]

                # Already in an area?
                if self.get_area_at(x, y):
                    continue

                if elev > 0.75 and np.random.random() < 0.2:
                    self.areas[(x - 10, y - 10)] = WorldArea(
                        x - 10, y - 10, 20, 20, "dungeon"
                    )
                    self.areas[(x - 10, y - 10)].biome = "mountain_cave"
                    # Place Dungeon Entrance
                    self.world_map[y, x] = TILE_STAIRS_DOWN
                    dungeon_count += 1
                elif moist > 0.6 and elev < 0.7 and np.random.random() < 0.15:
                    self.areas[(x - 15, y - 15)] = WorldArea(
                        x - 15, y - 15, 30, 30, "forest"
                    )
                    self.areas[(x - 15, y - 15)].biome = "dense_forest"
                    forest_count += 1
                elif moist < 0.25 and elev < 0.5 and np.random.random() < 0.15:
                    self.areas[(x - 15, y - 15)] = WorldArea(
                        x - 15, y - 15, 30, 30, "desert"
                    )
                    self.areas[(x - 15, y - 15)].biome = "oasis_desert"
                    desert_count += 1

        print(
            f"Defined {town_count} towns, {dungeon_count} dungeons, {forest_count} forests, and {desert_count} deserts"
        )

    def load_world(self):
        """Load the persistent world from file, or generate if it doesn't exist."""
        if os.path.exists(self.world_file):
            print("Loading persistent world from file...")
            try:
                with open(self.world_file, "rb") as f:
                    data = pickle.load(f)

                # Check if dimensions match configuration
                if (
                    data["world_width"] != self.world_width
                    or data["world_height"] != self.world_height
                ):
                    print("World dimensions changed in config. Regenerating world...")
                    self.generate_world()
                else:
                    self.world_map = data["world_map"]
                    self.biome_map = data["biome_map"]
                    self.areas = data["areas"]
                    self.world_width = data["world_width"]
                    self.world_height = data["world_height"]
                    self.player_start_pos = data.get("player_start_pos")
                    self.preplaced_entities = data.get("preplaced_entities", [])
                    self.center_x = self.world_width // 2
                    self.center_y = self.world_height // 2
                    print(
                        f"World loaded successfully! Size: {self.world_width}x{self.world_height}"
                    )
            except Exception as e:
                print(f"Error loading world: {e}. Regenerating...")
                self.generate_world()
        else:
            print("World file not found, generating new persistent world...")
            self.generate_world()

    def save_world(self):
        """Save the persistent world to file."""
        data = {
            "world_map": self.world_map,
            "biome_map": self.biome_map,
            "areas": self.areas,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "world_seed": self.world_seed,
            "player_start_pos": self.player_start_pos,
            "preplaced_entities": self.preplaced_entities,
        }
        with open(self.world_file, "wb") as f:
            pickle.dump(data, f)
        print("World saved to file.")

    def get_tile(self, x: int, y: int):
        """Get the tile type at the given coordinates."""
        if 0 <= x < self.world_width and 0 <= y < self.world_height:
            return self.world_map[y, x]
        return TILE_WALL  # Return wall for out of bounds

    def get_biome(self, x: int, y: int) -> str:
        """Get the biome at the given coordinates."""
        if 0 <= x < self.world_width and 0 <= y < self.world_height:
            return self.biome_map[y, x]
        return "void"

    def get_area_at(self, x: int, y: int) -> Optional[WorldArea]:
        """Get the special area at the given coordinates, if any."""
        for (ax, ay), area in self.areas.items():
            if ax <= x < ax + area.width and ay <= y < ay + area.height:
                return area
        return None

    def get_chunk(self, chunk_x: int, chunk_y: int, chunk_size: int = 32) -> GameMap:
        """Get a chunk of the world as a GameMap. Optimized with NumPy slicing."""
        # Calculate the actual world coordinates for this chunk
        # Apply offset so (0,0) is at the center of the world
        world_start_x = chunk_x * chunk_size + self.center_x
        world_start_y = chunk_y * chunk_size + self.center_y

        # Create a new GameMap for this chunk
        chunk_map = GameMap(chunk_size, chunk_size)

        # Calculate intersection with world bounds
        wsx = max(0, world_start_x)
        wex = min(self.world_width, world_start_x + chunk_size)
        wsy = max(0, world_start_y)
        wey = min(self.world_height, world_start_y + chunk_size)

        # Check if there is any overlap
        if wex > wsx and wey > wsy:
            # Calculate corresponding coordinates in the chunk map
            csx = wsx - world_start_x
            cex = csx + (wex - wsx)
            csy = wsy - world_start_y
            cey = csy + (wey - wsy)

            # Slice copy (Fast!)
            chunk_map.tiles[csy:cey, csx:cex] = self.world_map[wsy:wey, wsx:wex]

        return chunk_map

    def get_full_game_map(self) -> GameMap:
        """Get the entire world as a single GameMap for seamless play."""
        # Instantiate with direct reference to world_map to avoid allocation
        game_map = GameMap(self.world_width, self.world_height, tiles=self.world_map)

        # Initialize explored status based on some logic if needed?
        # For now, it defaults to False (Hidden)

        return game_map

    def get_creatures_for_biome(self, biome: str) -> List[str]:
        """Get a list of creatures that spawn in the given biome."""
        return BIOME_CREATURES.get(
            biome, ["goblin", "bat"]
        )  # Default creatures if biome not found


def get_persistent_world() -> PersistentWorld:
    """Get the singleton persistent world instance."""
    if not hasattr(get_persistent_world, "_instance"):
        get_persistent_world._instance = PersistentWorld()
        get_persistent_world._instance.load_world()
    return get_persistent_world._instance
