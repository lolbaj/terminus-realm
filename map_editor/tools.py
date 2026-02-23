"""
Drawing tools and algorithms for the Map Editor.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .map_manager import MapManager
    from .undo_manager import UndoManager

from . import auto_tiler


def set_tile_with_undo(
    map_mgr: "MapManager", undo_mgr: "UndoManager", x: int, y: int, char: str
):
    set_tile_with_undo_layer(map_mgr, undo_mgr, x, y, char, map_mgr.active_layer)


def set_tile_with_undo_layer(
    map_mgr: "MapManager",
    undo_mgr: "UndoManager",
    x: int,
    y: int,
    char: str,
    layer: str,
):
    if 0 <= x < map_mgr.width and 0 <= y < map_mgr.height:
        old = map_mgr.get_tile(x, y, layer)
        if old != char:
            undo_mgr.push_action(x, y, old, char, layer)
            map_mgr.set_tile(x, y, char, layer)
            # Apply auto-tiling if enabled
            if getattr(map_mgr, "auto_tiling", True):
                auto_tiler.update_area(map_mgr, x, y, layer, undo_mgr)


def draw_brush(
    map_mgr: "MapManager", undo_mgr: "UndoManager", x: int, y: int, char: str, size: int
):
    h = size // 2
    for dy in range(-h, size - h):
        for dx in range(-h, size - h):
            set_tile_with_undo(map_mgr, undo_mgr, x + dx, y + dy, char)


def draw_line(
    map_mgr: "MapManager",
    undo_mgr: "UndoManager",
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    char: str,
    brush_size: int,
):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        draw_brush(map_mgr, undo_mgr, x0, y0, char, brush_size)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def flood_fill(
    map_mgr: "MapManager",
    undo_mgr: "UndoManager",
    x: int,
    y: int,
    target_char: str,
    replace_char: str,
):
    if target_char == replace_char:
        return

    from .palette import CHAR_TO_ID

    layer = map_mgr.active_layer
    # Bounds check for starting point
    if not (0 <= x < map_mgr.width and 0 <= y < map_mgr.height):
        return

    # Get IDs for more robust comparison (e.g. any wall type matches any wall type)
    target_id = CHAR_TO_ID.get(target_char, target_char)
    replace_id = CHAR_TO_ID.get(replace_char, replace_char)

    if target_id == replace_id and target_char != " ":
        # If IDs match, only fill if characters differ (unless they are empty space)
        if map_mgr.get_tile(x, y, layer) == replace_char:
            return

    # Temporarily disable auto-tiling for speed during massive fill
    was_auto = getattr(map_mgr, "auto_tiling", False)
    map_mgr.auto_tiling = False

    undo_mgr.start_group()
    stack = [(x, y)]
    visited = {(x, y)}

    while stack:
        cx, cy = stack.pop()

        # Apply change
        set_tile_with_undo_layer(map_mgr, undo_mgr, cx, cy, replace_char, layer)

        # Add neighbors
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < map_mgr.width and 0 <= ny < map_mgr.height:
                if (nx, ny) not in visited:
                    n_char = map_mgr.get_tile(nx, ny, layer)
                    n_id = CHAR_TO_ID.get(n_char, n_char)
                    if n_id == target_id:
                        visited.add((nx, ny))
                        stack.append((nx, ny))

    undo_mgr.end_group()

    # Restore auto-tiling and update area
    map_mgr.auto_tiling = was_auto
    if was_auto:
        # For simplicity, we trigger auto-tiling updates on neighbors of the entire filled area
        # but a full map pass is easier if the area is large.
        # Let's just update the ones in visited.
        for vx, vy in visited:
            auto_tiler.process_auto_tile(map_mgr, vx, vy, layer, undo_mgr)


def draw_rect(
    map_mgr: "MapManager",
    undo_mgr: "UndoManager",
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    char: str,
):
    # Temporarily disable auto-tiling for speed
    was_auto = getattr(map_mgr, "auto_tiling", False)
    map_mgr.auto_tiling = False
    layer = map_mgr.active_layer

    undo_mgr.start_group()
    x_min, x_max = min(x0, x1), max(x0, x1)
    y_min, y_max = min(y0, y1), max(y0, y1)

    for ry in range(y_min, y_max + 1):
        for rx in range(x_min, x_max + 1):
            set_tile_with_undo_layer(map_mgr, undo_mgr, rx, ry, char, layer)
    undo_mgr.end_group()

    map_mgr.auto_tiling = was_auto
    if was_auto:
        # Update connection for the border of the rectangle
        for ry in range(y_min, y_max + 1):
            for rx in range(x_min, x_max + 1):
                # We only need to auto-tile walls.
                # For speed, only update if it's actually a wall.
                auto_tiler.process_auto_tile(map_mgr, rx, ry, layer, undo_mgr)
