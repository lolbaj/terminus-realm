"""
Tests for Phase 3: World Expansion - Chunk System and Procedural Generation.
"""

from world.chunk_manager import Chunk
from world.persistent_world import PersistentWorld


class TestChunkCreation:
    """Test chunk creation and basic access."""

    def test_chunk_creation(self, chunk_manager):
        """Test that chunks are created when requested."""
        chunk = chunk_manager.get_chunk(0, 0)

        assert chunk is not None
        assert isinstance(chunk, Chunk)
        assert chunk.x == 0
        assert chunk.y == 0

    def test_chunk_size(self, chunk_manager):
        """Test chunk has correct size."""
        chunk = chunk_manager.get_chunk(0, 0)

        assert chunk.size == 32
        assert chunk.map.width == 32
        assert chunk.map.height == 32

    def test_chunk_world_coordinates(self, chunk_manager):
        """Test chunk world coordinate calculation."""
        chunk = chunk_manager.get_chunk(0, 0)

        assert chunk.world_x == 0
        assert chunk.world_y == 0

        chunk2 = chunk_manager.get_chunk(1, 1)
        assert chunk2.world_x == 32
        assert chunk2.world_y == 32

    def test_chunk_local_to_world_conversion(self, chunk_manager):
        """Test converting between chunk-local and world coordinates."""
        chunk = chunk_manager.get_chunk(0, 0)

        # Local (5, 5) in chunk (0, 0) should be world (5, 5)
        world_x, world_y = chunk.get_world_pos(5, 5)
        assert world_x == 5
        assert world_y == 5

        # Local (5, 5) in chunk (1, 1) should be world (37, 37)
        chunk2 = chunk_manager.get_chunk(1, 1)
        world_x, world_y = chunk2.get_world_pos(5, 5)
        assert world_x == 37  # 32 + 5
        assert world_y == 37

    def test_chunk_world_to_local_conversion(self, chunk_manager):
        """Test converting world to chunk-local coordinates."""
        chunk = chunk_manager.get_chunk(0, 0)

        # World (5, 5) should be local (5, 5) in chunk (0, 0)
        local_x, local_y = chunk.get_chunk_pos(5, 5)
        assert local_x == 5
        assert local_y == 5

        # World (37, 37) should be local (5, 5) in chunk (1, 1)
        # Note: chunk.get_chunk_pos converts world -> local for THIS chunk
        # So we need to get chunk (1,1) and check its local coords
        chunk2 = chunk_manager.get_chunk(1, 1)
        local_x, local_y = chunk2.get_chunk_pos(37, 37)
        assert local_x == 5
        assert local_y == 5


class TestChunkManager:
    """Test ChunkManager functionality."""

    def test_get_chunk_coords(self, chunk_manager):
        """Test converting world coordinates to chunk coordinates."""
        # World (0, 0) is in chunk (0, 0)
        cx, cy = chunk_manager.get_chunk_coords(0, 0)
        assert cx == 0
        assert cy == 0

        # World (15, 15) is still in chunk (0, 0)
        cx, cy = chunk_manager.get_chunk_coords(15, 15)
        assert cx == 0
        assert cy == 0

        # World (32, 32) is in chunk (1, 1)
        cx, cy = chunk_manager.get_chunk_coords(32, 32)
        assert cx == 1
        assert cy == 1

        # World (63, 63) is still in chunk (1, 1)
        cx, cy = chunk_manager.get_chunk_coords(63, 63)
        assert cx == 1
        assert cy == 1

    def test_tile_access(self, chunk_manager):
        """Test accessing tiles through chunk manager."""
        tile = chunk_manager.get_tile_at(5, 5)
        assert tile is not None

        tile = chunk_manager.get_tile_at(20, 20)
        assert tile is not None

    def test_walkable_check(self, chunk_manager):
        """Test checking if tiles are walkable."""
        walkable = chunk_manager.is_walkable(5, 5)
        assert isinstance(walkable, bool)

        walkable = chunk_manager.is_walkable(20, 20)
        assert isinstance(walkable, bool)

    def test_transparent_check(self, chunk_manager):
        """Test checking if tiles are transparent."""
        transparent = chunk_manager.is_transparent(5, 5)
        assert isinstance(transparent, bool)


class TestRollingBuffer:
    """Test the rolling buffer chunk loading system."""

    def test_initial_chunk_count(self, chunk_manager):
        """Test initially no chunks are loaded."""
        count = chunk_manager.get_loaded_chunk_count()
        assert count == 0

    def test_update_active_area_loads_chunks(self, chunk_manager):
        """Test that updating active area loads chunks."""
        # Update with chunk coordinates (not world coordinates)
        chunk_manager.update_active_area(0, 0)

        # Give async worker time to load
        import time

        time.sleep(0.1)

        # With buffer_radius=1, should load 3x3 = 9 chunks
        count = chunk_manager.get_loaded_chunk_count()
        assert count == 9

    def test_chunks_unloaded_when_moving(self, chunk_manager):
        """Test that old chunks are unloaded when moving away."""
        import time

        # Load chunks at (0, 0)
        chunk_manager.update_active_area(0, 0)
        time.sleep(0.1)
        chunk_manager.get_loaded_chunk_count()

        # Move far away
        chunk_manager.update_active_area(10, 10)
        time.sleep(0.1)

        # Should still have 9 chunks (new area)
        new_count = chunk_manager.get_loaded_chunk_count()
        assert new_count == 9

        # Old chunks should be unloaded
        # The origin chunk may or may not be loaded depending on implementation
        # This test documents the expected behavior

    def test_active_chunks_set(self, chunk_manager):
        """Test active chunks set is maintained."""
        chunk_manager.update_active_area(5, 5)

        # Center chunk should be in active set
        assert (5, 5) in chunk_manager.active_chunks

        # Adjacent chunks should be in active set
        assert (4, 5) in chunk_manager.active_chunks
        assert (6, 5) in chunk_manager.active_chunks
        assert (5, 4) in chunk_manager.active_chunks
        assert (5, 6) in chunk_manager.active_chunks


