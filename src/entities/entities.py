from typing import List, Tuple
import random
from core.ecs import EntityManager
from data.loader import DATA_LOADER
from entities.components import (
    Position,
    Render,
    Health,
    Player,
    Monster,
    Combat,
    Level,
    Skills,
    Equipment,
    Item,
    Consumable,
    WeaponStats,
    ArmorStats,
    Inventory,
    Shop,
)

# Loot Configuration
RARITY_CONFIG = {
    "common": {"weight": 60, "color": (255, 255, 255), "affixes": 0},
    "uncommon": {"weight": 25, "color": (50, 255, 50), "affixes": 1},
    "rare": {"weight": 10, "color": (50, 100, 255), "affixes": 2},
    "epic": {"weight": 4, "color": (180, 50, 255), "affixes": 3},
    "legendary": {"weight": 1, "color": (255, 215, 0), "affixes": 4},
}

WEAPON_PREFIXES = {
    "Sharp": {"attack": 2},
    "Heavy": {"attack": 4},
    "Balanced": {"attack": 1},
    "Rusty": {"attack": -1},
    "Lethal": {"attack": 5},
    "Vicious": {"attack": 3},
}

WEAPON_SUFFIXES = {
    "of Power": {"attack": 3},
    "of the Bear": {"attack": 5},
    "of Might": {"attack": 2},
    "of Ruin": {"attack": 4},
}

ARMOR_PREFIXES = {
    "Sturdy": {"defense": 2},
    "Hardened": {"defense": 3},
    "Thick": {"defense": 1},
    "Reinforced": {"defense": 4},
    "Iron": {"defense": 2},
}

ARMOR_SUFFIXES = {
    "of Stone": {"defense": 4},
    "of Protection": {"defense": 2},
    "of the Turtle": {"defense": 3},
    "of Iron": {"defense": 2},
}

SPECIAL_EFFECTS = ["Vampiric", "Flaming", "Frozen", "Swift"]


