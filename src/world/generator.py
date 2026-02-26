"""
Procedural generation system using noise algorithms.
"""

import numpy as np
import random

from world.map import (
    GameMap,
    TILE_FLOOR,
    TILE_WALL,
    TILE_WATER,
    TILE_GRASS,
    TILE_TREE,
    TILE_SAND,
    TILE_PAVEMENT,
    TILE_SNOW,
    TILE_LAVA,
    TILE_ASH,
    TILE_CACTUS,
    TILE_ICE,
    TILE_DOOR,
)
from world.static_maps import STATIC_CHUNKS


def _cellular_automata_step(grid, birth_limit, death_limit):
    """
    Perform one step of cellular automata using optimized NumPy vectorization.
    This calculates neighbor counts using array slicing, which is much faster than loops.
    """
    # Count neighbors by shifting the grid in 8 directions
    # Pad grid with 0 (walls) to handle edges easily without reducing size
    padded = np.pad(grid, 1, mode="constant", constant_values=0)

    # Sum up all 8 neighbors
    neighbors = (
        padded[0:-2, 0:-2]
        + padded[0:-2, 1:-1]
        + padded[0:-2, 2:]  # Top row
        + padded[1:-1, 0:-2]
        + padded[1:-1, 2:]  # Middle row
        + padded[2:, 0:-2]
        + padded[2:, 1:-1]
        + padded[2:, 2:]  # Bottom row
    )

    # Create new grid based on rules
    # If cell is wall (0) and neighbors > birth_limit -> become floor (1)
    # If cell is floor (1) and neighbors < death_limit -> become wall (0)

    # Start with a copy or zeros
    new_grid = grid.copy()

    # Apply Birth Rule
    # "Where (grid is wall) AND (neighbors > birth_limit), set to 1"
    birth_mask = (grid == 0) & (neighbors > birth_limit)
    new_grid[birth_mask] = 1

    # Apply Death Rule
    # "Where (grid is floor) AND (neighbors < death_limit), set to 0"
    death_mask = (grid == 1) & (neighbors < death_limit)
    new_grid[death_mask] = 0

    return new_grid


def apply_cellular_automata(
    grid: np.ndarray, birth_limit: int = 4, death_limit: int = 3, steps: int = 1
) -> np.ndarray:
    """
    Apply cellular automata rules to smooth the map.
    Optimized with NumPy vectorization.
    """
    current_grid = grid.copy()
    for _ in range(steps):
        current_grid = _cellular_automata_step(current_grid, birth_limit, death_limit)
    return current_grid


