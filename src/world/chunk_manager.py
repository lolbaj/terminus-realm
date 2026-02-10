"""
Chunk manager for the roguelike game.
Implements a rolling buffer system to manage world chunks efficiently.
"""

import numpy as np
from typing import Dict, Tuple, Optional, Set
from world.map import (
    TILE_WALL,
)
import random


class Chunk:
    """Represents a single chunk of the game world."""

    def __init__(
        self,
        x: int,
        y: int,
        size: int = 32,
        chunk_type: str = "mixed",
        seed: int = None,
    ):
        self.x = x  # Chunk coordinate (not world coordinate)
        self.y = y
        self.size = size
        self.world_x = x * size  # World coordinate of top-left corner
        self.world_y = y * size
        self.chunk_type = chunk_type  # "overworld", "dungeon", or "mixed"
        self.seed = seed

        # Fetch chunk from PersistentWorld
        from world.persistent_world import get_persistent_world

        persistent_world = get_persistent_world()

        # This returns a copy of the slice from the global map
        self.map = persistent_world.get_chunk(x, y, size)

        # Store entities that belong to this chunk
        self.entities: Set[int] = set()

    def get_world_pos(self, chunk_x: int, chunk_y: int) -> Tuple[int, int]:
        """Convert chunk-local coordinates to world coordinates."""
        return (self.world_x + chunk_x, self.world_y + chunk_y)

    def get_chunk_pos(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to chunk-local coordinates."""
        return (world_x - self.world_x, world_y - self.world_y)


class ChunkManager:
    """Manages world chunks with a rolling buffer system."""

    def __init__(self, chunk_size: int = 32, buffer_radius: int = 1):
        self.chunk_size = chunk_size
        self.buffer_radius = (
            buffer_radius  # 1 means 3x3 buffer (radius 1 around center)
        )
        self.loaded_chunks: Dict[Tuple[int, int], Chunk] = {}
        self.active_area: Tuple[int, int] = (0, 0)  # Center chunk of active area

        # Track which chunks are in the active area
        self.active_chunks: Set[Tuple[int, int]] = set()

    def get_chunk_coords(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to chunk coordinates."""
        chunk_x = world_x // self.chunk_size
        chunk_y = world_y // self.chunk_size
        return (chunk_x, chunk_y)

    def get_chunk(self, chunk_x: int, chunk_y: int) -> Optional[Chunk]:
        """Get a chunk by its coordinates, loading it if necessary."""
        coords = (chunk_x, chunk_y)

        if coords not in self.loaded_chunks:
            # Load the chunk
            self.loaded_chunks[coords] = Chunk(chunk_x, chunk_y, self.chunk_size)

        return self.loaded_chunks[coords]

    def get_tile_at(self, world_x: int, world_y: int):
        """Get the tile at the given world coordinates."""
        chunk_x, chunk_y = self.get_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)

        if chunk:
            # Convert world coordinates to chunk-local coordinates
            local_x = world_x - chunk.world_x
            local_y = world_y - chunk.world_y

            # Access the tile in the chunk's map
            if 0 <= local_x < chunk.map.width and 0 <= local_y < chunk.map.height:
                return chunk.map.tiles[local_y, local_x]

        # Return a default wall tile if coordinates are out of bounds

        return TILE_WALL

    def is_walkable(self, world_x: int, world_y: int) -> bool:
        """Check if a world position is walkable."""
        chunk_x, chunk_y = self.get_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)

        if chunk:
            local_x = world_x - chunk.world_x
            local_y = world_y - chunk.world_y

            if 0 <= local_x < chunk.map.width and 0 <= local_y < chunk.map.height:
                return chunk.map.is_walkable(local_x, local_y)

        return False

    def is_transparent(self, world_x: int, world_y: int) -> bool:
        """Check if a world position is transparent."""
        chunk_x, chunk_y = self.get_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)

        if chunk:
            local_x = world_x - chunk.world_x
            local_y = world_y - chunk.world_y

            if 0 <= local_x < chunk.map.width and 0 <= local_y < chunk.map.height:
                return chunk.map.is_transparent(local_x, local_y)

        return False

    def update_active_area(self, center_chunk_x: int, center_chunk_y: int):
        """Update the active area around the given center chunk."""
        # Remember old active chunks to unload them later
        old_active_chunks = self.active_chunks.copy()

        # Calculate new active chunks based on buffer radius
        self.active_chunks = set()
        for dx in range(-self.buffer_radius, self.buffer_radius + 1):
            for dy in range(-self.buffer_radius, self.buffer_radius + 1):
                chunk_coords = (center_chunk_x + dx, center_chunk_y + dy)
                self.active_chunks.add(chunk_coords)

                # Ensure the chunk is loaded
                if chunk_coords not in self.loaded_chunks:
                    self.loaded_chunks[chunk_coords] = Chunk(
                        chunk_coords[0], chunk_coords[1], self.chunk_size
                    )

        # Unload chunks that are no longer in the active area
        chunks_to_unload = old_active_chunks - self.active_chunks
        for chunk_coords in chunks_to_unload:
            if chunk_coords in self.loaded_chunks:
                del self.loaded_chunks[chunk_coords]

        self.active_area = (center_chunk_x, center_chunk_y)

    def move_active_area(self, dx: int, dy: int):
        """Move the active area by the given chunk offsets."""
        new_center_x = self.active_area[0] + dx
        new_center_y = self.active_area[1] + dy
        self.update_active_area(new_center_x, new_center_y)

    def get_loaded_chunk_count(self) -> int:
        """Get the number of currently loaded chunks."""
        return len(self.loaded_chunks)

    def get_tile_char(self, world_x: int, world_y: int, visible: bool = True):
        """Get the character representation of a tile at world coordinates."""
        chunk_x, chunk_y = self.get_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)

        if chunk:
            local_x = world_x - chunk.world_x
            local_y = world_y - chunk.world_y

            if 0 <= local_x < chunk.map.width and 0 <= local_y < chunk.map.height:
                return chunk.map.get_tile_char(local_x, local_y, visible)

        return " "

    def get_tile_fg_color(self, world_x: int, world_y: int, visible: bool = True):
        """Get the foreground color of a tile at world coordinates."""
        chunk_x, chunk_y = self.get_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)

        if chunk:
            local_x = world_x - chunk.world_x
            local_y = world_y - chunk.world_y

            if 0 <= local_x < chunk.map.width and 0 <= local_y < chunk.map.height:
                return chunk.map.get_tile_fg_color(local_x, local_y, visible)

        return (0, 0, 0)


def create_world_generator(seed: Optional[int] = None):
    """Create a world generator with the given seed."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    return ChunkManager()
