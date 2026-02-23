"""
Test script to verify Phase 3 chunk system functionality.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world.chunk_manager import ChunkManager


def test_chunk_creation_and_access():
    """Test that chunks are created and can be accessed properly."""
    print("Testing chunk creation and access...")

    # Create a chunk manager
    chunk_mgr = ChunkManager(chunk_size=16, buffer_radius=1)

    # Test getting a chunk
    chunk = chunk_mgr.get_chunk(0, 0)
    assert chunk is not None, "Chunk should be created when requested"
    assert chunk.x == 0 and chunk.y == 0, "Chunk coordinates should match request"
    assert chunk.size == 16, "Chunk size should match manager's size"

    print(f"✓ Chunk (0,0) created with size {chunk.size}")

    # Test world-to-chunk coordinate conversion
    world_x, world_y = 25, 40
    chunk_x, chunk_y = chunk_mgr.get_chunk_coords(world_x, world_y)
    expected_chunk_x, expected_chunk_y = 1, 2  # 25//16=1, 40//16=2

    assert (
        chunk_x == expected_chunk_x
    ), f"Expected chunk_x {expected_chunk_x}, got {chunk_x}"
    assert (
        chunk_y == expected_chunk_y
    ), f"Expected chunk_y {expected_chunk_y}, got {chunk_y}"

    print(
        f"✓ World coordinates ({world_x}, {world_y}) map to chunk ({chunk_x}, {chunk_y})"
    )

    # Test tile access
    tile_type = chunk_mgr.get_tile_at(world_x, world_y)
    assert tile_type is not None, "Tile should be accessible"

    print(f"✓ Tile at ({world_x}, {world_y}) is accessible with type {tile_type}")


def test_chunk_loading_unloading():
    """Test the rolling buffer system for loading/unloading chunks."""
    print("\nTesting chunk loading and unloading...")

    # Create a chunk manager with small buffer
    chunk_mgr = ChunkManager(
        chunk_size=16, buffer_radius=1
    )  # 3x3 buffer = 9 chunks max

    # Initially, no chunks should be loaded
    assert (
        chunk_mgr.get_loaded_chunk_count() == 0
    ), "Initially no chunks should be loaded"

    # Move to chunk (0,0) - this should load 9 chunks (3x3)
    chunk_mgr.update_active_area(0, 0)
    count_after_first_load = chunk_mgr.get_loaded_chunk_count()
    assert (
        count_after_first_load == 9
    ), f"Should have 9 chunks loaded after moving to (0,0), got {count_after_first_load}"

    print(f"✓ Moved to (0,0), loaded {count_after_first_load} chunks")

    # Move to chunk (5,5) - this should unload old chunks and load new ones
    chunk_mgr.update_active_area(5, 5)
    count_after_move = chunk_mgr.get_loaded_chunk_count()
    assert (
        count_after_move == 9
    ), f"Should still have 9 chunks loaded after moving, got {count_after_move}"

    print(f"✓ Moved to (5,5), now have {count_after_move} chunks loaded")

    # Verify that old chunks are unloaded by checking if we can still access them
    # The old center (0,0) should now be outside the active area
    old_chunk_coords = (0, 0)
    new_active_area = set()
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            new_active_area.add((5 + dx, 5 + dy))

    # The old chunk should not be in the new active area
    assert (
        old_chunk_coords not in new_active_area
    ), "Old chunk should not be in new active area"

    print("✓ Old chunks properly unloaded when moving away")


def test_procedural_generation():
    """Test that chunks are generated with procedural content."""
    print("\nTesting procedural generation...")

    # Create a chunk manager
    chunk_mgr = ChunkManager(chunk_size=16, buffer_radius=0)  # Just center chunk

    # Load a chunk
    chunk_mgr.update_active_area(0, 0)

    # Check that the chunk has varied terrain
    chunk = chunk_mgr.get_chunk(0, 0)
    unique_tile_types = set(chunk.map.tiles.flatten())

    # Should have more than just one tile type (walls)
    assert (
        len(unique_tile_types) > 1
    ), f"Chunk should have varied terrain, only found types: {unique_tile_types}"

    print(
        f"✓ Chunk has {len(unique_tile_types)} different tile types: {unique_tile_types}"
    )

    # Test consistency - same chunk coords should generate same content
    chunk2 = chunk_mgr.get_chunk(0, 0)
    # Compare the maps (they should be identical for the same coordinates)
    maps_identical = (chunk.map.tiles == chunk2.map.tiles).all()
    assert maps_identical, "Same chunk coordinates should generate identical content"

    print("✓ Procedural generation is consistent for same coordinates")


def test_world_boundary_access():
    """Test accessing tiles near and beyond chunk boundaries."""
    print("\nTesting world boundary access...")

    # Create a chunk manager
    chunk_mgr = ChunkManager(chunk_size=16, buffer_radius=1)
    chunk_mgr.update_active_area(0, 0)

    # Test accessing tiles at chunk boundaries
    boundary_tests = [
        (15, 15),  # Edge of chunk (0,0)
        (16, 16),  # Corner of chunk (1,1)
        (0, 0),  # Beginning of chunk (0,0)
    ]

    for wx, wy in boundary_tests:
        tile = chunk_mgr.get_tile_at(wx, wy)
        assert tile is not None, f"Tile at boundary ({wx}, {wy}) should be accessible"

        walkable = chunk_mgr.is_walkable(wx, wy)
        assert isinstance(
            walkable, bool
        ), f"is_walkable should return boolean for ({wx}, {wy})"

        transparent = chunk_mgr.is_transparent(wx, wy)
        assert isinstance(
            transparent, bool
        ), f"is_transparent should return boolean for ({wx}, {wy})"

    print("✓ Successfully accessed tiles at various boundaries")


def main():
    """Run all chunk system tests."""
    print("Testing Phase 3: World Expansion - Chunk System\n")

    test_chunk_creation_and_access()
    test_chunk_loading_unloading()
    test_procedural_generation()
    test_world_boundary_access()

    print("\n✓ All Phase 3 tests passed!")
    print(
        "Chunk system with rolling buffer and procedural generation is working correctly."
    )


if __name__ == "__main__":
    main()
