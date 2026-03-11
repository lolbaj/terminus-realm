"""
Drawing tools and algorithms for the Map Editor.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .map_manager import MapManager
    from .undo_manager import UndoManager

from . import auto_tiler
from .models import SymmetryMode


def set_tile_with_undo(
    map_mgr: "MapManager", undo_mgr: "UndoManager", x: int, y: int, char: str, symmetry: SymmetryMode = SymmetryMode.NONE
):
    if symmetry == SymmetryMode.NONE:
        set_tile_with_undo_layer(map_mgr, undo_mgr, x, y, char, map_mgr.active_layer)
    else:
        set_tile_symmetrical(map_mgr, undo_mgr, x, y, char, symmetry)


def set_tile_symmetrical(
    map_mgr: "MapManager", undo_mgr: "UndoManager", x: int, y: int, char: str, symmetry: SymmetryMode
):
    layer = map_mgr.active_layer
    points = [(x, y)]
    
    if symmetry == SymmetryMode.HORIZONTAL:
        points.append((map_mgr.width - 1 - x, y))
    elif symmetry == SymmetryMode.VERTICAL:
        points.append((x, map_mgr.height - 1 - y))
    elif symmetry == SymmetryMode.QUAD:
        points.append((map_mgr.width - 1 - x, y))
        points.append((x, map_mgr.height - 1 - y))
        points.append((map_mgr.width - 1 - x, map_mgr.height - 1 - y))
        
    for px, py in points:
        set_tile_with_undo_layer(map_mgr, undo_mgr, px, py, char, layer)


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
    map_mgr: "MapManager", undo_mgr: "UndoManager", x: int, y: int, char: str, size: int, symmetry: SymmetryMode = SymmetryMode.NONE
):
    h = size // 2
    for dy in range(-h, size - h):
        for dx in range(-h, size - h):
            set_tile_with_undo(map_mgr, undo_mgr, x + dx, y + dy, char, symmetry)


def draw_line(
    map_mgr: "MapManager",
    undo_mgr: "UndoManager",
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    char: str,
    brush_size: int,
    symmetry: SymmetryMode = SymmetryMode.NONE
):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        draw_brush(map_mgr, undo_mgr, x0, y0, char, brush_size, symmetry)
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
    symmetry: SymmetryMode = SymmetryMode.NONE
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
    
    # Calculate symmetry seed points
    start_points = [(x, y)]
    if symmetry == SymmetryMode.HORIZONTAL:
        start_points.append((map_mgr.width - 1 - x, y))
    elif symmetry == SymmetryMode.VERTICAL:
        start_points.append((x, map_mgr.height - 1 - y))
    elif symmetry == SymmetryMode.QUAD:
        start_points.append((map_mgr.width - 1 - x, y))
        start_points.append((x, map_mgr.height - 1 - y))
        start_points.append((map_mgr.width - 1 - x, map_mgr.height - 1 - y))

    visited = set()
    for sx, sy in start_points:
        if (sx, sy) in visited:
            continue
        stack = [(sx, sy)]
        visited.add((sx, sy))

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
    symmetry: SymmetryMode = SymmetryMode.NONE
):
    # Temporarily disable auto-tiling for speed
    was_auto = getattr(map_mgr, "auto_tiling", False)
    map_mgr.auto_tiling = False
    layer = map_mgr.active_layer

    undo_mgr.start_group()
    
    # Calculate all symmetry rectangles
    rects = [(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))]
    if symmetry == SymmetryMode.HORIZONTAL:
        x_min, y_min, x_max, y_max = rects[0]
        rects.append((map_mgr.width - 1 - x_max, y_min, map_mgr.width - 1 - x_min, y_max))
    elif symmetry == SymmetryMode.VERTICAL:
        x_min, y_min, x_max, y_max = rects[0]
        rects.append((x_min, map_mgr.height - 1 - y_max, x_max, map_mgr.height - 1 - y_min))
    elif symmetry == SymmetryMode.QUAD:
        x_min, y_min, x_max, y_max = rects[0]
        rects.append((map_mgr.width - 1 - x_max, y_min, map_mgr.width - 1 - x_min, y_max))
        rects.append((x_min, map_mgr.height - 1 - y_max, x_max, map_mgr.height - 1 - y_min))
        rects.append((map_mgr.width - 1 - x_max, map_mgr.height - 1 - y_max, map_mgr.width - 1 - x_min, map_mgr.height - 1 - y_min))

    affected_points = []
    for x_min, y_min, x_max, y_max in rects:
        for ry in range(y_min, y_max + 1):
            for rx in range(x_min, x_max + 1):
                set_tile_with_undo_layer(map_mgr, undo_mgr, rx, ry, char, layer)
                affected_points.append((rx, ry))
    undo_mgr.end_group()

    map_mgr.auto_tiling = was_auto
    if was_auto:
        for rx, ry in affected_points:
            auto_tiler.process_auto_tile(map_mgr, rx, ry, layer, undo_mgr)
