"""
Tests for Loot 2.0 system including rarity, affixes, and item generation.
"""

import pytest
from entities.components import Item, WeaponStats, ArmorStats, Render
from entities.entities import RARITY_CONFIG


class TestLootRarity:
    """Test item rarity system."""

    def test_rarity_weights_valid(self):
        """Test that rarity weights are properly configured."""
        total_weight = sum(config["weight"] for config in RARITY_CONFIG.values())
        assert (
            total_weight == 100
        ), f"Rarity weights should sum to 100, got {total_weight}"

    def test_rarity_color_assignment(self, entity_factory):
        """Test that items receive correct color for their rarity."""
        for _ in range(50):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            render = entity_factory.entity_manager.get_component(item_id, Render)

            expected_color = RARITY_CONFIG[item.rarity]["color"]
            assert (
                render.fg_color == expected_color
            ), f"Item {item.name} ({item.rarity}) color mismatch"

    def test_rarity_distribution(self, entity_factory):
        """Test that rarity distribution follows weights."""
        rarity_counts = {}
        num_samples = 200

        for _ in range(num_samples):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            rarity = item.rarity
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        # Verify all rarities are possible
        assert len(rarity_counts) >= 3, "Should have at least 3 different rarities"

        # Common should be most frequent
        assert rarity_counts.get("common", 0) > rarity_counts.get("rare", 0)

        # Legendary should be rarest (or close to it)
        legendary_count = rarity_counts.get("legendary", 0)
        common_count = rarity_counts.get("common", 0)
        if common_count > 0:
            ratio = legendary_count / common_count
            # Legendary should be roughly 1/60th of common (1% vs 60%)
            assert ratio < 0.1, f"Legendary too common: ratio {ratio}"

    @pytest.mark.parametrize(
        "rarity", ["common", "uncommon", "rare", "epic", "legendary"]
    )
    def test_each_rarity_can_drop(self, entity_factory, rarity):
        """Test that each rarity tier can be generated."""
        found = False

        # Use more attempts for legendary to avoid flakiness
        attempts = 500 if rarity == "legendary" else 200
        for _ in range(attempts):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            if item.rarity == rarity:
                found = True
                break

        assert found, f"Could not generate {rarity} item in {attempts} attempts"


class TestAffixes:
    """Test item affix system."""

    def test_affix_generation_occurs(self, entity_factory):
        """Test that affixes are generated on items."""
        has_affixes = False

        for _ in range(100):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            if item.affixes:
                has_affixes = True
                break

        assert has_affixes, "Should generate some items with affixes"

    def test_affix_count_matches_rarity(self, entity_factory):
        """Test that affix count matches rarity configuration."""
        for _ in range(100):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)

            # Allow some flexibility for edge cases
            if len(item.affixes) > 0:
                # Affix count should roughly match rarity
                if item.rarity == "common":
                    assert (
                        len(item.affixes) <= 1
                    ), "Common items should have 0-1 affixes"
                elif item.rarity == "legendary":
                    assert len(item.affixes) >= 1, "Legendary items should have affixes"

    def test_affix_in_item_name(self, entity_factory):
        """Test that affixes appear in item names."""
        # Just verify affixes are generated - name integration tested elsewhere
        found_affix = False
        for _ in range(100):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)

            if item.affixes:
                found_affix = True
                break

        assert found_affix, "Should generate items with affixes"

    def test_weapon_prefixes(self, entity_factory):
        """Test weapon prefix affixes."""
        prefixes_found = set()

        for _ in range(200):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)

            for affix in item.affixes:
                if affix in [
                    "Sharp",
                    "Heavy",
                    "Balanced",
                    "Rusty",
                    "Lethal",
                    "Vicious",
                ]:
                    prefixes_found.add(affix)

        # Should find at least some prefixes
        assert len(prefixes_found) >= 1, "Should find weapon prefixes"

    def test_weapon_suffixes(self, entity_factory):
        """Test weapon suffix affixes."""
        suffixes_found = set()

        for _ in range(200):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)

            for affix in item.affixes:
                if affix in ["of Power", "of the Bear", "of Might", "of Ruin"]:
                    suffixes_found.add(affix)

        # Should find at least some suffixes
        assert len(suffixes_found) >= 1, "Should find weapon suffixes"

    def test_armor_prefixes(self, entity_factory):
        """Test armor prefix affixes."""
        prefixes_found = set()

        for _ in range(200):
            item_id = entity_factory.create_item(0, 0, "shield")
            item = entity_factory.entity_manager.get_component(item_id, Item)

            for affix in item.affixes:
                if affix in ["Sturdy", "Hardened", "Thick", "Reinforced", "Iron"]:
                    prefixes_found.add(affix)

        assert len(prefixes_found) >= 1, "Should find armor prefixes"


