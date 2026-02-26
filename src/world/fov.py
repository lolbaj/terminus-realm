"""
Field of View (FOV) calculation module.
Implements a robust Recursive Shadowcasting algorithm.
"""

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.map import GameMap


def calculate_fov(game_map: "GameMap", x: int, y: int, radius: int) -> np.ndarray:
    """
    Calculate the field of view from a given position.

    Args:
        game_map: The GameMap instance containing tile data.
        x: The x-coordinate of the observer.
        y: The y-coordinate of the observer.
        radius: The maximum visibility radius.

    Returns:
        A boolean numpy array where True indicates the tile is visible.
    """
    width, height = game_map.width, game_map.height
    visible = np.zeros((height, width), dtype=bool)

    # Observer is always visible
    if 0 <= x < width and 0 <= y < height:
        visible[y, x] = True
    else:
        return visible

    # Scan each of the 8 octants
    for octant in range(8):
        _refresh_octant(game_map, visible, x, y, radius, octant)

    return visible


def _refresh_octant(game_map, visible, x, y, radius, octant):
    """Scan a single octant using recursive shadowcasting."""
    # (row, start_slope, end_slope)
    stack = [(1, 1.0, 0.0)]

    width, height = game_map.width, game_map.height

    while stack:
        row, start_slope, end_slope = stack.pop()

        if row > radius:
            continue

        prev_tile_blocked = False

        # Iterate through columns in this row
        for col in range(row + 1):
            # Transform relative octant coordinates to map coordinates
            # Each octant has a different mapping of (row, col) to (dx, dy)
            dx, dy = _transform_octant(row, col, octant)
            mx, my = x + dx, y + dy

            if not (0 <= mx < width and 0 <= my < height):
                continue

            # Slopes for the current tile
            # Use symmetric slopes for better results
            l_slope = (col + 0.5) / (row - 0.5)
            r_slope = (col - 0.5) / (row + 0.5)

            if start_slope < r_slope:
                continue
            if end_slope > l_slope:
                break  # Moved past the visible cone

            # Check distance
            if (dx * dx + dy * dy) <= (radius * radius):
                visible[my, mx] = True

            # Transparency check
            tile_blocked = not game_map.is_transparent(mx, my)

            if prev_tile_blocked:
                if not tile_blocked:
                    # Transition from blocked to free: start a new segment
                    start_slope = l_slope
            else:
                if tile_blocked and row < radius:
                    # Transition from free to blocked: push the completed segment
                    stack.append((row + 1, start_slope, r_slope))

            prev_tile_blocked = tile_blocked

        # If the last tile was free, the segment continues into the next row
        if not prev_tile_blocked and row < radius:
            stack.append((row + 1, start_slope, end_slope))


def _transform_octant(row, col, octant):
    """Convert (row, col) in an abstract octant to (dx, dy) relative to origin."""
    if octant == 0:
        return (row, col)
    if octant == 1:
        return (col, row)
    if octant == 2:
        return (-col, row)
    if octant == 3:
        return (-row, col)
    if octant == 4:
        return (-row, -col)
    if octant == 5:
        return (-col, -row)
    if octant == 6:
        return (col, -row)
    if octant == 7:
        return (row, -col)
    return (0, 0)
