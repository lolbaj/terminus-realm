"""
Test script to verify Loot 2.0 functionality.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.ecs import EntityManager
from entities.entities import EntityFactory
from entities.components import Item, WeaponStats, ArmorStats, Render


def test_loot_generation():
    """Test that items are generated with rarity and affixes."""
    print("Testing Loot Generation...")

    entity_manager = EntityManager()
    factory = EntityFactory(entity_manager)

    # Generate a few swords to see different rarities
    items = []
    for _ in range(50):
        eid = factory.create_item(0, 0, "sword")
        items.append(eid)

    rarity_counts = {}
    has_affixes = False

    for eid in items:
        item = entity_manager.get_component(eid, Item)
        render = entity_manager.get_component(eid, Render)

        # Check rarity
        rarity = item.rarity
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        # Check color matching rarity
        # (Simplified check, assuming RARITY_CONFIG is used)
        from entities.entities import RARITY_CONFIG

        expected_color = RARITY_CONFIG[rarity]["color"]
        assert (
            render.fg_color == expected_color
        ), f"Item {item.name} color {render.fg_color} does not match rarity {rarity} color {expected_color}"

        # Check affixes
        if item.affixes:
            has_affixes = True
            # print(f"Generated: {item.name} ({rarity}) - Affixes: {item.affixes}")

            # Verify name contains affixes
            for affix in item.affixes:
                if affix not in ["Epic Boost", "Legendary Boost"]:
                    assert (
                        affix in item.name
                    ), f"Affix {affix} should be in item name {item.name}"

        # Verify stats
        weapon_stats = entity_manager.get_component(eid, WeaponStats)
        if weapon_stats:
            # Base sword has 5 attack. Any increase must be from affixes or rarity boosts.
            if not item.affixes:
                assert (
                    weapon_stats.attack_power == 5
                ), f"Common sword should have 5 attack, got {weapon_stats.attack_power}"
            else:
                assert (
                    weapon_stats.attack_power != 5
                    or "Balanced" in item.affixes
                    or "Rusty" in item.affixes
                ), f"Affixed sword {item.name} should likely not have base 5 attack, got {weapon_stats.attack_power}"

    print(f"Rarity Distribution: {rarity_counts}")
    assert has_affixes, "Should have generated at least some items with affixes"
    assert len(rarity_counts) > 1, "Should have generated multiple rarities"

    print("✓ Loot generation with rarity and affixes is working!")


def test_armor_generation():
    """Test that armor items are generated correctly."""
    print("\nTesting Armor Generation...")

    entity_manager = EntityManager()
    factory = EntityFactory(entity_manager)

    # Generate a few shields
    for _ in range(20):
        eid = factory.create_item(0, 0, "shield")
        item = entity_manager.get_component(eid, Item)
        armor_stats = entity_manager.get_component(eid, ArmorStats)

        assert armor_stats is not None, "Shield should have ArmorStats"
        # Base shield has 3 defense
        if not item.affixes:
            assert (
                armor_stats.defense == 3
            ), f"Common shield should have 3 defense, got {armor_stats.defense}"

    print("✓ Armor generation is working!")


if __name__ == "__main__":
    test_loot_generation()
    test_armor_generation()
