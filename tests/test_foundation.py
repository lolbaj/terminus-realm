"""
Basic tests to verify the ECS foundation and data loading.
"""

from entities.components import Position, Render, Health, Player, Monster


class TestECS:
    """Test the Entity Component System."""

    def test_create_entity(self, entity_manager):
        """Test entity creation returns unique IDs."""
        eid1 = entity_manager.create_entity()
        eid2 = entity_manager.create_entity()

        assert eid1 != eid2, "Entity IDs should be unique"
        assert eid1 == 0, "First entity ID should be 0"
        assert eid2 == 1, "Second entity ID should be 1"

    def test_destroy_entity(self, entity_manager):
        """Test entity destruction removes all components."""
        eid = entity_manager.create_entity()
        entity_manager.add_component(eid, Position(5, 5))

        assert entity_manager.has_component(eid, Position)

        entity_manager.destroy_entity(eid)

        assert eid not in entity_manager.entities
        assert not entity_manager.has_component(eid, Position)

    def test_component_add_and_get(self, entity_manager):
        """Test adding and retrieving components."""
        eid = entity_manager.create_entity()
        position = Position(10, 20)
        entity_manager.add_component(eid, position)

        retrieved = entity_manager.get_component(eid, Position)

        assert retrieved is position
        assert retrieved.x == 10
        assert retrieved.y == 20

    def test_has_component(self, entity_manager):
        """Test checking if entity has a component."""
        eid = entity_manager.create_entity()

        assert not entity_manager.has_component(eid, Position)

        entity_manager.add_component(eid, Position(0, 0))

        assert entity_manager.has_component(eid, Position)

    def test_get_entities_with_components(self, entity_manager):
        """Test querying entities with specific components."""
        # Create entity with Position only
        eid1 = entity_manager.create_entity()
        entity_manager.add_component(eid1, Position(0, 0))

        # Create entity with Position and Health
        eid2 = entity_manager.create_entity()
        entity_manager.add_component(eid2, Position(5, 5))
        entity_manager.add_component(eid2, Health(100, 100))

        # Query for entities with Position
        pos_entities = entity_manager.get_entities_with_components(Position)
        assert len(pos_entities) == 2
        assert eid1 in pos_entities
        assert eid2 in pos_entities

        # Query for entities with Position AND Health
        both_entities = entity_manager.get_entities_with_components(Position, Health)
        assert len(both_entities) == 1
        assert eid2 in both_entities

    def test_create_player(self, entity_wrapper):
        """Test player entity creation with all required components."""
        player_eid = entity_wrapper.factory.create_player(5, 5)

        assert entity_wrapper.entity_manager.has_component(player_eid, Position)
        assert entity_wrapper.entity_manager.has_component(player_eid, Render)
        assert entity_wrapper.entity_manager.has_component(player_eid, Health)
        assert entity_wrapper.entity_manager.has_component(player_eid, Player)

    def test_get_player(self, entity_wrapper, player_entity):
        """Test retrieving the player entity."""
        retrieved = entity_wrapper.get_player()
        assert retrieved == player_entity

    def test_create_monster(self, entity_factory):
        """Test monster entity creation."""
        monster_eid = entity_factory.create_monster(10, 10, "goblin")

        # Verify components
        em = entity_factory.entity_manager
        assert em.has_component(monster_eid, Position)
        assert em.has_component(monster_eid, Render)
        assert em.has_component(monster_eid, Health)
        assert em.has_component(monster_eid, Monster)

        # Verify position
        pos = em.get_component(monster_eid, Position)
        assert pos.x == 10
        assert pos.y == 10

        # Verify monster type
        monster = em.get_component(monster_eid, Monster)
        assert monster.monster_type == "goblin"


class TestDataLoading:
    """Test the data loading system."""

    def test_load_item_data(self, data_loader):
        """Test loading item data by ID."""
        potion_data = data_loader.get_item_data("health_potion")

        assert potion_data is not None
        assert potion_data["name"] == "Health Potion"
        assert potion_data["heal_amount"] == 20

    def test_load_nonexistent_item(self, data_loader):
        """Test loading non-existent item returns None."""
        fake_item = data_loader.get_item_data("non_existent_item")
        assert fake_item is None

    def test_load_monster_data(self, data_loader):
        """Test loading monster data by ID."""
        goblin_data = data_loader.get_monster_data("goblin")

        assert goblin_data is not None
        assert goblin_data["name"] == "Goblin"
        assert goblin_data["health"] > 0
        assert goblin_data["attack"] > 0

    def test_load_tile_data(self, data_loader):
        """Test loading tile data."""
        tiles_data = data_loader.load_json("tiles")

        assert "0" in tiles_data  # Floor tile
        assert tiles_data["0"]["name"] == "floor"
        assert tiles_data["0"]["walkable"] is True

    def test_cache_is_used(self, data_loader):
        """Test that data is cached after first load."""
        # First load
        data1 = data_loader.load_json("items")

        # Second load should use cache
        data2 = data_loader.load_json("items")

        assert data1 is data2, "Cached data should be same object"


class TestPositionComponent:
    """Test Position component behavior."""

    def test_position_creation(self):
        """Test creating a Position component."""
        pos = Position(5, 10)

        assert pos.x == 5
        assert pos.y == 10
        assert pos.z == 0  # Default z

    def test_position_with_z(self):
        """Test creating a Position with z coordinate."""
        pos = Position(5, 10, 3)

        assert pos.x == 5
        assert pos.y == 10
        assert pos.z == 3


class TestHealthComponent:
    """Test Health component behavior."""

    def test_health_creation(self):
        """Test creating a Health component."""
        health = Health(100, 100)

        assert health.current == 100
        assert health.maximum == 100

    def test_health_damage(self):
        """Test applying damage to health."""
        health = Health(100, 100)
        health.current -= 25

        assert health.current == 75

    def test_health_healing(self):
        """Test healing health."""
        health = Health(50, 100)
        health.current = min(health.maximum, health.current + 30)

        assert health.current == 80