class EntityFactory:
    """Factory for creating entities with predefined templates."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def create_shopkeeper(
        self,
        x: int,
        y: int,
        name: str = "Merchant",
        shop_items: List[Tuple[str, int]] = None,
    ) -> int:
        """Create a static shopkeeper entity."""
        eid = self.entity_manager.create_entity()

        if shop_items is None:
            shop_items = [("health_potion", 50), ("sword", 100)]

        self.entity_manager.add_component(eid, Position(x=x, y=y))
        self.entity_manager.add_component(
            eid, Render(char="💰", fg_color=(255, 215, 0))
        )
        self.entity_manager.add_component(eid, Health(current=100, maximum=100))

        # Add Shop component
        self.entity_manager.add_component(
            eid, Shop(shop_name=f"{name}'s Shop", items=shop_items)
        )

        # Add Monster component with static AI so it can be interacted with
        self.entity_manager.add_component(
            eid,
            Monster(
                ai_type="static",
                monster_type="merchant",
                name=name,
                xp_reward=0,
            ),
        )

        return eid

    def create_player(self, x: int, y: int) -> int:
        """Create a player entity."""
        eid = self.entity_manager.create_entity()

        # Create initial equipment
        sword = self.create_item(0, 0, "sword")
        # Remove position from equipped item so it doesn't show on map
        self.entity_manager.remove_component(sword, Position)

        # Add components
        self.entity_manager.add_component(eid, Position(x=x, y=y))
        self.entity_manager.add_component(
            eid, Render(char="🧙", fg_color=(255, 255, 255))
        )
        self.entity_manager.add_component(eid, Health(current=500, maximum=500))
        self.entity_manager.add_component(
            eid, Combat(attack_power=0, defense=0)
        )  # Combat now derived from Skills
        self.entity_manager.add_component(eid, Skills())

        # Equip the sword
        self.entity_manager.add_component(
            eid, Equipment(weapon=sword, weapon_type="melee")
        )

        self.entity_manager.add_component(eid, Inventory(capacity=20, items=[]))
        self.entity_manager.add_component(eid, Level())
        self.entity_manager.add_component(eid, Player())

        return eid

    def create_monster(self, x: int, y: int, monster_type: str = "goblin") -> int:
        """Create a monster entity."""
        eid = self.entity_manager.create_entity()

        # Load monster data
        data = DATA_LOADER.get_monster_data(monster_type)

        if not data:
            # Default fallback
            data = {
                "name": "Unknown Creature",
                "char": "👾",
                "fg_color": [255, 255, 255],
                "health": 10,
                "attack": 3,
                "defense": 0,
                "ai_type": "passive",
                "xp_reward": 10,
            }

        # Add components
        self.entity_manager.add_component(eid, Position(x=x, y=y))

        # Color tuple conversion
        fg_color = tuple(data.get("fg_color", [255, 255, 255]))
        self.entity_manager.add_component(
            eid, Render(char=data.get("char", "?"), fg_color=fg_color)
        )

        hp = data.get("health", 10)
        self.entity_manager.add_component(eid, Health(current=hp, maximum=hp))

        self.entity_manager.add_component(
            eid,
            Combat(attack_power=data.get("attack", 0), defense=data.get("defense", 0)),
        )

        self.entity_manager.add_component(
            eid,
            Monster(
                ai_type=data.get("ai_type", "passive"),
                monster_type=monster_type,
                name=data.get("name", "Unknown"),
                xp_reward=data.get("xp_reward", 0),
            ),
        )

        return eid

    def create_item(self, x: int, y: int, item_type: str) -> int:
        """Create an item entity with random rarity/affixes."""
        eid = self.entity_manager.create_entity()
        self.entity_manager.add_component(eid, Position(x=x, y=y))

        # Load item data
        data = DATA_LOADER.get_item_data(item_type)

        if not data:
            # Fallback for unknown items
            self.entity_manager.add_component(
                eid, Render(char="📦", fg_color=(255, 255, 0))
            )
            self.entity_manager.add_component(
                eid,
                Item(
                    name="Unknown Item",
                    description="What is this?",
                    char="📦",
                    color=(255, 255, 0),
                ),
            )
            return eid

        # Roll Rarity
        rarities = list(RARITY_CONFIG.keys())
        weights = [RARITY_CONFIG[r]["weight"] for r in rarities]
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        config = RARITY_CONFIG[rarity]

        # Base item properties
        name = data.get("name", "Item")
        fg_color = config["color"]  # Use rarity color
        affixes = []

        # Type specific generation
        i_type = data.get("type", "misc")
        attack_bonus = data.get("attack_bonus", 0)
        defense_bonus = data.get("defense_bonus", 0)

        if i_type == "weapon" and config["affixes"] > 0:
            # Generate Weapon Affixes
            num_affixes = config["affixes"]

            # 1st: Prefix
            if num_affixes >= 1:
                prefix = random.choice(list(WEAPON_PREFIXES.keys()))
                name = f"{prefix} {name}"
                attack_bonus += WEAPON_PREFIXES[prefix]["attack"]
                affixes.append(prefix)

            # 2nd: Suffix
            if num_affixes >= 2:
                suffix = random.choice(list(WEAPON_SUFFIXES.keys()))
                name = f"{name} {suffix}"
                attack_bonus += WEAPON_SUFFIXES[suffix]["attack"]
                affixes.append(suffix)

            # 3rd/4th: Extra Boost (Special Effects)
            if num_affixes >= 3:
                effect = random.choice(SPECIAL_EFFECTS)
                affixes.append(effect)
                name = f"{effect} {name}"

            if num_affixes >= 4:
                # Add another special effect
                effect = random.choice(SPECIAL_EFFECTS)
                if effect not in affixes:
                    affixes.append(effect)
                    name = f"{effect} {name}"
                else:
                    # Fallback if duplicate rolled
                    attack_bonus += 5
                    affixes.append("Legendary Power")

        elif i_type == "armor" and config["affixes"] > 0:
            # Generate Armor Affixes
            num_affixes = config["affixes"]

            if num_affixes >= 1:
                prefix = random.choice(list(ARMOR_PREFIXES.keys()))
                name = f"{prefix} {name}"
                defense_bonus += ARMOR_PREFIXES[prefix]["defense"]
                affixes.append(prefix)

            if num_affixes >= 2:
                suffix = random.choice(list(ARMOR_SUFFIXES.keys()))
                name = f"{name} {suffix}"
                defense_bonus += ARMOR_SUFFIXES[suffix]["defense"]
                affixes.append(suffix)

            if num_affixes >= 3:
                defense_bonus += 2
                affixes.append("Epic Boost")
            if num_affixes >= 4:
                defense_bonus += 3
                affixes.append("Legendary Boost")

        # Create Components
        self.entity_manager.add_component(
            eid, Render(char=data.get("char", "?"), fg_color=fg_color)
        )

        self.entity_manager.add_component(
            eid,
            Item(
                name=name,
                description=data.get("description", ""),
                char=data.get("char", "?"),
                color=fg_color,
                rarity=rarity,
                affixes=affixes,
            ),
        )

        if i_type == "consumable":
            self.entity_manager.add_component(
                eid,
                Consumable(
                    effect_type="heal",
                    amount=data.get("heal_amount", 0),
                    message=f"You use the {data.get('name')}.",
                ),
            )
        elif i_type == "weapon":
            self.entity_manager.add_component(
                eid,
                WeaponStats(
                    attack_power=attack_bonus,
                    weapon_type="melee",  # Default
                ),
            )
        elif i_type == "armor":
            self.entity_manager.add_component(
                eid,
                ArmorStats(
                    defense=defense_bonus,
                    slot="hand",  # Default
                ),
            )

        return eid


class EntityManagerWrapper:
    """Wrapper for entity management with convenience methods."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.factory = EntityFactory(entity_manager)

    def get_player(self) -> int:
        """Get the player entity ID."""
        player_entities = self.entity_manager.get_entities_with_components(Player)
        if player_entities:
            return player_entities[0]
        return None

    def get_monsters_at_position(self, x: int, y: int) -> List[int]:
        """Get all monsters at a specific position."""
        monsters = self.entity_manager.get_entities_with_components(Monster)
        result = []

        for eid in monsters:
            pos = self.entity_manager.get_component(eid, Position)
            if pos and pos.x == x and pos.y == y:
                result.append(eid)

        return result

    def get_items_at_position(self, x: int, y: int) -> List[int]:
        """Get all items at a specific position."""
        # Items don't have a specific component yet, so we'll look for entities
        # that have Position and Render but not Player/Monster
        all_entities = self.entity_manager.entities.keys()
        result = []

        for eid in all_entities:
            pos = self.entity_manager.get_component(eid, Position)
            if pos and pos.x == x and pos.y == y:
                # Check if it's not a player or monster
                if not (
                    self.entity_manager.has_component(eid, Player)
                    or self.entity_manager.has_component(eid, Monster)
                ):
                    result.append(eid)

        return result