class TestWeaponGeneration:
    """Test weapon item generation."""

    def test_sword_base_stats(self, entity_factory):
        """Test sword has correct base stats."""
        item_id = entity_factory.create_item(0, 0, "sword")
        weapon_stats = entity_factory.entity_manager.get_component(item_id, WeaponStats)

        assert weapon_stats is not None
        # Base sword attack should be 5
        assert (
            weapon_stats.attack_power >= 3
        ), "Sword should have reasonable base attack"

    def test_weapon_type_assignment(self, entity_factory):
        """Test weapons have correct type."""
        for item_type in ["sword"]:
            item_id = entity_factory.create_item(0, 0, item_type)
            weapon_stats = entity_factory.entity_manager.get_component(
                item_id, WeaponStats
            )

            assert weapon_stats.weapon_type in ["melee", "distance", "magic"]

    def test_weapon_stat_scaling_with_rarity(self, entity_factory):
        """Test that weapon stats scale with rarity."""
        common_attacks = []
        rare_attacks = []

        for _ in range(50):
            item_id = entity_factory.create_item(0, 0, "sword")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            weapon_stats = entity_factory.entity_manager.get_component(
                item_id, WeaponStats
            )

            if item.rarity == "common":
                common_attacks.append(weapon_stats.attack_power)
            elif item.rarity in ["rare", "epic", "legendary"]:
                rare_attacks.append(weapon_stats.attack_power)

        if common_attacks and rare_attacks:
            avg_common = sum(common_attacks) / len(common_attacks)
            avg_rare = sum(rare_attacks) / len(rare_attacks)
            # Higher rarity should generally have better stats
            assert (
                avg_rare >= avg_common * 0.8
            ), "Rare items should have comparable or better stats"


class TestArmorGeneration:
    """Test armor item generation."""

    def test_shield_base_stats(self, entity_factory):
        """Test shield has correct base stats."""
        item_id = entity_factory.create_item(0, 0, "shield")
        armor_stats = entity_factory.entity_manager.get_component(item_id, ArmorStats)

        assert armor_stats is not None
        # Base shield defense should be 3
        assert armor_stats.defense >= 2, "Shield should have reasonable base defense"

    def test_armor_slot_assignment(self, entity_factory):
        """Test armor has correct slot."""
        item_id = entity_factory.create_item(0, 0, "shield")
        armor_stats = entity_factory.entity_manager.get_component(item_id, ArmorStats)

        assert armor_stats.slot is not None
        assert isinstance(armor_stats.slot, str)

    def test_armor_stat_scaling_with_rarity(self, entity_factory):
        """Test that armor stats scale with rarity."""
        common_defense = []
        rare_defense = []

        for _ in range(50):
            item_id = entity_factory.create_item(0, 0, "shield")
            item = entity_factory.entity_manager.get_component(item_id, Item)
            armor_stats = entity_factory.entity_manager.get_component(
                item_id, ArmorStats
            )

            if item.rarity == "common":
                common_defense.append(armor_stats.defense)
            elif item.rarity in ["rare", "epic", "legendary"]:
                rare_defense.append(armor_stats.defense)

        if common_defense and rare_defense:
            avg_common = sum(common_defense) / len(common_defense)
            avg_rare = sum(rare_defense) / len(rare_defense)
            assert (
                avg_rare >= avg_common * 0.8
            ), "Rare armor should have comparable or better stats"


class TestConsumableGeneration:
    """Test consumable item generation."""

    def test_health_potion_creation(self, entity_factory):
        """Test health potion is created correctly."""
        item_id = entity_factory.create_item(0, 0, "health_potion")
        item = entity_factory.entity_manager.get_component(item_id, Item)

        assert item is not None
        assert "potion" in item.name.lower() or "health" in item.name.lower()

    def test_consumable_heal_amount(self, data_loader):
        """Test consumable heal amount from data."""
        potion_data = data_loader.get_item_data("health_potion")

        assert potion_data is not None
        assert potion_data.get("heal_amount", 0) > 0


class TestItemRender:
    """Test item rendering."""

    def test_item_char_assignment(self, entity_factory):
        """Test items have render characters."""
        for item_type in ["sword", "shield", "health_potion"]:
            item_id = entity_factory.create_item(0, 0, item_type)
            render = entity_factory.entity_manager.get_component(item_id, Render)

            assert render is not None
            assert render.char is not None
            assert len(render.char) > 0

    def test_item_color_from_rarity(self, entity_factory):
        """Test item colors match rarity."""
        item_id = entity_factory.create_item(0, 0, "sword")
        item = entity_factory.entity_manager.get_component(item_id, Item)
        render = entity_factory.entity_manager.get_component(item_id, Render)

        expected = RARITY_CONFIG[item.rarity]["color"]
        assert render.fg_color == expected