def generate_perlin_noise(
    width: int,
    height: int,
    scale: float = 10.0,
    octaves: int = 1,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
) -> np.ndarray:
    """
    Generate 2D noise. Uses 'noise' library for small maps/chunks,
    and a numpy value-noise approximation for large maps to prevent freezing.
    """
    # FAST PATH for large maps (Value Noise approximation)
    if width * height > 250000:  # e.g., > 500x500
        # print("Using fast numpy noise generation for large map") # Debug
        world = np.zeros((height, width))
        current_scale = scale
        amp = 1.0
        total_amp = 0.0

        for _ in range(octaves):
            # Generate random grid
            s_float = max(2.0, current_scale)
            s_int = int(s_float)

            grid_h = max(2, height // s_int + 1)
            grid_w = max(2, width // s_int + 1)

            low_res = np.random.random((grid_h, grid_w))

            # Upscale using bilinear interpolation (manual numpy implementation)
            y_indices = np.linspace(0, grid_h - 1, height)
            x_indices = np.linspace(0, grid_w - 1, width)

            y_low = y_indices.astype(int)
            y_high = np.minimum(y_low + 1, grid_h - 1)
            y_weight = y_indices - y_low

            x_low = x_indices.astype(int)
            x_high = np.minimum(x_low + 1, grid_w - 1)
            x_weight = x_indices - x_low

            # Interpolate rows
            row_low = low_res[y_low, :]
            row_high = low_res[y_high, :]
            interpolated_rows = (
                row_low * (1 - y_weight[:, None]) + row_high * y_weight[:, None]
            )

            # Interpolate columns
            col_low = interpolated_rows[:, x_low]
            col_high = interpolated_rows[:, x_high]
            layer = col_low * (1 - x_weight) + col_high * x_weight

            # Accumulate
            world += layer * amp
            total_amp += amp

            # Prepare next octave
            current_scale /= lacunarity
            amp *= persistence

        return world / total_amp

    # SLOW/QUALITY PATH for chunks (Perlin Noise)
    # Import noise library if available, otherwise use a simple fallback
    try:
        import noise

        world = np.zeros((height, width))

        for y in range(height):
            for x in range(width):
                amplitude = 1.0
                frequency = 1.0
                noise_height = 0.0

                for i in range(octaves):
                    sample_x = x / scale * frequency
                    sample_y = y / scale * frequency

                    perlin_value = noise.pnoise2(
                        sample_x,
                        sample_y,
                        octaves=1,
                        persistence=1.0,
                        lacunarity=1.0,
                        repeatx=width,
                        repeaty=height,
                        base=0,
                    )

                    noise_height += perlin_value * amplitude

                    amplitude *= persistence
                    frequency *= lacunarity

                world[y][x] = noise_height

        # Normalize to 0-1 range
        world = (world - np.min(world)) / (np.max(world) - np.min(world))
        return world

    except ImportError:
        # Fallback to a simple random noise if noise library is not available
        print("Warning: 'noise' library not found. Using simple random noise instead.")
        return np.random.random((height, width))


def generate_simplex_noise(width: int, height: int, scale: float = 10.0) -> np.ndarray:
    """
    Generate 2D Simplex noise as an alternative to Perlin noise.
    """
    try:
        import noise

        world = np.zeros((height, width))

        for y in range(height):
            for x in range(width):
                sample_x = x / scale
                sample_y = y / scale
                world[y][x] = noise.snoise2(sample_x, sample_y, octaves=1)

        # Normalize to 0-1 range
        world = (world - np.min(world)) / (np.max(world) - np.min(world))
        return world

    except ImportError:
        # Fallback to the same implementation as perlin noise
        return generate_perlin_noise(width, height, scale)


def generate_terrain_from_noise(
    noise_map: np.ndarray,
    water_threshold: float = 0.2,
    floor_threshold: float = 0.5,
    grass_threshold: float = 0.4,
) -> np.ndarray:
    """
    Convert noise map to terrain types.
    """
    height, width = noise_map.shape
    terrain = np.full((height, width), TILE_WALL, dtype=np.uint8)

    # Apply thresholds
    for y in range(height):
        for x in range(width):
            value = noise_map[y, x]

            if value < water_threshold:
                terrain[y, x] = TILE_WATER
            elif value < grass_threshold:
                terrain[y, x] = TILE_GRASS
            elif value < floor_threshold:
                terrain[y, x] = TILE_FLOOR

    return terrain


def generate_cave_system(
    width: int, height: int, initial_fill_prob: float = 0.45, steps: int = 4
) -> np.ndarray:
    """
    Generate a cave-like system using cellular automata.
    """
    # Create initial random grid
    grid = np.random.choice(
        [0, 1], size=(height, width), p=[initial_fill_prob, 1 - initial_fill_prob]
    )

    # Apply cellular automata to smooth
    smoothed_grid = apply_cellular_automata(grid, steps=steps)

    # Convert to tile types
    terrain = np.where(smoothed_grid == 1, TILE_FLOOR, TILE_WALL)

    return terrain.astype(np.uint8)


def generate_chunk_with_noise(
    chunk_x: int, chunk_y: int, chunk_size: int, seed: int = None
) -> GameMap:
    """
    Generate a chunk using noise algorithms.
    """
    if seed is not None:
        random.seed(seed + chunk_x * 1000 + chunk_y)
        np.random.seed(seed + chunk_x * 1000 + chunk_y)

    # Create a new game map for this chunk
    game_map = GameMap(chunk_size, chunk_size)

    # Generate noise map based on chunk coordinates for consistent generation
    noise_scale = 20.0  # Adjust for desired level of detail
    noise_map = generate_perlin_noise(
        chunk_size,
        chunk_size,
        scale=noise_scale,
        octaves=3,
        persistence=0.5,
        lacunarity=2.0,
    )

    # Apply thresholds to create terrain
    terrain = generate_terrain_from_noise(
        noise_map, water_threshold=0.3, floor_threshold=0.7
    )

    # Apply some cellular automata to smooth terrain
    # Convert to binary for cellular automata (1 for floor, 0 for wall)
    binary_map = np.where(terrain == TILE_FLOOR, 1, 0)
    smoothed_binary = apply_cellular_automata(binary_map, steps=2)

    # Convert back to tile types
    game_map.tiles = np.where(smoothed_binary == 1, TILE_FLOOR, TILE_WALL)

    # Add some water features
    for y in range(chunk_size):
        for x in range(chunk_size):
            if noise_map[y, x] < 0.25:  # More water in low-lying areas
                game_map.tiles[y, x] = TILE_WATER

    return game_map


def generate_dungeon_chunk(
    chunk_x: int, chunk_y: int, chunk_size: int, seed: int = None
) -> GameMap:
    """
    Generate a dungeon-style chunk with rooms and corridors.
    """
    if seed is not None:
        random.seed(seed + chunk_x * 1000 + chunk_y)
        np.random.seed(seed + chunk_x * 1000 + chunk_y)

    # Create a new game map for this chunk
    game_map = GameMap(chunk_size, chunk_size)

    # Generate dungeon layout
    game_map.generate_dungeon_rooms(max_rooms=8, min_size=3, max_size=6)

    return game_map


def generate_biome_chunk(
    chunk_x: int, chunk_y: int, chunk_size: int, seed: int = None
) -> GameMap:
    """
    Generate a chunk based on Rucoy-style biomes or static maps.
    """
    # Check for static manually designed chunk
    if (chunk_x, chunk_y) in STATIC_CHUNKS:
        game_map = GameMap(chunk_size, chunk_size)
        layout = STATIC_CHUNKS[(chunk_x, chunk_y)]

        for y, row in enumerate(layout):
            if y >= chunk_size:
                break
            for x, char in enumerate(row):
                if x >= chunk_size:
                    break

                # Parse legend
                if char == "#":
                    game_map.tiles[y, x] = TILE_WALL
                elif char == ".":
                    game_map.tiles[y, x] = TILE_PAVEMENT
                elif char == "+":
                    game_map.tiles[y, x] = TILE_DOOR
                elif char == "~":
                    game_map.tiles[y, x] = TILE_WATER
                elif char == ",":
                    game_map.tiles[y, x] = TILE_GRASS
                elif char == "T":
                    game_map.tiles[y, x] = TILE_TREE
                elif char == "S":
                    game_map.tiles[y, x] = TILE_SAND
                elif char == "C":
                    game_map.tiles[y, x] = TILE_CACTUS
                elif char == "^":
                    game_map.tiles[y, x] = TILE_WALL
                elif char == "=":
                    game_map.tiles[y, x] = TILE_LAVA
                elif char == "*":
                    game_map.tiles[y, x] = TILE_ICE
                else:
                    # Default to pavement for unknown chars
                    game_map.tiles[y, x] = TILE_PAVEMENT

        return game_map

    # Proceed with procedural generation for non-static chunks
    if seed is not None:
        random.seed(seed + chunk_x * 1000 + chunk_y)
        np.random.seed(seed + chunk_x * 1000 + chunk_y)

    game_map = GameMap(chunk_size, chunk_size)

    # Calculate world coordinates
    world_cx = chunk_x * chunk_size + chunk_size // 2
    world_cy = chunk_y * chunk_size + chunk_size // 2
    distance = (world_cx**2 + world_cy**2) ** 0.5

    # Determine Biome
    biome = "forest"
    if distance < 60:
        biome = "town"
    elif distance < 250:
        biome = "forest"
    elif distance < 450:
        biome = "desert"
    elif distance < 650:
        biome = "snow"
    else:
        biome = "volcanic"

    # Generate noise
    noise_map = generate_perlin_noise(
        chunk_size, chunk_size, scale=15.0, octaves=2, persistence=0.5
    )

    # Fill chunk
    for y in range(chunk_size):
        for x in range(chunk_size):
            noise_val = noise_map[y, x]

            if biome == "town":
                if noise_val > 0.7:
                    game_map.tiles[y, x] = TILE_WALL
                elif noise_val < 0.2:
                    game_map.tiles[y, x] = TILE_GRASS
                else:
                    game_map.tiles[y, x] = TILE_PAVEMENT

            elif biome == "forest":
                if noise_val < 0.25:
                    game_map.tiles[y, x] = TILE_WATER
                elif noise_val > 0.65:
                    game_map.tiles[y, x] = TILE_TREE
                else:
                    game_map.tiles[y, x] = TILE_GRASS

            elif biome == "desert":
                if noise_val < 0.1:
                    game_map.tiles[y, x] = TILE_WATER
                elif noise_val > 0.8:
                    game_map.tiles[y, x] = TILE_WALL
                elif noise_val > 0.7:
                    game_map.tiles[y, x] = TILE_CACTUS
                else:
                    game_map.tiles[y, x] = TILE_SAND

            elif biome == "snow":
                if noise_val < 0.3:
                    game_map.tiles[y, x] = TILE_ICE
                elif noise_val > 0.7:
                    game_map.tiles[y, x] = TILE_TREE
                else:
                    game_map.tiles[y, x] = TILE_SNOW

            elif biome == "volcanic":
                if noise_val < 0.3:
                    game_map.tiles[y, x] = TILE_LAVA
                elif noise_val > 0.6:
                    game_map.tiles[y, x] = TILE_WALL
                else:
                    game_map.tiles[y, x] = TILE_ASH

    return game_map
