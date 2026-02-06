"""
Boss system for special encounters in the roguelike game.
"""

from typing import Dict, List, Tuple, Optional
from core.ecs import EntityManager
from entities.entities import EntityFactory
from entities.components import Position, Monster, Health, Combat, Render
from world.persistent_world import get_persistent_world


class BossEncounter:
    """Represents a special boss encounter."""

    def __init__(
        self,
        name: str,
        boss_type: str,
        x: int,
        y: int,
        health: int,
        attack: int,
        defense: int,
        special_abilities: List[str] = None,
    ):
        self.name = name
        self.boss_type = boss_type
        self.x = x
        self.y = y
        self.health = health
        self.attack = attack
        self.defense = defense
        self.special_abilities = special_abilities or []
        self.defeated = False


class BossSystem:
    """System for managing boss encounters."""

    def __init__(self, entity_manager: EntityManager, entity_factory: EntityFactory):
        self.entity_manager = entity_manager
        self.entity_factory = entity_factory
        self.persistent_world = get_persistent_world()
        self.boss_encounters: Dict[Tuple[int, int], BossEncounter] = {}
        self._setup_boss_encounters()

    def _setup_boss_encounters(self):
        """Set up boss encounters in specific areas of the world."""
        # Define boss encounters in special areas
        # These would be placed in dungeons, special biomes, etc.

        # Forest Guardian - in dense forest area
        self.boss_encounters[(50, 50)] = BossEncounter(
            name="Forest Guardian",
            boss_type="forest_guardian",
            x=50,
            y=50,
            health=150,
            attack=15,
            defense=8,
            special_abilities=["entangle", "heal_ally", "summon_saplings"],
        )

        # Desert Sphinx - in oasis desert
        self.boss_encounters[(120, 80)] = BossEncounter(
            name="Desert Sphinx",
            boss_type="desert_sphinx",
            x=120,
            y=80,
            health=200,
            attack=18,
            defense=10,
            special_abilities=["riddle", "sand_storm", "curse"],
        )

        # Mountain Yeti King - in mountain area
        self.boss_encounters[(160, 150)] = BossEncounter(
            name="Yeti King",
            boss_type="yeti_king",
            x=160,
            y=150,
            health=250,
            attack=22,
            defense=12,
            special_abilities=["ice_roar", "freeze", "call_blizzard"],
        )

        # Swamp Hydra - in swamp area
        self.boss_encounters[(30, 140)] = BossEncounter(
            name="Swamp Hydra",
            boss_type="swamp_hydra",
            x=30,
            y=140,
            health=300,
            attack=20,
            defense=15,
            special_abilities=["regenerate_head", "poison_breath", "multi_attack"],
        )

        # Ocean Kraken - in ocean area
        self.boss_encounters[(100, 20)] = BossEncounter(
            name="Ancient Kraken",
            boss_type="ancient_kraken",
            x=100,
            y=20,
            health=400,
            attack=25,
            defense=18,
            special_abilities=["tentacle_slam", "ink_cloud", "summon_minions"],
        )

        # Dungeon Dragon - in mountain cave dungeon
        self.boss_encounters[(170, 100)] = BossEncounter(
            name="Dragon of the Depths",
            boss_type="cave_dragon",
            x=170,
            y=100,
            health=500,
            attack=30,
            defense=20,
            special_abilities=["fire_breath", "wing_buffet", "roar_fear"],
        )

    def check_for_boss_encounter(
        self, player_x: int, player_y: int, radius: int = 5
    ) -> Optional[BossEncounter]:
        """Check if the player is near a boss encounter."""
        for (bx, by), boss in self.boss_encounters.items():
            if not boss.defeated:
                distance = ((player_x - bx) ** 2 + (player_y - by) ** 2) ** 0.5
                if distance <= radius:
                    return boss
        return None

    def spawn_boss(self, boss_encounter: BossEncounter) -> int:
        """Spawn a boss entity."""
        # Create the boss entity
        eid = self.entity_manager.create_entity()

        # Determine appearance based on boss type
        boss_appearance = self._get_boss_appearance(boss_encounter.boss_type)

        # Add components
        self.entity_manager.add_component(
            eid, Position(x=boss_encounter.x, y=boss_encounter.y)
        )
        self.entity_manager.add_component(
            eid, Render(char=boss_appearance["char"], fg_color=boss_appearance["color"])
        )
        self.entity_manager.add_component(
            eid, Health(current=boss_encounter.health, maximum=boss_encounter.health)
        )
        self.entity_manager.add_component(
            eid,
            Combat(attack_power=boss_encounter.attack, defense=boss_encounter.defense),
        )
        self.entity_manager.add_component(
            eid,
            Monster(
                ai_type="aggressive",
                monster_type=boss_encounter.boss_type,
                name=boss_encounter.name,
            ),
        )

        # Mark the boss as spawned
        boss_encounter.defeated = False

        return eid

    def _get_boss_appearance(self, boss_type: str) -> Dict[str, any]:
        """Get the appearance details for a boss type."""
        appearances = {
            "forest_guardian": {"char": "T", "color": (34, 139, 34)},  # Green for tree
            "desert_sphinx": {"char": "S", "color": (210, 180, 140)},  # Tan for sphinx
            "yeti_king": {"char": "Y", "color": (173, 216, 230)},  # Light blue for yeti
            "swamp_hydra": {"char": "H", "color": (139, 69, 19)},  # Brown for hydra
            "ancient_kraken": {"char": "K", "color": (75, 0, 130)},  # Indigo for kraken
            "cave_dragon": {"char": "D", "color": (139, 0, 0)},  # Dark red for dragon
        }
        return appearances.get(
            boss_type, {"char": "B", "color": (255, 0, 0)}
        )  # Default boss appearance

    def trigger_boss_encounter(self, boss_encounter: BossEncounter) -> int:
        """Trigger a boss encounter and spawn the boss."""
        print(f"BOSS ENCOUNTER: {boss_encounter.name} appears!")
        boss_entity_id = self.spawn_boss(boss_encounter)
        return boss_entity_id
