# World Generation & Map Management

This directory manages the physical environment of Terminus Realm.

## Modules

- **`generator.py`**: Procedural world generation using Perlin noise and cellular automata.
- **`chunk_manager.py`**: Efficient loading and unloading of map "chunks" as the player moves.
- **`map.py`**: The `GameMap` class representing the current active grid.
- **`fov.py`**: Visibility and "Field of View" calculations using recursive shadowcasting.
- **`persistent_world.py`**: Logic for saving and restoring the world state across sessions.
- **`static_maps.py`**: Support for hand-crafted maps (like towns or dungeons).

## Key Features

- **Infinite World**: The chunk manager ensures you can walk in any direction without hitting boundaries.
- **Procedural Biomes**: Different noise layers determine terrain types like forests, mountains, and plains.
- **Optimized Data**: Map data is stored in NumPy arrays for high performance.
