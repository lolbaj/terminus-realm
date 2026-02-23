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
}

CATEGORIES = {
    "GROUND": [".", ",", "S", "*", "~", "=", "A", "I", "P"],
    "PLANTS": ["T", "C"],
    "WALLS": ["#", "+", "║", "═", "╔", "╗", "╚", "╝", "╠", "╦", "╣", "╩", "╬", "█"],
    "SPECIAL": ["@", "<", ">"],
}


def load_tile_palette() -> Dict[str, TileDef]:
    palette = {}
    try:
        game_tiles = DATA_LOADER.load_json("tiles")
        for char, tid in CHAR_TO_ID.items():
            if tid == "player":
                palette[char] = TileDef(
                    " @", "Start", True, True, (255, 255, 255), (150, 0, 150)
                )
                continue
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
