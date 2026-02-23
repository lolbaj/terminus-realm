"""
Basic test to verify the foundation is working.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.ecs import EntityManager
from entities.components import Position, Render, Health, Player
from entities.entities import EntityManagerWrapper
from data.loader import DATA_LOADER


def test_ecs():
    """Test the ECS system."""
    print("Testing ECS system...")

    # Create entity manager
    em = EntityManager()
    entity_wrapper = EntityManagerWrapper(em)

    # Create a player entity
    player_eid = entity_wrapper.factory.create_player(5, 5)
    print(f"Created player entity with ID: {player_eid}")

    # Verify the player has the right components
    assert em.has_component(player_eid, Position)
    assert em.has_component(player_eid, Render)
    assert em.has_component(player_eid, Health)
    assert em.has_component(player_eid, Player)

    print("Player entity has all required components")

    # Test getting the player
    retrieved_player = entity_wrapper.get_player()
    assert retrieved_player == player_eid
    print("Successfully retrieved player entity")

    # Create a monster entity
    monster_eid = entity_wrapper.factory.create_monster(10, 10, "goblin")
    print(f"Created monster entity with ID: {monster_eid}")

    # Verify the monster has the right components
    assert em.has_component(monster_eid, Position)
    assert em.has_component(monster_eid, Render)
    assert em.has_component(monster_eid, Health)

    print("Monster entity has all required components")

    print("ECS system test passed!")


def test_data_loading():
    """Test the data loading system."""
    print("\nTesting data loading system...")

    # Load item data
    potion_data = DATA_LOADER.get_item_data("health_potion")
    assert potion_data is not None
    assert potion_data["name"] == "Health Potion"
    assert potion_data["heal_amount"] == 20

    print(f"Loaded item data: {potion_data['name']}")

    # Try to load non-existent item
    fake_item = DATA_LOADER.get_item_data("non_existent_item")
    assert fake_item is None

    print("Data loading test passed!")


def main():
    """Run all tests."""
    print("Running foundation tests...\n")

    test_ecs()
    test_data_loading()

    print("\nAll foundation tests passed! ✅")


if __name__ == "__main__":
    main()
