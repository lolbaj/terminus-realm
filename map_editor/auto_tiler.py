"""
Auto-tiling logic for the Map Editor.
Automatically selects characters based on neighbor connections.
"""

from typing import TYPE_CHECKING
from .palette import CHAR_TO_ID

if TYPE_CHECKING:
    from .map_manager import MapManager
    from .undo_manager import UndoManager

# Bitmask for neighbors:
#   1
# 8   2
#   4
# (Top=1, Right=2, Bottom=4, Left=8)

# Characters for box-drawing connections
WALL_MAP = {
    0: "█",  # Isolated
    1: "║",
    2: "═",
    4: "║",
    8: "═",
    3: "╚",
    6: "╔",
    12: "╗",
    9: "╝",
    5: "║",
    10: "═",
    7: "╠",
    14: "╦",
    13: "╣",
    11: "╩",
    15: "╬",
}


def is_type(map_mgr: "MapManager", x: int, y: int, layer: str, target_id: str) -> bool:
    char = map_mgr.get_tile(x, y, layer)
    return CHAR_TO_ID.get(char) == target_id


def get_neighbors_mask(
    map_mgr: "MapManager", x: int, y: int, layer: str, target_id: str
) -> int:
    mask = 0
    if is_type(map_mgr, x, y - 1, layer, target_id):
        mask |= 1
    if is_type(map_mgr, x + 1, y, layer, target_id):
        mask |= 2
    if is_type(map_mgr, x, y + 1, layer, target_id):
        mask |= 4
    if is_type(map_mgr, x - 1, y, layer, target_id):
        mask |= 8
    return mask


def process_auto_tile(
    map_mgr: "MapManager", x: int, y: int, layer: str, undo_mgr: "UndoManager" = None
):
    """Updates the character at (x, y) based on neighbors."""
    char = map_mgr.get_tile(x, y, layer)
    tid = CHAR_TO_ID.get(char)

    if tid == "1":  # Wall
        mask = get_neighbors_mask(map_mgr, x, y, layer, "1")
        new_char = WALL_MAP.get(mask, "█")
        if new_char != char:
            if undo_mgr:
                undo_mgr.push_action(x, y, char, new_char, layer)
            map_mgr.set_tile(x, y, new_char, layer)

    # Future water logic could go here if we had directional water tiles


def update_area(
    map_mgr: "MapManager", x: int, y: int, layer: str, undo_mgr: "UndoManager" = None
):
    """Updates (x, y) and all its neighbors."""
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            process_auto_tile(map_mgr, x + dx, y + dy, layer, undo_mgr)
