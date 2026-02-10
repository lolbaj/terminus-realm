"""
Component definitions for the ECS system.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List
from core.ecs import Component


@dataclass(slots=True)
class Position(Component):
    """Position component for entities."""

    x: int
    y: int
    z: int = 0  # For multi-level maps


@dataclass(slots=True)
class Render(Component):
    """Render component for entities."""

    char: str
    fg_color: Tuple[int, int, int]  # RGB values
    bg_color: Optional[Tuple[int, int, int]] = None
    priority: int = 0  # Higher numbers render on top


@dataclass(slots=True)
class Health(Component):
    """Health component for entities."""

    current: int
    maximum: int


@dataclass(slots=True)
class Combat(Component):
    """Combat component for entities."""

    attack_power: int
    defense: int


@dataclass(slots=True)
class Player(Component):
    """Player tag component."""

    pass


@dataclass(slots=True)
class Skills(Component):
    """Rucoy-style skill system."""

    melee: int = 5
    distance: int = 5
    magic: int = 5

    # XP trackers for each skill
    melee_xp: int = 0
    distance_xp: int = 0
    magic_xp: int = 0

    # XP thresholds (next level = current_level * 100 roughly)
    def xp_for_next_level(self, current_level: int) -> int:
        return current_level * 50


@dataclass(slots=True)
class Level(Component):
    """Level component for entities that can gain experience."""

    current_level: int = 1
    current_xp: int = 0
    xp_to_next_level: int = 100
    attribute_points: int = 0


@dataclass(slots=True)
class Monster(Component):
    """Monster tag component."""

    ai_type: str = "passive"  # passive, aggressive, patrol
    monster_type: str = "goblin"  # goblin, orc, spider, etc.
    name: str = "Unknown Monster"
    speed: float = 1.0  # Movement speed factor
    xp_reward: int = 10  # XP given when defeated


@dataclass(slots=True)
class Item(Component):
    """Generic item component."""

    name: str
    description: str
    weight: float = 0.0
    value: int = 0
    char: str = "?"
    color: Tuple[int, int, int] = (255, 255, 255)
    rarity: str = "common"
    affixes: List[str] = None

    def __post_init__(self):
        if self.affixes is None:
            self.affixes = []


@dataclass(slots=True)
class Consumable(Component):
    """Component for items that can be consumed."""

    effect_type: str  # "heal", "xp", "buff"
    amount: int
    message: str = "You use the item."


@dataclass(slots=True)
class WeaponStats(Component):
    """Stats for weapon items."""

    attack_power: int
    weapon_type: str  # "melee", "distance", "magic"


@dataclass(slots=True)
class ArmorStats(Component):
    """Stats for armor items."""

    defense: int
    slot: str  # "body", "head", "legs"


@dataclass(slots=True)
class Inventory(Component):
    """Inventory component for entities."""

    capacity: int
    items: List[int]  # List of Entity IDs representing items

    def __post_init__(self):
        if self.items is None:
            self.items = []


@dataclass(slots=True)
class Equipment(Component):
    """Equipment component for entities."""

    weapon: Optional[str] = None
    weapon_type: str = "melee"  # melee, distance, magic
    armor: Optional[str] = None


@dataclass(slots=True)
class FieldOfView(Component):
    """Field of view component for entities."""

    radius: int
    visible_tiles: List[Tuple[int, int]] = None

    def __post_init__(self):
        if self.visible_tiles is None:
            self.visible_tiles = []


@dataclass(slots=True)
class BlocksTile(Component):
    """Component indicating that an entity blocks movement."""

    pass


@dataclass(slots=True)
class BlocksVision(Component):
    """Component indicating that an entity blocks vision."""

    pass


@dataclass(slots=True)
class Shop(Component):
    """Component for entities that can trade."""

    shop_name: str
    items: List[Tuple[str, int]]  # List of (item_type, price)

    def __post_init__(self):
        if self.items is None:
            self.items = []
