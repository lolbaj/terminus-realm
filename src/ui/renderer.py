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
        # Initialize with enough space for a large terminal
        max_shape = (200, 200)
        self.previous_frame = np.full(max_shape, " ", dtype=object)
        self.previous_fg_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)
        self.previous_bg_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)

        # Current frame buffers
        self.fg_color_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)
        self.bg_color_buffer = np.full((*max_shape, 3), -1, dtype=np.int16)

        # Flag to clear screen
        self.first_render = True
        self.needs_full_clear = False

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

        if self.first_render or self.needs_full_clear:
            print("\033[2J\033[H", end="", flush=True)
            self.first_render = False
            self.needs_full_clear = False
            # Wipe previous frame to force redraw
            self.previous_frame.fill(" ")

        # --- Dynamic Viewport Logic (16:9) ---
        ui_reserve = 6  # Border + Stats + Skills + Messages

        # Avail width/height in CELLS
        # Increase margin to -4 (2 cells/4 chars on each side) to prevent touching edges
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

        player_pos = entity_manager.get_component(player_id, Position)
        camera_x, camera_y = 0, 0
        if player_pos:
            camera_x = player_pos.x - self.map_render_width // 2
            camera_y = player_pos.y - self.map_render_height // 2
            camera_x = max(0, min(camera_x, game_map.width - self.map_render_width))
            camera_y = max(0, min(camera_y, game_map.height - self.map_render_height))

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
        """Render the game map to the buffer with camera offset."""
        # Use the render dimensions which are calculated based on screen size
        render_w = self.map_render_width
        render_h = self.map_render_height

        # Calculate offsets to center the map drawing in the buffer
        buffer_x_offset = offset_x + 1
        buffer_y_offset = offset_y + 1

        for y in range(render_h):
            for x in range(render_w):
                # Map coordinates
                map_x = x + cam_x
                map_y = y + cam_y

                # Check bounds
                if 0 <= map_x < game_map.width and 0 <= map_y < game_map.height:
                    # Check visibility
                    is_visible = False
                    if (
                        0 <= map_x < game_map.visible.shape[1]
                        and 0 <= map_y < game_map.visible.shape[0]
                    ):
                        is_visible = game_map.visible[map_y, map_x]

                    # Get char
                    char = game_map.get_tile_char(map_x, map_y, visible=is_visible)
                    fg_color = game_map.get_tile_fg_color(
                        map_x, map_y, visible=is_visible
                    )

                    # Get bg color if available
                    bg_color = None
                    if 0 <= map_x < game_map.width and 0 <= map_y < game_map.height:
                        tile_def = game_map.tile_definitions[
                            game_map.tiles[map_y, map_x]
                        ]
                        bg_color = tile_def.bg_color

                    # Draw to buffer
                    buffer_y = y + buffer_y_offset
                    buffer_x = x + buffer_x_offset

                    if (
                        0 <= buffer_y < self.screen_height
                        and 0 <= buffer_x < self.screen_width // 2
                    ):
                        buffer[buffer_y, buffer_x] = char
                        self.fg_color_buffer[buffer_y, buffer_x] = fg_color
                        if bg_color:
                            self.bg_color_buffer[buffer_y, buffer_x] = bg_color

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

        # List Items
        inv = entity_manager.get_component(player_id, Inventory)
        equip = entity_manager.get_component(player_id, Equipment)

        if inv:
            for i, item_id in enumerate(inv.items):
                item_y = start_y + 2 + i
                if item_y >= start_y + win_h - 1:
                    break

                item_comp = entity_manager.get_component(item_id, Item)
                if not item_comp:
                    continue

                # Check if equipped
                is_equipped = False
                if equip and equip.weapon == item_comp.name:  # Simplified check
                    is_equipped = True

                # Draw Item Name
                prefix = "> " if i == selection else "  "
                suffix = " (E)" if is_equipped else ""
                name = f"{prefix}{item_comp.char} {item_comp.name}{suffix}"

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
            buffer[start_y + 2, start_x + 2] = "No Inventory Component!"

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
        from entities.components import Health, Position, Level, Skills

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

            # XP Bar
            if player_level:
                self._draw_bar(
                    buffer,
                    offset_x + 22,
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
        """Output the render buffer to the terminal using incremental updates."""
        import sys
        
        # Hide cursor
        output_parts = ["\033[?25l"]

        # Cache last color to reduce escape codes
        last_fg = (-1, -1, -1)
        last_bg = (-1, -1, -1)

        # Track virtual cursor position
        v_cursor_y = -1
        v_cursor_x = -1

        rows, cols = buffer.shape
        max_cols = shutil.get_terminal_size().columns

        for y in range(rows):
            for x in range(cols):
                char = buffer[y, x]
                fg = tuple(self.fg_color_buffer[y, x])
                bg = tuple(self.bg_color_buffer[y, x])

                prev_char = self.previous_frame[y, x]
                prev_fg = tuple(self.previous_fg_buffer[y, x])
                prev_bg = tuple(self.previous_bg_buffer[y, x])

                # Check if cell changed or if we need to force sync
                if char != prev_char or fg != prev_fg or bg != prev_bg:
                    # Target screen column (1-based)
                    screen_col = x * 2 + 1

                    # Skip if would exceed terminal width
                    if screen_col + 1 > max_cols:
                        continue

                    # Move cursor if drift detected or new line
                    if y != v_cursor_y or x != v_cursor_x:
                        output_parts.append(f"\033[{y+1};{screen_col}H")

                    # Update foreground color
                    if fg != last_fg:
                        if fg[0] == -1:
                            output_parts.append("\033[39m")
                        else:
                            output_parts.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m")
                        last_fg = fg

                    # Update background color
                    if bg != last_bg:
                        if bg[0] == -1:
                            output_parts.append("\033[49m")
                        else:
                            output_parts.append(f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                        last_bg = bg

                    # Render and enforce 2-column width
                    # Python len() counts characters; we need to handle emojis (width 2) 
                    # vs ASCII (width 1).
                    if len(char) == 1:
                        if ord(char) > 126:
                            # Emoji or Unicode - assume width 2 (Standard for most modern terms)
                            output_parts.append(char)
                            # Emojis often cause drift; force a cursor move for the next cell
                            v_cursor_x = -1 
                        else:
                            # Standard ASCII - pad to width 2
                            output_parts.append(char + " ")
                            v_cursor_x = x + 1
                    elif len(char) == 2:
                        output_parts.append(char)
                        v_cursor_x = x + 1
                    else:
                        # Fallback for weird cases
                        output_parts.append(char[:2])
                        v_cursor_x = -1

                    v_cursor_y = y

        # Save state
        self.previous_frame[:rows, :cols] = buffer
        self.previous_fg_buffer[:rows, :cols] = self.fg_color_buffer[:rows, :cols]
        self.previous_bg_buffer[:rows, :cols] = self.bg_color_buffer[:rows, :cols]

        # Reset state and flush
        output_parts.append("\033[0m")
        sys.stdout.write("".join(output_parts))
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
