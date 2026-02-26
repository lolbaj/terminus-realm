"""
Tile palette management for the Map Editor.
Groups tiles into categories for easier navigation.
"""

import sys
import os
from typing import Dict, List
from .models import TileDef

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data.loader import DATA_LOADER

CHAR_TO_ID = {
    ".": "0",
    "#": "1",
    "+": "2",
    "~": "3",
    ",": "4",
    "T": "5",
    "<": "6",
    ">": "7",
    "S": "8",
    "P": "9",
    "*": "10",
    "=": "11",
    "A": "12",
    "C": "13",
    "I": "14",
    "@": "player",
    "║": "1",
    "═": "1",
    "╚": "1",
    "╔": "1",
    "╗": "1",
    "╝": "1",
    "╠": "1",
    "╦": "1",
    "╣": "1",
    "╩": "1",
    "╬": "1",
    "█": "1",
    # Monsters
    "g": "m_goblin",
    "o": "m_orc",
    "k": "m_skeleton",
    "r": "m_spider",
    "b": "m_bat",
    "U": "m_guard",
    "m": "m_merchant",
    "h": "m_citizen",
    "d": "m_dog",
    "w": "m_wolf",
    "E": "m_bear",
    "q": "m_scorpion",
    "n": "m_giant_ant",
    "j": "m_ice_slime",
    "y": "m_yeti",
    "p": "m_fire_imp",
    "v": "m_lava_golem",
    # Items
    "!": "i_health_potion",
    "/": "i_sword",
    "[": "i_shield",
    "(": "i_iron_helmet",
    ")": "i_leather_helmet",
    "{": "i_iron_chainmail",
    "}": "i_leather_tunic",
    "_": "i_iron_greaves",
    "-": "i_leather_boots",
}

CATEGORIES = {
    "GROUND": [".", ",", "S", "*", "~", "=", "A", "I", "P"],
    "PLANTS": ["T", "C"],
    "WALLS": ["#", "+", "║", "═", "╔", "╗", "╚", "╝", "╠", "╦", "╣", "╩", "╬", "█"],
    "MONSTERS": ["g", "o", "k", "r", "b", "U", "m", "h", "d", "w", "E", "q", "n", "j", "y", "p", "v"],
    "ITEMS": ["!", "/", "[", "(", ")", "{", "}", "_", "-"],
    "SPECIAL": ["@", "<", ">"],
}


def load_tile_palette() -> Dict[str, TileDef]:
    palette = {}
    try:
        game_tiles = DATA_LOADER.load_json("tiles")
        game_monsters = DATA_LOADER.load_json("monsters")
        game_items = DATA_LOADER.load_json("items")

        for char, tid in CHAR_TO_ID.items():
            if tid == "player":
                palette[char] = TileDef(
                    " @", "Start", True, True, (255, 255, 255), (150, 0, 150)
                )
                continue
            
            # Monster Handling
            if tid.startswith("m_"):
                m_key = tid[2:]
                data = game_monsters.get(m_key, {})
                palette[char] = TileDef(
                    char=data.get("char", "M ") if len(data.get("char", "")) == 2 else data.get("char", "M") + " ",
                    name=data.get("name", m_key),
                    walkable=True,
                    transparent=True,
                    fg_color=tuple(data.get("fg_color", [255, 255, 255])),
                    bg_color=None
                )
                continue

            # Item Handling
            if tid.startswith("i_"):
                i_key = tid[2:]
                data = game_items.get(i_key, {})
                palette[char] = TileDef(
                    char=data.get("char", "I ") if len(data.get("char", "")) == 2 else data.get("char", "I") + " ",
                    name=data.get("name", i_key),
                    walkable=True,
                    transparent=True,
                    fg_color=tuple(data.get("color", [255, 255, 255])),
                    bg_color=None
                )
                continue

            # Normal Tile Handling
            data = game_tiles.get(tid, {})
            display_char = data.get("char", "??")
            if char in "║═╚╔╗╝╠╦╣╩╬█":
                display_char = char + (" " if char != "█" else "█")
            palette[char] = TileDef(
                char=display_char,
                name=(
                    data.get("name", "unknown")
                    if char not in "║═╚╔╗╝╠╦╣╩╬█"
                    else f"Wall ({char})"
                ),
                walkable=data.get("walkable", True),
                transparent=data.get("transparent", True),
                fg_color=tuple(data.get("fg", [255, 255, 255])),
                bg_color=tuple(data.get("bg", [0, 0, 0])) if data.get("bg") else None,
            )
    except Exception:
        palette = {
            ".": TileDef("..", "Floor", True, True, (100, 100, 100), (40, 40, 40))
        }
    return palette


TILE_PALETTE = load_tile_palette()


def get_category_layout(category_name: str) -> List[List[str]]:
    chars = CATEGORIES.get(category_name, [])
    # Split into rows of 6
    layout = []
    for i in range(0, len(chars), 6):
        layout.append(chars[i : i + 6])
    return layout
