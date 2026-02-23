"""
Test script to verify Equipment system and stats application.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from core.engine import GameEngine
from entities.components import (
    Equipment,
    WeaponStats,
    ArmorStats,
    Inventory,
    Health,
    Position,
)
from entities.entities import EntityFactory


def test_equipment_stats():
    """Test that equipping items affects combat stats."""
    print("Testing Equipment Stats...")

    engine = GameEngine()
    engine.initialize_game()

    player_id = engine.player_id
    factory = EntityFactory(engine.entity_manager)

    # 1. Create a strong sword
    sword_id = factory.create_item(0, 0, "sword")
    weapon_stats = engine.entity_manager.get_component(sword_id, WeaponStats)
    # Buff it to be sure
    weapon_stats.attack_power = 50

    # 2. Equip it manually (simulating what use_inventory_item does)
    equip = engine.entity_manager.get_component(player_id, Equipment)
    equip.weapon = sword_id
    equip.weapon_type = weapon_stats.weapon_type

    # 3. Create a dummy monster with high HP
    monster_id = factory.create_monster(0, 0)
    monster_health = engine.entity_manager.get_component(monster_id, Health)
    monster_health.maximum = 1000
    monster_health.current = 1000

    monster_health_before = monster_health.current

    # Force combat
    engine.handle_combat(player_id, monster_id)

    monster_health_comp = engine.entity_manager.get_component(monster_id, Health)

    if monster_health_comp is None:
        print("Monster died (Entity destroyed). Damage was sufficient.")
        damage_dealt = monster_health_before  # At least this much
    else:
        monster_health_after = monster_health_comp.current
        damage_dealt = monster_health_before - monster_health_after

    print(f"Dealt {damage_dealt} damage with 50 atk sword.")

    # Base skills are 5. Weapon is 50. Defense is 0.
    # Damage = 55 - (0//2) + variance(-1, 2) = 54 to 57.
    assert (
        damage_dealt >= 50
    ), f"Damage {damage_dealt} should be high (>= 50) with 50 atk sword"

    print("✓ Weapon stats correctly applied to damage.")


def test_armor_defense():
    """Test that equipping armor reduces damage."""
    print("\nTesting Armor Defense...")

    engine = GameEngine()
    engine.initialize_game()

    player_id = engine.player_id
    factory = EntityFactory(engine.entity_manager)

    # 1. Equip heavy armor on player
    shield_id = factory.create_item(0, 0, "shield")
    armor_stats = engine.entity_manager.get_component(shield_id, ArmorStats)
    armor_stats.defense = 50  # Massive defense

    equip = engine.entity_manager.get_component(player_id, Equipment)
    equip.armor = shield_id

    # 2. Create monster
    monster_id = factory.create_monster(0, 0)

    player_health_before = engine.entity_manager.get_component(
        player_id, Health
    ).current

    # Monster attacks player
    engine.handle_combat(monster_id, player_id)

    player_health_after = engine.entity_manager.get_component(player_id, Health).current
    damage_taken = player_health_before - player_health_after

    print(f"Took {damage_taken} damage with 50 def armor.")

    # Monster Atk 3. Player Def 50.
    # Damage = 3 - (50//2) + var = 3 - 25 = -22 -> 0.
    assert (
        damage_taken == 0
    ), f"Damage {damage_taken} should be 0 with 50 def armor against weak monster"

    print("✓ Armor stats correctly reduce damage.")


def test_inventory_equip_logic():
    """Test the use_inventory_item method for equipping."""
    print("\nTesting Inventory Equip Logic...")

    engine = GameEngine()
    engine.initialize_game()
    player_id = engine.player_id

    factory = EntityFactory(engine.entity_manager)

    # Give player a sword in inventory
    new_sword_id = factory.create_item(0, 0, "sword")
    engine.entity_manager.remove_component(new_sword_id, Position)  # Picked up

    inv = engine.entity_manager.get_component(player_id, Inventory)
    inv.items.append(new_sword_id)

    # Select it
    # Note: selection index needs to point to the new item.
    # The player starts with empty inventory in create_player (wait, I modified create_player to equip items, but inventory starts empty).
    # Check create_player:
    # self.entity_manager.add_component(eid, Inventory(capacity=20, items=[]))
    # So the new sword is at index 0.

    engine.inventory_selection = 0

    # Use it
    engine.use_inventory_item()

    # Check if equipped
    equip = engine.entity_manager.get_component(player_id, Equipment)
    assert equip.weapon == new_sword_id, "New sword should be equipped"
    assert new_sword_id not in inv.items, "New sword should be removed from inventory"

    # Check if old weapon (starting gear) is in inventory
    # The starting gear was equipped in create_player.
    # So when we equip new sword, old one should go to inventory.
    assert len(inv.items) > 0, "Old weapon should be returned to inventory"

    print("✓ Inventory equip/swap logic works.")


if __name__ == "__main__":
    test_equipment_stats()
    test_armor_defense()
    test_inventory_equip_logic()
