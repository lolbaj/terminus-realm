"""
Field of View (FOV) calculation module.
Implements Recursive Shadowcasting for efficient visibility.
"""

import numpy as np
from world.map import GameMap


def calculate_fov(game_map: GameMap, x: int, y: int, radius: int) -> np.ndarray:
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
    visible[y, x] = True

    def get_light(r, c):
        if 0 <= r < height and 0 <= c < width:
            # We assume walls block light.
            # game_map.is_transparent(c, r) would be ideal,
            # but checking is_walkable is a close proxy if walls are the only blocker.
            # Better: check the tile type directly if available, or use a method on game_map.
            # Using game_map.tiles directly: TILE_WALL blocks light.
            # We need to import TILE_WALL to be safe, or just rely on game_map methods.
            return game_map.is_transparent(c, r)
        return False

    def cast_light(cx, cy, row, start, end, radius, xx, xy, yx, yy, id):
        if start < end:
            return

        radius_sq = radius * radius

        for j in range(row, radius + 1):
            dx, dy = -j - 1, -j
            blocked = False

            while dx <= 0:
                dx += 1
                # Translate relative coordinates to map coordinates
                X, Y = cx + dx * xx + dy * xy, cy + dx * yx + dy * yy

                # Slope of the left and right edges of the current tile
                l_slope, r_slope = (dx - 0.5) / (dy + 0.5), (dx + 0.5) / (dy - 0.5)

                if start < r_slope:
                    continue
                elif end > l_slope:
                    break
                else:
                    # Check bounds
                    if 0 <= X < width and 0 <= Y < height:
                        # Check radius
                        if dx * dx + dy * dy < radius_sq:
                            visible[Y, X] = True

                    if blocked:
                        if not get_light(Y, X):
                            new_start = r_slope
                            if id < 4:  # Optimization/Logic check
                                cast_light(
                                    cx,
                                    cy,
                                    j + 1,
                                    start,
                                    l_slope,
                                    radius,
                                    xx,
                                    xy,
                                    yx,
                                    yy,
                                    id + 1,
                                )
                            else:
                                cast_light(
                                    cx,
                                    cy,
                                    j + 1,
                                    start,
                                    l_slope,
                                    radius,
                                    xx,
                                    xy,
                                    yx,
                                    yy,
                                    id + 1,
                                )
                            start = new_start
                            if (
                                start < end
                            ):  # Should not happen given loop condition but good for safety
                                return
                        else:
                            blocked = False
                            start = r_slope  # Tweak?
                    else:
                        if not get_light(Y, X) and j < radius:
                            blocked = True
                            cast_light(
                                cx,
                                cy,
                                j + 1,
                                start,
                                l_slope,
                                radius,
                                xx,
                                xy,
                                yx,
                                yy,
                                id + 1,
                            )
                            new_start = r_slope
                            start = new_start

            if blocked:
                break

    # Simple Symmetric Shadowcasting (Python implementation of a common algorithm)
    # Source adapted from various roguebasin/libtcod Python examples

    # 0: Octant 1
    # ...
    # This specific implementation is a bit complex to write from scratch without errors.
    # Let's use a simpler, cleaner recursive shadowcaster.

    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 0, -1, 0, 1, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 0, 1, 0, 1, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, -1, 0, 1, 0, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 1, 0, 1, 0, visible)

    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 0, -1, 0, -1, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 0, 1, 0, -1, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, -1, 0, -1, 0, visible)
    _cast_light_recursive(game_map, x, y, radius, 1, 1.0, 0.0, 1, 0, -1, 0, visible)

    return visible


def _cast_light_recursive(
    game_map, cx, cy, radius, row, start_slope, end_slope, xx, xy, yx, yy, visible
):
    if start_slope < end_slope:
        return

    radius_sq = radius * radius

    for j in range(row, radius + 1):
        dx = -j - 1
        dy = -j
        blocked = False

        while dx <= 0:
            dx += 1
            # Translate relative to map
            X, Y = cx + dx * xx + dy * xy, cy + dx * yx + dy * yy

            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)

            if start_slope < r_slope:
                continue
            elif end_slope > l_slope:
                break
            else:
                # Check bounds
                if 0 <= X < game_map.width and 0 <= Y < game_map.height:
                    if dx * dx + dy * dy < radius_sq:
                        visible[Y, X] = True

                # Check blocking
                # We need a safe way to check transparency
                is_transparent = False
                if 0 <= X < game_map.width and 0 <= Y < game_map.height:
                    is_transparent = game_map.is_transparent(X, Y)

                if blocked:
                    if is_transparent:
                        blocked = False
                        start_slope = r_slope
                    else:
                        pass
                else:
                    if not is_transparent and j < radius:
                        blocked = True
                        _cast_light_recursive(
                            game_map,
                            cx,
                            cy,
                            radius,
                            j + 1,
                            start_slope,
                            l_slope,
                            xx,
                            xy,
                            yx,
                            yy,
                            visible,
                        )
                        start_slope = r_slope

        if blocked:
            break
