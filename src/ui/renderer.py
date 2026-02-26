"""
Terminal rendering system for the roguelike game using rich.
"""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from typing import TYPE_CHECKING
import numpy as np
import shutil

if TYPE_CHECKING:
    from world.map import GameMap
    from core.ecs import EntityManager
    from entities.entities import EntityManagerWrapper


class Renderer:
    """Renders the game to the terminal using rich."""

    def __init__(self, console: Console, screen_width: int, screen_height: int):
        self.console = console
        # Use a slightly smaller width to avoid wrapping issues in some terminals
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Viewport dimensions (will be calculated dynamically)
        self.map_render_width = 23
        self.map_render_height = 13

        # Double buffering for efficient rendering
        # Initialize with enough space for current terminal
        max_shape = (max(200, self.screen_height), max(200, self.screen_width // 2))
        self.previous_frame = np.full(max_shape, "  ", dtype=object)
        self.previous_fg_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)
        self.previous_bg_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)

        # Current frame buffers
        self.fg_color_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)
        self.bg_color_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)

        # Flag to clear screen
        self.first_render = True
        self.needs_full_clear = False

        # Screen shake state
        self.shake_intensity = 0.0
        self.shake_end_time = 0.0

        # Camera tracking to force clear on move
        self._last_cam_x = -1
        self._last_cam_y = -1

    def _draw_text_packed(self, buffer, x, y, text, fg_color, max_width=None):
        """Draw text to the buffer, packing 2 chars per cell for normal width."""
        if len(text) % 2 != 0:
            text += " "

        pairs = [text[i : i + 2] for i in range(0, len(text), 2)]

        for i, pair in enumerate(pairs):
            bx = x + i
            if max_width and i >= max_width:
                break

            if 0 <= y < buffer.shape[0] and 0 <= bx < buffer.shape[1]:
                buffer[y, bx] = pair
                self.fg_color_buffer[y, bx] = fg_color

    def _draw_box(self, buffer, x, y, w, h, color):
        """Draw a box frame in cells."""
        # Horizontal lines
        for i in range(w):
            if 0 <= y < buffer.shape[0] and 0 <= x + i < buffer.shape[1]:
                buffer[y, x + i] = "=="
                self.fg_color_buffer[y, x + i] = color
            if 0 <= y + h - 1 < buffer.shape[0] and 0 <= x + i < buffer.shape[1]:
                buffer[y + h - 1, x + i] = "=="
                self.fg_color_buffer[y + h - 1, x + i] = color

        # Vertical lines
        for j in range(h):
            if 0 <= y + j < buffer.shape[0] and 0 <= x < buffer.shape[1]:
                buffer[y + j, x] = "||"
                self.fg_color_buffer[y + j, x] = color
            if 0 <= y + j < buffer.shape[0] and 0 <= x + w - 1 < buffer.shape[1]:
                buffer[y + j, x + w - 1] = "||"
                self.fg_color_buffer[y + j, x + w - 1] = color

    def trigger_shake(self, intensity: float, duration: float = 0.3):
        """Trigger a screen shake effect."""
        import time

        self.shake_intensity = intensity
        self.shake_end_time = time.time() + duration

    def render(
        self,
        game_map: "GameMap",
        entity_manager: "EntityManager",
        entity_wrapper: "EntityManagerWrapper",
        player_id: int,
        messages: list = None,
        game_state: str = "PLAYING",
        inventory_selection: int = 0,
        shop_id: int = None,
    ):
        """Render the current game state."""
        # Update dimensions to match current terminal size
        t_cols, t_lines = shutil.get_terminal_size()

        # Safety margin
        t_cols = max(40, t_cols - 2)
        t_lines = max(10, t_lines)

        # Handle Resize
        if t_cols != self.screen_width or t_lines != self.screen_height:
            self.screen_width = t_cols
            self.screen_height = t_lines
            self.needs_full_clear = True

            # Ensure buffers are large enough for new terminal size
            rows_needed = self.screen_height
            cols_needed = self.screen_width // 2
            current_max_rows, current_max_cols = self.previous_frame.shape

            if rows_needed > current_max_rows or cols_needed > current_max_cols:
                new_max_rows = max(rows_needed, current_max_rows)
                new_max_cols = max(cols_needed, current_max_cols)
                new_max_shape = (new_max_rows, new_max_cols)

                # Resize all buffers
                new_prev_frame = np.full(new_max_shape, "  ", dtype=object)
                new_prev_frame[:current_max_rows, :current_max_cols] = self.previous_frame
                self.previous_frame = new_prev_frame

                new_prev_fg = np.full((*new_max_shape, 3), -1, dtype=np.int16)
                new_prev_fg[:current_max_rows, :current_max_cols] = self.previous_fg_buffer
                self.previous_fg_buffer = new_prev_fg

                new_prev_bg = np.full((*new_max_shape, 3), -1, dtype=np.int16)
                new_prev_bg[:current_max_rows, :current_max_cols] = self.previous_bg_buffer
                self.previous_bg_buffer = new_prev_bg

                self.fg_color_buffer = np.full((*new_max_shape, 3), -1, dtype=np.int16)
                self.bg_color_buffer = np.full((*new_max_shape, 3), -1, dtype=np.int16)

        # --- Dynamic Viewport Logic (16:9) ---
        ui_reserve = 6  # Border + Stats + Skills + Messages

        # Avail width/height in CELLS
        avail_w = (self.screen_width // 2) - 4
        avail_h = self.screen_height - ui_reserve - 4

        # Best K for 16K x 9K
        k = min(avail_w / 16, avail_h / 9)
        if k < 1:
            k = 1

        self.map_render_width = int(16 * k)
        self.map_render_height = int(9 * k)

        # Total content block size
        content_w = self.map_render_width + 2
        content_h = self.map_render_height + ui_reserve

        # Center position
        start_x = max(0, ((self.screen_width // 2) - content_w) // 2)
        start_y = max(0, (self.screen_height - content_h) // 2)

        # Prepare Buffer
        shape = (self.screen_height, self.screen_width // 2)
        render_buffer = np.full(shape, "  ", dtype=object)
        self.fg_color_buffer[: shape[0], : shape[1]] = -1
        self.bg_color_buffer[: shape[0], : shape[1]] = -1

        # Camera
        from entities.components import Position
        import time

        player_pos = entity_manager.get_component(player_id, Position)
        camera_x, camera_y = 0, 0
        if player_pos:
            camera_x = player_pos.x - self.map_render_width // 2
            camera_y = player_pos.y - self.map_render_height // 2

            # Apply Screen Shake
            if time.time() < self.shake_end_time:
                shake_x = int(np.random.uniform(-1, 1) * self.shake_intensity)
                shake_y = int(np.random.uniform(-1, 1) * self.shake_intensity)
                camera_x += shake_x
                camera_y += shake_y

            camera_x = max(0, min(camera_x, game_map.width - self.map_render_width))
            camera_y = max(0, min(camera_y, game_map.height - self.map_render_height))

        # Force clear if camera moved significantly or screen resized
        if camera_x != self._last_cam_x or camera_y != self._last_cam_y:
            self._last_cam_x = camera_x
            self._last_cam_y = camera_y
            # We don't necessarily need a full ANSI clear (\033[2J), 
            # just wiping previous_frame will force redraw in _output_buffer
            self.needs_full_clear = True

        if self.first_render or self.needs_full_clear:
            self.first_render = False
            self.needs_full_clear = False
            # Fill with None to force a redraw of everything on the next frame
            self.previous_frame.fill(None)
            self.previous_fg_buffer.fill(-1)
            self.previous_bg_buffer.fill(-1)

        # Render visible frame/box
        self._draw_box(
            render_buffer, start_x, start_y, content_w, content_h, (100, 100, 100)
        )

        # Render Map & Entities
        self._render_map(render_buffer, game_map, camera_x, camera_y, start_x, start_y)
        self._render_entities(
            render_buffer,
            entity_manager,
            game_map,
            camera_x,
            camera_y,
            start_x,
            start_y,
        )

        # UI (inside the box)
        self._render_ui(
            render_buffer, entity_manager, player_id, messages, start_x, start_y
        )

        # Overlays
        if game_state == "INVENTORY":
            self._render_inventory(
                render_buffer, entity_manager, player_id, inventory_selection
            )
        elif game_state == "STATS":
            self._render_stats(
                render_buffer, entity_manager, player_id, inventory_selection
            )
        elif game_state == "HELP":
            self._render_help(render_buffer)
        elif game_state == "SHOPPING":
            self._render_shop(render_buffer, entity_manager, shop_id)

        # Output
        self._output_buffer(render_buffer)

    def _render_map(
        self,
        buffer: np.ndarray,
        game_map: "GameMap",
        cam_x: int,
        cam_y: int,
        offset_x: int = 1,
        offset_y: int = 1,
    ):
        """Render the game map to the buffer with camera offset using vectorized operations."""
        import time

        current_time = time.time()

        # Use the render dimensions which are calculated based on screen size
        render_w = self.map_render_width
        render_h = self.map_render_height

        # Calculate limits for the map slice
        y_end = min(cam_y + render_h, game_map.height)
        x_end = min(cam_x + render_w, game_map.width)

        slice_h = y_end - cam_y
        slice_w = x_end - cam_x

        if slice_h <= 0 or slice_w <= 0:
            return

        # Calculate offsets to center the map drawing in the buffer
        buffer_y_offset = offset_y + 1
        buffer_x_offset = offset_x + 1

        # Get map slice
        tiles_slice = game_map.tiles[cam_y:y_end, cam_x:x_end]
        visible_slice = game_map.visible[cam_y:y_end, cam_x:x_end]

        # Map to chars and colors (Very fast vectorized indexing)
        chars = game_map.tile_char_lookup[tiles_slice].copy()
        fg_colors = game_map.tile_fg_color_lookup[tiles_slice].copy()
        bg_colors = game_map.tile_bg_color_lookup[tiles_slice].copy()

        # Handle Procedural Grass Detail
        from world.map import TILE_GRASS, TILE_LAVA, TILE_WATER

        grass_mask = tiles_slice == TILE_GRASS
        if np.any(grass_mask):
            # Revert to normal solid green from 1st commit
            fg_colors[grass_mask] = [50, 200, 50]
            bg_colors[grass_mask] = [34, 160, 34]
            chars[grass_mask] = "  "

        # Handle Procedural Lava Texture
        lava_mask = tiles_slice == TILE_LAVA
        if np.any(lava_mask):
            t = current_time * 0.3  # Slow, viscous flow
            yy, xx = np.ogrid[cam_y:y_end, cam_x:x_end]

            # Dynamic flow with multiple octaves
            flow_1 = np.sin(xx * 0.2 + t * 0.5) * np.cos(yy * 0.3 - t * 0.3)
            flow_2 = np.sin(yy * 0.15 + t * 0.8) * np.cos(xx * 0.25 + t * 0.4)
            combined_flow = (flow_1 + flow_2 * 0.5 + 1.5) / 3.0

            heat_core = (
                np.sin(xx * 0.4 + combined_flow * 3.0 + t) * np.cos(yy * 0.5 - t * 0.6)
                + 1.0
            ) / 2.0

            crust_noise = ((xx * 31 + yy * 37) % 41) / 41.0
            is_crust = crust_noise > 0.65 + heat_core * 0.35

            # Glow pulse
            glow = 1.0 + np.sin(t * 1.5) * 0.1

            # Determine colors based on heat
            r_base = np.clip(60 + heat_core * 195, 0, 255).astype(np.int16)
            g_base = np.clip(heat_core**2 * 120 * glow, 0, 255).astype(np.int16)

            fg_colors[lava_mask, 0] = r_base[lava_mask]
            fg_colors[lava_mask, 1] = g_base[lava_mask]
            fg_colors[lava_mask, 2] = 0

            bg_colors[lava_mask, 0] = (r_base[lava_mask] // 3).astype(np.int16)
            bg_colors[lava_mask, 1] = (g_base[lava_mask] // 5).astype(np.int16)
            bg_colors[lava_mask, 2] = 0

            # Assign characters based on heat density (no 'oo')
            h_mask = lava_mask & (heat_core > 0.85)
            m_mask = lava_mask & (heat_core <= 0.85) & (heat_core > 0.6)
            l_mask = lava_mask & (heat_core <= 0.6) & (heat_core > 0.3)
            c_mask = lava_mask & (is_crust | (heat_core <= 0.3))

            chars[h_mask] = "██"  # Brightest core
            chars[m_mask] = "▓▓"  # Dense heat
            chars[l_mask] = "▒▒"  # Cooling lava
            chars[c_mask] = "░░"  # Thin crust/coolest regions

            # Extra dark crust patches
            dark_crust = c_mask & (crust_noise > 0.8)
            if np.any(dark_crust):
                fg_colors[dark_crust, 0] = 30
                fg_colors[dark_crust, 1] = 10
                bg_colors[dark_crust, 0] = 15
                bg_colors[dark_crust, 1] = 5
                chars[dark_crust] = "  "

        water_mask = tiles_slice == TILE_WATER
        if np.any(water_mask):
            # Viewport-independent shore detection using the full map
            # This prevents water tiles from changing color as they enter/leave the screen
            y_start = cam_y
            x_start = cam_x
            
            # Create a shore mask for the visible slice
            # A tile is "shallow" if it's water but adjacent to land
            full_is_land = game_map.tiles != TILE_WATER
            
            # Efficient neighbor check for the current slice
            # We use the full map's land-mask to avoid viewport edge artifacts
            land_slice = full_is_land[y_start:y_end, x_start:x_end]
            
            # Check neighbors in the full map
            near_land = np.zeros_like(land_slice, dtype=bool)
            if y_start > 0:
                near_land |= full_is_land[y_start-1:y_end-1, x_start:x_end]
            if y_end < game_map.height:
                near_land |= full_is_land[y_start+1:y_end+1, x_start:x_end]
            if x_start > 0:
                near_land |= full_is_land[y_start:y_end, x_start-1:x_end-1]
            if x_end < game_map.width:
                near_land |= full_is_land[y_start:y_end, x_start+1:x_end+1]
                
            shallows_mask = water_mask & near_land
            
            t = current_time * 0.8  # Slightly slower for smoother flow
            yy, xx = np.ogrid[y_start:y_end, x_start:x_end]

            # Simplified flow for stability
            flow = (np.sin(xx * 0.2 + t) * np.cos(yy * 0.2 - t * 0.5) + 1.0) / 2.0
            motion = (np.sin(xx * 0.1 + flow * 2.0) + 1.0) / 2.0

            def get_water_color(m, shallows):
                # Deep water: Dark blue-teal
                r_v = (15 + m * 10).astype(np.int16)
                g_v = (60 + m * 20).astype(np.int16)
                b_v = (130 + m * 40).astype(np.int16)

                if np.any(shallows):
                    # Shallow water: Blend towards grass/sand colors (more green/yellow)
                    s_mask = shallows
                    # Greener/lighter for the shore
                    r_v[s_mask] = (40 + m[s_mask] * 15).astype(np.int16)
                    g_v[s_mask] = (120 + m[s_mask] * 30).astype(np.int16)
                    b_v[s_mask] = (140 + m[s_mask] * 20).astype(np.int16)
                return r_v, g_v, b_v

            r_f, g_f, b_f = get_water_color(motion[water_mask], shallows_mask[water_mask])

            # Foreground and Background synced for solid liquid look
            fg_colors[water_mask, 0] = r_f
            fg_colors[water_mask, 1] = g_f
            fg_colors[water_mask, 2] = b_f
            bg_colors[water_mask, 0] = r_f
            bg_colors[water_mask, 1] = g_f
            bg_colors[water_mask, 2] = b_f

            # Use pure background color
            chars[water_mask] = "  "

        # Handle Procedural Sand Dunes
        from world.map import TILE_SAND, TILE_CACTUS

        sand_mask = (tiles_slice == TILE_SAND) | (tiles_slice == TILE_CACTUS)
        if np.any(sand_mask):
            t = current_time * 0.2
            yy, xx = np.ogrid[cam_y:y_end, cam_x:x_end]

            # Broad, slow sweeps for dunes to avoid pixelation
            dune_wave = (
                np.sin(xx * 0.04 + t * 0.5) * 0.5
                + np.cos(yy * 0.03 - t * 0.3) * 0.5
                + 1.0
            ) / 2.0

            def get_sand_color(d):
                # Classic golden desert colors from 1st commit
                r = np.clip(210 + d * 20, 0, 255).astype(np.int16)
                g = np.clip(190 + d * 15, 0, 255).astype(np.int16)
                b = np.clip(120 + d * 10, 0, 255).astype(np.int16)
                return r, g, b

            r_s, g_s, b_s = get_sand_color(dune_wave[sand_mask])

            bg_colors[sand_mask, 0] = r_s
            bg_colors[sand_mask, 1] = g_s
            bg_colors[sand_mask, 2] = b_s

            # Pure color sand - no characters
            chars[sand_mask] = "  "

            # Ensure TILE_CACTUS keeps its character
            cactus_only = sand_mask & (tiles_slice == TILE_CACTUS)
            if np.any(cactus_only):
                chars[cactus_only] = "ψ "
                fg_colors[cactus_only, 0] = 100
                fg_colors[cactus_only, 1] = 220
                fg_colors[cactus_only, 2] = 100

        # Handle Procedural Floor Texture
        floor_mask = tiles_slice == 0
        if np.any(floor_mask):
            yy, xx = np.ogrid[cam_y:y_end, cam_x:x_end]

            # Better stone variety and large-scale wear
            stone_noise = ((xx * 17 + yy * 23) % 29) / 29.0
            wear_large = (np.sin(xx * 0.15) * np.cos(yy * 0.1) + 1.0) / 2.0

            # Base stone colors
            base_val = 85 + stone_noise * 30 - wear_large * 15
            fg_colors[floor_mask, 0] = base_val[floor_mask].astype(np.int16)
            fg_colors[floor_mask, 1] = (base_val[floor_mask] - 2).astype(np.int16)
            fg_colors[floor_mask, 2] = (base_val[floor_mask] - 5).astype(np.int16)

            bg_colors[floor_mask, 0] = (base_val[floor_mask] // 3).astype(np.int16)
            bg_colors[floor_mask, 1] = (base_val[floor_mask] // 3).astype(np.int16)
            bg_colors[floor_mask, 2] = (base_val[floor_mask] // 3 + 2).astype(np.int16)

            # Grout/Grid (4x4 tiles)
            tile_grid = ((xx - cam_x) % 4 == 0) | ((yy - cam_y) % 4 == 0)
            if np.any(tile_grid):
                g_mask = floor_mask & tile_grid
                fg_colors[g_mask] = np.clip(fg_colors[g_mask] - 30, 20, 255)
                bg_colors[g_mask] = np.clip(bg_colors[g_mask] - 10, 10, 255)
                chars[g_mask] = "░░"

            # Worn patches
            worn_stone = floor_mask & (stone_noise > 0.85)
            if np.any(worn_stone):
                chars[worn_stone] = "· "

        # Handle Procedural Wall Texture
        wall_mask = tiles_slice == 1
        if np.any(wall_mask):
            # Original solid wall style
            fg_colors[wall_mask] = [80, 80, 90]
            bg_colors[wall_mask] = [20, 20, 25]
            chars[wall_mask] = "██"

        # Handle Visibility/Exploration
        if game_map.is_dark:
            yy, xx = np.ogrid[cam_y:y_end, cam_x:x_end]
            px, py = cam_x + render_w // 2, cam_y + render_h // 2
            dist_sq = (xx - px) ** 2 + (yy - py) ** 2
            light_radius = 12
            max_dist_sq = light_radius**2
            light_level = np.clip(1.0 - (dist_sq / max_dist_sq), 0.2, 1.0) ** 1.5
            fg_colors[:, :, 0] = (fg_colors[:, :, 0] * light_level).astype(np.int16)
            fg_colors[:, :, 1] = (fg_colors[:, :, 1] * light_level).astype(np.int16)
            fg_colors[:, :, 2] = (fg_colors[:, :, 2] * light_level).astype(np.int16)
            bg_mask = bg_colors[:, :, 0] != -1
            bg_colors[bg_mask, 0] = (
                bg_colors[bg_mask, 0] * light_level[bg_mask]
            ).astype(np.int16)
            bg_colors[bg_mask, 1] = (
                bg_colors[bg_mask, 1] * light_level[bg_mask]
            ).astype(np.int16)
            bg_colors[bg_mask, 2] = (
                bg_colors[bg_mask, 2] * light_level[bg_mask]
            ).astype(np.int16)

            not_visible = ~visible_slice
            if np.any(not_visible):
                explored_slice = game_map.explored[cam_y:y_end, cam_x:x_end]
                dim_mask = not_visible & explored_slice
                if np.any(dim_mask):
                    fg_colors[dim_mask] = np.maximum(0, fg_colors[dim_mask] - 100)
                hide_mask = not_visible & ~explored_slice
                if np.any(hide_mask):
                    chars[hide_mask] = "  "
                    fg_colors[hide_mask] = 0
                    bg_colors[hide_mask] = -1

        # Assign to buffers
        by_end = buffer_y_offset + slice_h
        bx_end = buffer_x_offset + slice_w
        if by_end > self.screen_height:
            by_end = self.screen_height
            chars = chars[: by_end - buffer_y_offset, :]
            fg_colors = fg_colors[: by_end - buffer_y_offset, :]
            bg_colors = bg_colors[: by_end - buffer_y_offset, :]
        if bx_end > self.screen_width // 2:
            bx_end = self.screen_width // 2
            chars = chars[:, : bx_end - buffer_x_offset]
            fg_colors = fg_colors[:, : bx_end - buffer_x_offset]
            bg_colors = bg_colors[:, : bx_end - buffer_x_offset]

        buffer[buffer_y_offset:by_end, buffer_x_offset:bx_end] = chars
        self.fg_color_buffer[buffer_y_offset:by_end, buffer_x_offset:bx_end] = fg_colors
        self.bg_color_buffer[buffer_y_offset:by_end, buffer_x_offset:bx_end] = bg_colors

    def _render_entities(
        self,
        buffer: np.ndarray,
        entity_manager: "EntityManager",
        game_map: "GameMap",
        cam_x: int,
        cam_y: int,
        offset_x: int = 1,
        offset_y: int = 1,
    ):
        """Render entities to the buffer with camera offset."""
        # Import the actual component classes
        from entities.components import Position, Render

        # Get all entities with Position and Render components
        entities_with_pos = set(
            entity_manager.get_all_entities_with_component(Position)
        )
        entities_with_render = set(
            entity_manager.get_all_entities_with_component(Render)
        )

        # Find entities that have both components
        entities_to_render = entities_with_pos.intersection(entities_with_render)

        buffer_x_offset = offset_x + 1
        buffer_y_offset = offset_y + 1

        for eid in entities_to_render:
            pos_comp = entity_manager.get_component(eid, Position)
            render_comp = entity_manager.get_component(eid, Render)

            if pos_comp and render_comp:
                # Calculate screen position relative to camera
                screen_x = pos_comp.x - cam_x
                screen_y = pos_comp.y - cam_y

                # Check if visible on screen
                if (
                    0 <= screen_x < self.map_render_width
                    and 0 <= screen_y < self.map_render_height
                ):
                    # Apply buffer offset
                    buffer_x = screen_x + buffer_x_offset
                    buffer_y = screen_y + buffer_y_offset

                    if (
                        0 <= buffer_x < self.screen_width // 2
                        and 0 <= buffer_y < self.screen_height
                    ):
                        buffer[buffer_y, buffer_x] = render_comp.char
                        self.fg_color_buffer[buffer_y, buffer_x] = render_comp.fg_color
                        if render_comp.bg_color:
                            self.bg_color_buffer[buffer_y, buffer_x] = (
                                render_comp.bg_color
                            )

    def _draw_bar(self, buffer, x, y, width, current, maximum, fg_color, bg_color):
        """Draw a progress bar using packed characters."""
        if width < 3:
            return

        # Draw frame
        if 0 <= y < self.screen_height - 1 and 0 <= x < self.screen_width // 2:
            buffer[y, x] = "[ "
        if (
            0 <= y < self.screen_height - 1
            and 0 <= x + width - 1 < self.screen_width // 2
        ):
            buffer[y, x + width - 1] = " ]"

        # Content width (in cells)
        content_width = width - 2

        ratio = max(0.0, min(1.0, current / maximum)) if maximum > 0 else 0
        fill_cells = int(content_width * ratio)

        for i in range(content_width):
            bx = x + 1 + i
            if 0 <= y < self.screen_height - 1 and 0 <= bx < self.screen_width // 2:
                if i < fill_cells:
                    buffer[y, bx] = "=="
                    self.fg_color_buffer[y, bx] = fg_color
                else:
                    buffer[y, bx] = ".."
                    self.fg_color_buffer[y, bx] = bg_color

    def _render_shop(
        self,
        buffer: np.ndarray,
        entity_manager: "EntityManager",
        shop_id: int,
    ):
        """Render the shop window overlay."""
        from entities.components import Shop

        # Window dimensions
        win_w = 40
        win_h = 30

        # Center the window
        buffer_w = self.screen_width // 2
        start_x = (buffer_w - win_w) // 2
        start_y = (self.screen_height - win_h) // 2

        # Clamp
        if start_x < 0:
            start_x = 0
        if start_y < 0:
            start_y = 0

        # Draw Window Frame
        for y in range(win_h):
            for x in range(win_w):
                bx = start_x + x
                by = start_y + y

                if 0 <= bx < buffer_w and 0 <= by < self.screen_height - 1:
                    # Clear background
                    buffer[by, bx] = " "
                    self.fg_color_buffer[by, bx] = (255, 255, 255)
                    self.bg_color_buffer[by, bx] = (30, 10, 10)  # Dark Red/Brown BG

                    # Borders
                    if x == 0 or x == win_w - 1 or y == 0 or y == win_h - 1:
                        buffer[by, bx] = "$"
                        self.fg_color_buffer[by, bx] = (255, 215, 0)

        # Get Shop Data
        shop = None
        if shop_id is not None:
            shop = entity_manager.get_component(shop_id, Shop)

        title = shop.shop_name if shop else "Shop"

        # Title
        for i, char in enumerate(title):
            if start_x + 2 + i < buffer_w:
                buffer[start_y, start_x + 2 + i] = char

        # List Items
        if shop:
            for i, (item_name, price) in enumerate(shop.items):
                item_y = start_y + 2 + i
                if item_y >= start_y + win_h - 1:
                    break

                # Draw Item Name and Price
                text = f"{item_name}: {price}g"

                for j, char in enumerate(text):
                    bx = start_x + 2 + j
                    if (
                        bx < start_x + win_w - 1
                        and 0 <= item_y < self.screen_height - 1
                    ):
                        buffer[item_y, bx] = char
                        self.fg_color_buffer[item_y, bx] = (200, 200, 200)
        else:
            buffer[start_y + 2, start_x + 2] = "Shop Closed"

    def _render_help(self, buffer: np.ndarray):
        """Render the help screen overlay."""
        # Window dimensions
        win_w = 46
        win_h = 28

        # Center the window
        buffer_w = self.screen_width // 2
        start_x = (buffer_w - win_w) // 2
        start_y = (self.screen_height - win_h) // 2

        # Draw Window Frame
        for y in range(win_h):
            for x in range(win_w):
                bx = start_x + x
                by = start_y + y
                if 0 <= bx < buffer_w and 0 <= by < self.screen_height - 1:
                    buffer[by, bx] = " "
                    self.bg_color_buffer[by, bx] = (30, 30, 40)
                    if x == 0 or x == win_w - 1 or y == 0 or y == win_h - 1:
                        buffer[by, bx] = "*"
                        self.fg_color_buffer[by, bx] = (200, 200, 100)

        # Title
        title = " TERMINUS REALM - CONTROLS "
        for i, char in enumerate(title):
            if start_x + (win_w - len(title)) // 2 + i < buffer_w:
                buffer[start_y, start_x + (win_w - len(title)) // 2 + i] = char

        controls = [
            ("WASD/Arrows/Vi/Num", "Movement"),
            ("QEZC / YUBN / 1-9", "Diagonal Movement"),
            ("Enter/Space/x", "Select/Interact"),
            ("Space / o", "Action Menu / Attack"),
            ("i / I", "Toggle Inventory"),
            ("C / K (Shift)", "Stat Allocation"),
            ("g / ,", "Pick up Item"),
            ("t / f", "Target/Fire Weapon"),
            (". / 5", "Wait/Rest"),
            ("1, 2, 3", "Cast Skills"),
            ("?", "Show this Help"),
            ("Esc / p / Q", "Quit Game"),
        ]

        for i, (key, desc) in enumerate(controls):
            y = start_y + 2 + i * 2
            if y >= start_y + win_h - 1:
                break

            # Key
            for j, char in enumerate(key):
                bx = start_x + 2 + j
                if bx < buffer_w:
                    buffer[y, bx] = char
                    self.fg_color_buffer[y, bx] = (255, 255, 100)

            # Desc
            for j, char in enumerate(" : " + desc):
                bx = start_x + 2 + len(key) + j
                if bx < buffer_w:
                    buffer[y, bx] = char
                    self.fg_color_buffer[y, bx] = (200, 200, 200)

        # Footer
        footer = " Press any key to return "
        for i, char in enumerate(footer):
            bx = start_x + (win_w - len(footer)) // 2 + i
            by = start_y + win_h - 2
            if bx < buffer_w:
                buffer[by, bx] = char
                self.fg_color_buffer[by, bx] = (150, 150, 150)

    def _render_stats(
        self,
        buffer: np.ndarray,
        entity_manager: "EntityManager",
        player_id: int,
        selection: int,
    ):
        """Render the stat allocation window overlay."""
        from entities.components import Level, Combat, Health, Mana

        # Window dimensions
        win_w = 40
        win_h = 20

        # Center the window
        buffer_w = self.screen_width // 2
        start_x = (buffer_w - win_w) // 2
        start_y = (self.screen_height - win_h) // 2

        # Draw Window Frame
        for y in range(win_h):
            for x in range(win_w):
                bx = start_x + x
                by = start_y + y
                if 0 <= bx < buffer_w and 0 <= by < self.screen_height - 1:
                    buffer[by, bx] = " "
                    self.bg_color_buffer[by, bx] = (20, 40, 20)  # Dark Green BG
                    if x == 0 or x == win_w - 1 or y == 0 or y == win_h - 1:
                        buffer[by, bx] = "+"
                        self.fg_color_buffer[by, bx] = (50, 200, 50)

        # Title
        title = " STAT ALLOCATION "
        for i, char in enumerate(title):
            if start_x + 2 + i < buffer_w:
                buffer[start_y, start_x + 2 + i] = char

        level_comp = entity_manager.get_component(player_id, Level)
        combat = entity_manager.get_component(player_id, Combat)
        health = entity_manager.get_component(player_id, Health)
        mana = entity_manager.get_component(player_id, Mana)

        if not level_comp:
            return

        # Points available
        pts_text = f"Points Available: {level_comp.attribute_points}"
        for i, char in enumerate(pts_text):
            if start_x + 2 + i < buffer_w:
                buffer[start_y + 2, start_x + 2 + i] = char
                self.fg_color_buffer[start_y + 2, start_x + 2 + i] = (255, 215, 0)

        # Stats to increase
        stats = [
            ("Strength (Atk+2)", combat.attack_power if combat else 0),
            ("Dexterity (Def+1)", combat.defense if combat else 0),
            ("Vitality (HP+20)", health.maximum if health else 0),
            ("Intelligence (MP+15)", mana.maximum if mana else 0),
        ]

        for i, (name, val) in enumerate(stats):
            y = start_y + 5 + i * 2
            prefix = "> " if i == selection else "  "
            text = f"{prefix}{name}: {val}"
            color = (255, 255, 255) if i != selection else (255, 255, 0)

            for j, char in enumerate(text):
                bx = start_x + 4 + j
                if bx < start_x + win_w - 1:
                    buffer[y, bx] = char
                    self.fg_color_buffer[y, bx] = color

        # Help text
        help_text = "Use WASD/Arrows to move, E/Space to allocate"
        for i, char in enumerate(help_text):
            bx = start_x + 2 + i
            by = start_y + win_h - 2
            if bx < buffer_w:
                buffer[by, bx] = char
                self.fg_color_buffer[by, bx] = (150, 150, 150)

    def _render_inventory(
        self,
        buffer: np.ndarray,
        entity_manager: "EntityManager",
        player_id: int,
        selection: int,
    ):
        """Render the inventory window overlay."""
        from entities.components import Inventory, Item, Equipment

        # Window dimensions
        win_w = 40
        win_h = 30

        # Center the window
        # Buffer width is screen_width // 2
        buffer_w = self.screen_width // 2
        start_x = (buffer_w - win_w) // 2
        start_y = (self.screen_height - win_h) // 2

        # Clamp
        if start_x < 0:
            start_x = 0
        if start_y < 0:
            start_y = 0

        # Draw Window Frame
        for y in range(win_h):
            for x in range(win_w):
                bx = start_x + x
                by = start_y + y

                if 0 <= bx < buffer_w and 0 <= by < self.screen_height - 1:
                    # Clear background
                    buffer[by, bx] = " "
                    self.fg_color_buffer[by, bx] = (255, 255, 255)
                    self.bg_color_buffer[by, bx] = (10, 10, 30)  # Dark Blue/Black BG

                    # Borders
                    if x == 0 or x == win_w - 1 or y == 0 or y == win_h - 1:
                        buffer[by, bx] = "#"
                        self.fg_color_buffer[by, bx] = (100, 100, 200)

        # Title
        title = " INVENTORY "
        for i, char in enumerate(title):
            if start_x + 2 + i < buffer_w:
                buffer[start_y, start_x + 2 + i] = char

        # Display Equipped Items
        equip = entity_manager.get_component(player_id, Equipment)
        equip_y = start_y + 2

        if equip:
            def get_item_name(eid):
                if eid is None:
                    return "None"
                it = entity_manager.get_component(eid, Item)
                return it.name if it else "Unknown"

            # Draw equipment slots
            slots = [
                (f"Wpn: {get_item_name(equip.weapon)} ({equip.weapon_type})"),
                (f"Head: {get_item_name(equip.head)}"),
                (f"Body: {get_item_name(equip.body)}"),
                (f"Legs: {get_item_name(equip.legs)}"),
                (f"Shield: {get_item_name(equip.shield)}")
            ]

            for i, text in enumerate(slots):
                for j, char in enumerate(text):
                    if start_x + 2 + j < buffer_w:
                        buffer[equip_y + i, start_x + 2 + j] = char
                        self.fg_color_buffer[equip_y + i, start_x + 2 + j] = (100, 200, 255)

            equip_y += len(slots) + 1  # Add spacing

        # List Items
        inv = entity_manager.get_component(player_id, Inventory)

        if inv:
            for i, item_id in enumerate(inv.items):
                item_y = equip_y + i
                if item_y >= start_y + win_h - 1:
                    break

                item_comp = entity_manager.get_component(item_id, Item)
                if not item_comp:
                    continue

                # Draw Item Name
                prefix = "> " if i == selection else "  "
                name = f"{prefix}{item_comp.char} {item_comp.name}"

                color = item_comp.color
                if i == selection:
                    color = (255, 255, 0)  # Highlight selected

                for j, char in enumerate(name):
                    bx = start_x + 2 + j
                    if (
                        bx < start_x + win_w - 1
                        and 0 <= item_y < self.screen_height - 1
                    ):
                        buffer[item_y, bx] = char
                        self.fg_color_buffer[item_y, bx] = color

            # Capacity Info
            cap_info = f"Capacity: {len(inv.items)}/{inv.capacity}"
            for i, char in enumerate(cap_info):
                bx = start_x + 2 + i
                by = start_y + win_h - 2
                if bx < buffer_w and 0 <= by < self.screen_height - 1:
                    buffer[by, bx] = char
                    self.fg_color_buffer[by, bx] = (150, 150, 150)
        else:
            buffer[equip_y, start_x + 2] = "No Inventory Component!"

    def _render_ui(
        self,
        buffer: np.ndarray,
        entity_manager: "EntityManager",
        player_id: int,
        messages: list = None,
        offset_x: int = 1,
        offset_y: int = 1,
    ):
        """Render UI elements to the buffer."""
        from entities.components import Health, Mana, Position, Level, Skills

        # Use the map render width plus borders for UI width
        buffer_width = self.map_render_width + 2

        # Draw a border between map and UI
        # UI starts at offset_y + self.map_render_height + 1
        ui_y = offset_y + self.map_render_height + 1
        for x in range(buffer_width):
            bx = offset_x + x
            if 0 <= ui_y < self.screen_height - 1 and 0 <= bx < self.screen_width // 2:
                buffer[ui_y, bx] = "--"

        # Get player info
        player_pos = entity_manager.get_component(player_id, Position)
        player_health = entity_manager.get_component(player_id, Health)
        player_mana = entity_manager.get_component(player_id, Mana)
        player_level = entity_manager.get_component(player_id, Level)
        player_skills = entity_manager.get_component(player_id, Skills)

        # Draw Stats
        stats_y = ui_y + 1
        if stats_y < self.screen_height - 1:
            # Level and Position
            info = f"Lvl {player_level.current_level if player_level else 1}"
            if player_pos:
                info += f" ({player_pos.x},{player_pos.y})"

            self._draw_text_packed(buffer, offset_x + 1, stats_y, info, (255, 255, 255))

            # HP Bar
            if player_health:
                self._draw_bar(
                    buffer,
                    offset_x + 12,
                    stats_y,
                    8,
                    player_health.current,
                    player_health.maximum,
                    (255, 50, 50),
                    (100, 0, 0),
                )

            # MP Bar
            if player_mana:
                self._draw_bar(
                    buffer,
                    offset_x + 22,
                    stats_y,
                    8,
                    player_mana.current,
                    player_mana.maximum,
                    (50, 100, 255),
                    (0, 0, 100),
                )

            # XP Bar
            if player_level:
                self._draw_bar(
                    buffer,
                    offset_x + 32,
                    stats_y,
                    8,
                    player_level.current_xp,
                    player_level.xp_to_next_level,
                    (255, 215, 0),
                    (100, 80, 0),
                )

        # Draw Skills Line
        skills_y = stats_y + 1
        if player_skills and skills_y < self.screen_height - 1:
            skill_info = f"M:{player_skills.melee} D:{player_skills.distance} Mg:{player_skills.magic}"
            self._draw_text_packed(
                buffer, offset_x + 1, skills_y, skill_info, (200, 200, 255)
            )

        # Draw Message Log (shifted down by 1 line)
        log_start_y = skills_y + 1
        if messages and log_start_y < self.screen_height - 1:
            for i, (msg, color) in enumerate(reversed(messages)):
                y = log_start_y + i
                if y >= self.screen_height - 1:
                    break

                self._draw_text_packed(
                    buffer, offset_x + 1, y, msg, color, max_width=buffer_width - 2
                )

    def _output_buffer(self, buffer: np.ndarray):
        """Output the render buffer to the terminal using stable incremental updates."""
        import sys

        # Initial output sequence
        render_commands = []

        # Optimization: Cache last color to reduce escape codes
        last_fg = (-1, -1, -1)
        last_bg = (-1, -1, -1)

        # Track virtual cursor position to avoid redundant moves
        v_cursor_y = -1
        v_cursor_x = -1

        rows, cols = buffer.shape
        t_size = shutil.get_terminal_size()
        max_cols = t_size.columns
        max_rows = t_size.lines

        # Limit to terminal size
        rows = min(rows, max_rows)
        cols = min(cols, max_cols // 2)

        for y in range(rows):
            for x in range(cols):
                char = buffer[y, x]
                fg = tuple(self.fg_color_buffer[y, x])
                bg = tuple(self.bg_color_buffer[y, x])

                # Use .get() or slice safely to compare with previous frame
                prev_char = self.previous_frame[y, x]
                prev_fg = tuple(self.previous_fg_buffer[y, x])
                prev_bg = tuple(self.previous_bg_buffer[y, x])

                # Check if tile changed
                if char != prev_char or fg != prev_fg or bg != prev_bg:
                    # Target screen column (1-based)
                    screen_col = x * 2 + 1

                    # Skip if would exceed terminal width
                    if screen_col + 1 > max_cols:
                        continue

                    # Move cursor if not at the current tile
                    if y != v_cursor_y or x != v_cursor_x:
                        render_commands.append(f"\033[{y+1};{screen_col}H")

                    # Update colors if changed
                    if fg != last_fg:
                        if fg[0] == -1:
                            render_commands.append("\033[39m")
                        else:
                            render_commands.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m")
                        last_fg = fg

                    if bg != last_bg:
                        if bg[0] == -1:
                            render_commands.append("\033[49m")
                        else:
                            render_commands.append(f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                        last_bg = bg

                    # Render and enforce 2-column width
                    if len(char) == 1:
                        if ord(char) > 126:
                            # Emoji/Wide char - most terms handle as width 2
                            render_commands.append(char)
                            # Emojis often cause drift; force a cursor move for the next cell
                            v_cursor_x = -1 
                        else:
                            # ASCII - pad to width 2
                            render_commands.append(char + " ")
                            v_cursor_x = x + 1
                    elif len(char) == 2:
                        render_commands.append(char)
                        v_cursor_x = x + 1
                    else:
                        render_commands.append(char[:2])
                        v_cursor_x = -1

                    v_cursor_y = y

        # Save state
        self.previous_frame[:rows, :cols] = buffer[:rows, :cols]
        self.previous_fg_buffer[:rows, :cols] = self.fg_color_buffer[:rows, :cols]
        self.previous_bg_buffer[:rows, :cols] = self.bg_color_buffer[:rows, :cols]

        # Reset colors and flush
        render_commands.append("\033[0m")
        sys.stdout.write("".join(render_commands))
        sys.stdout.flush()

    def render_simple_map(self, game_map: "GameMap"):
        """Simple map rendering for debugging."""
        # Create a text object to hold the map
        map_text = Text()

        for y in range(game_map.height):
            for x in range(game_map.width):
                char = game_map.get_tile_char(x, y)
                fg_color = game_map.get_tile_fg_color(x, y)

                # Convert RGB to rich color format
                color_str = f"rgb({fg_color[0]},{fg_color[1]},{fg_color[2]})"
                map_text.append(char, style=f"bold {color_str}")

            # Add newline after each row
            map_text.append("\n")

        # Print the map in a panel
        panel = Panel(map_text, title="Dungeon Map", border_style="blue")
        self.console.print(panel)