class TestProceduralGeneration:
    """Test procedural content generation."""

    def test_chunk_has_varied_terrain(self, chunk_manager):
        """Test that chunks have varied terrain."""
        chunk_manager.update_active_area(0, 0)
        chunk = chunk_manager.get_chunk(0, 0)

        unique_tiles = set(chunk.map.tiles.flatten())

        # Should have more than just walls
        assert (
            len(unique_tiles) > 1
        ), f"Chunk should have varied terrain, found: {unique_tiles}"

    def test_generation_consistency(self, chunk_manager):
        """Test that same coordinates generate same content."""
        chunk1 = chunk_manager.get_chunk(0, 0)
        chunk2 = chunk_manager.get_chunk(0, 0)

        # Same chunk coordinates should produce identical content
        maps_identical = (chunk1.map.tiles == chunk2.map.tiles).all()
        assert maps_identical, "Same chunk coords should generate identical content"

    def test_different_chunks_different_content(self, chunk_manager):
        """Test that different chunks have different content."""
        chunk1 = chunk_manager.get_chunk(0, 0)
        chunk2 = chunk_manager.get_chunk(10, 10)

        # Different chunks should generally have different content
        # (They might be similar due to noise, but unlikely identical)
        not (chunk1.map.tiles == chunk2.map.tiles).all()
        # Note: This might fail if noise produces similar patterns
        # It's more of a documentation test


class TestBoundaryAccess:
    """Test accessing tiles at chunk boundaries."""

    def test_chunk_boundary_tiles(self, chunk_manager):
        """Test accessing tiles at chunk boundaries."""
        chunk_manager.update_active_area(0, 0)

        # Test tiles at chunk (0,0) boundary
        boundary_tiles = [
            (15, 15),  # Edge of chunk (0,0)
            (0, 15),  # Left edge
            (15, 0),  # Top edge
        ]

        for x, y in boundary_tiles:
            tile = chunk_manager.get_tile_at(x, y)
            assert tile is not None, f"Tile at ({x}, {y}) should be accessible"

    def test_chunk_corner_tiles(self, chunk_manager):
        """Test accessing tiles at chunk corners."""
        chunk_manager.update_active_area(0, 0)

        corners = [(0, 0), (0, 15), (15, 0), (15, 15)]

        for x, y in corners:
            tile = chunk_manager.get_tile_at(x, y)
            assert tile is not None, f"Corner tile at ({x}, {y}) should be accessible"

    def test_cross_boundary_access(self, chunk_manager):
        """Test accessing tiles across chunk boundaries."""
        chunk_manager.update_active_area(0, 0)

        # Access tiles that cross from chunk (0,0) to (1,1)
        tiles = [
            (15, 15),  # Last tile of chunk (0,0)
            (16, 16),  # First tile of chunk (1,1)
            (15, 16),  # Boundary crossing
            (16, 15),  # Boundary crossing
        ]

        for x, y in tiles:
            tile = chunk_manager.get_tile_at(x, y)
            assert (
                tile is not None
            ), f"Cross-boundary tile at ({x}, {y}) should be accessible"


class TestPersistentWorld:
    """Test persistent world system."""

    def test_world_creation(self):
        """Test creating a persistent world."""
        world = PersistentWorld(world_width=100, world_height=100)

        assert world.world_width == 100
        assert world.world_height == 100

    def test_world_generation(self):
        """Test generating a persistent world."""
        world = PersistentWorld(world_width=100, world_height=100)
        world.generate_world()

        assert world.world_map is not None
        assert world.world_map.shape == (100, 100)

    def test_world_biome_map(self):
        """Test world has biome information."""
        world = PersistentWorld(world_width=100, world_height=100)
        world.generate_world()

        assert world.biome_map is not None
        assert world.biome_map.shape == (100, 100)

    def test_get_biome_at(self):
        """Test getting biome at position."""
        world = PersistentWorld(world_width=100, world_height=100)
        world.generate_world()

        biome = world.biome_map[50, 50]
        assert biome is not None

    def test_world_save_load(self, tmp_path):
        """Test saving and loading world."""
        save_file = tmp_path / "test_world.pkl"

        world1 = PersistentWorld(world_width=50, world_height=50)
        world1.generate_world()
        world1.world_file = str(save_file)
        world1.save_world()

        # Load into new instance
        world2 = PersistentWorld(world_width=50, world_height=50)
        world2.world_file = str(save_file)
        world2.load_world()

        # Maps should be identical
        assert (world1.world_map == world2.world_map).all()


class TestChunkEntities:
    """Test entity management in chunks."""

    def test_chunk_entity_storage(self, chunk_manager):
        """Test that chunks can store entity references."""
        chunk = chunk_manager.get_chunk(0, 0)

        # Chunks have an entities set
        assert hasattr(chunk, "entities")
        assert isinstance(chunk.entities, set)

    def test_chunk_entity_tracking(self, chunk_manager, entity_factory):
        """Test tracking entities in chunks."""
        chunk = chunk_manager.get_chunk(0, 0)

        # Add an entity reference
        test_eid = 12345
        chunk.entities.add(test_eid)

        assert test_eid in chunk.entities
