#!/usr/bin/env python3
"""
Terminus Realm Map Editor - Final Modular Version
"""

import sys
import os
import termios
import tty
import select
import fcntl
import shutil

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from map_editor.models import EditorMode
from map_editor.palette import TILE_PALETTE, CATEGORIES, get_category_layout
from map_editor.renderer import Renderer
from map_editor.map_manager import MapManager
from map_editor.undo_manager import UndoManager
from map_editor.prefab_manager import PrefabManager
from map_editor.input_handler import InputHandler
from map_editor import tools

# ANSI escape codes
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


class MapEditor:
    def __init__(self, width: int = 80, height: int = 40):
        self.map_mgr = MapManager(width, height)
        self.undo_mgr = UndoManager()
        self.prefab_mgr = PrefabManager()
        self.input_handler = InputHandler(self)

        self.cursor_x = width // 2
        self.cursor_y = height // 2
        self.camera_x = 0
        self.camera_y = 0

        self.mode = EditorMode.DRAW
        self.current_tile = "."
        self.categories = list(CATEGORIES.keys())
        self.category_idx = 0
        self.brush_size = 1
        self.paint_mode = False

        self.selection_start = None
        self.selection = None
        self.clipboard = None

        self.status_message = "Press 'H' for help."
        self.show_help = False
        self.simple_mode = False
        self.show_prefabs = False
        self.browser_idx = 0
        self.layer_visibility = "both"  # "both", "bg", "fg"
        self.zoom_level = 2  # 1: Zoom Out (1 char), 2: Normal (2 chars)

        self.term_cols, self.term_rows = 80, 24
        self.viewport_width, self.viewport_height = 40, 10
        self.start_x = 0

        self._detect_size()
        self.renderer = Renderer(self.term_cols, self.term_rows)
        self.original_settings = None

    def _detect_size(self):
        size = shutil.get_terminal_size((80, 24))
        self.term_cols, self.term_rows = size.columns, size.lines

        # We use a double-cell renderer (each cell is zoom_level chars wide)
        max_cells_w = self.term_cols // self.zoom_level

        # Viewport takes most of the height, minus space for UI (10 rows)
        self.viewport_height = max(5, self.term_rows - 10)
        # Viewport width matches cells, with a small margin
        self.viewport_width = min(max_cells_w - 4, self.map_mgr.width)

        # Center viewport horizontally
        self.start_x = (max_cells_w - self.viewport_width) // 2
        self.start_x = max(0, self.start_x)

    def setup_terminal(self):
        self.original_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        sys.stdout.write(HIDE_CURSOR)
        # Enable Mouse Tracking (Press, Release, Move, SGR)
        sys.stdout.write("\033[?1000h\033[?1003h\033[?1006h")
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    def restore_terminal(self):
        # Disable Mouse Tracking
        sys.stdout.write("\033[?1000l\033[?1003l\033[?1006l")
        if self.original_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()

    def get_key(self) -> str:
        if select.select([sys.stdin], [], [], 0.02) == ([sys.stdin], [], []):
            k = sys.stdin.read(1)
            if k == "\x1b":
                f = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
                fcntl.fcntl(sys.stdin, fcntl.F_SETFL, f | os.O_NONBLOCK)
                try:
                    k += sys.stdin.read(8)
                except Exception:
                    pass
                finally:
                    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, f)
            return k
        return ""

    def prompt(self, msg: str, default: str = "") -> str:
        self.restore_terminal()
        print(f"\n{msg}", end=" ", flush=True)
        try:
            import readline

            if default:
                readline.set_startup_hook(lambda: readline.insert_text(default))
            r = input().strip()
            if default:
                readline.set_startup_hook()
        except Exception:
            r = ""
        self.setup_terminal()
        return r

    def update_camera(self):
        mw, mh = self.viewport_width // 4, self.viewport_height // 4
        if self.map_mgr.width > self.viewport_width:
            if self.cursor_x < self.camera_x + mw:
                self.camera_x = max(0, self.cursor_x - mw)
            elif self.cursor_x >= self.camera_x + self.viewport_width - mw:
                self.camera_x = min(
                    self.map_mgr.width - self.viewport_width,
                    self.cursor_x - self.viewport_width + mw + 1,
                )
        else:
            self.camera_x = 0

        if self.map_mgr.height > self.viewport_height:
            if self.cursor_y < self.camera_y + mh:
                self.camera_y = max(0, self.cursor_y - mh)
            elif self.cursor_y >= self.camera_y + self.viewport_height - mh:
                self.camera_y = min(
                    self.map_mgr.height - self.viewport_height,
                    self.cursor_y - self.viewport_height + mh + 1,
                )
        else:
            self.camera_y = 0

    def render(self):
        self.renderer.clear()
        bw, bh, sx = self.viewport_width, self.viewport_height, self.start_x

        # Center the map within the viewport if it's smaller than viewport
        ox = max(0, (bw - self.map_mgr.width) // 2) if self.map_mgr.width < bw else 0
        oy = max(0, (bh - self.map_mgr.height) // 2) if self.map_mgr.height < bh else 0

        # Border around the viewport
        # Draw box exactly at viewport boundaries
        self.renderer.draw_box(sx, 0, bw + 2, bh + 2, (100, 100, 100))

        # Map Rendering
        for vy in range(bh):
            for vx in range(bw):
                # Calculate map coordinates
                mx, my = self.camera_x + vx - ox, self.camera_y + vy - oy

                # Screen coordinates (relative to sx)
                sc_x = sx + vx + 1
                sc_y = vy + 1

                if 0 <= my < self.map_mgr.height and 0 <= mx < self.map_mgr.width:
                    char_code = self.map_mgr.get_tile(mx, my, "bg")
                    fg_char = self.map_mgr.get_tile(mx, my, "fg")

                    # Apply visibility filters
                    if self.layer_visibility == "bg":
                        fg_char = " "
                    elif self.layer_visibility == "fg":
                        char_code = "."

                    # Selection detection
                    sel = False
                    if self.selection and self.selection.is_valid():
                        if (
                            self.selection.x
                            <= mx
                            < self.selection.x + self.selection.width
                            and self.selection.y
                            <= my
                            < self.selection.y + self.selection.height
                        ):
                            sel = True

                    if self.selection_start:
                        s1x, s1y = self.selection_start
                        if min(s1x, self.cursor_x) <= mx <= max(
                            s1x, self.cursor_x
                        ) and min(s1y, self.cursor_y) <= my <= max(s1y, self.cursor_y):
                            sel = True

                    # Determine visual tile
                    code = fg_char if fg_char != " " else char_code
                    tile = TILE_PALETTE.get(code, TILE_PALETTE["."])
                    fg, bg = tile.fg_color, tile.bg_color

                    # Layer dimming logic
                    if self.map_mgr.active_layer == "bg" and fg_char != " ":
                        fg = tuple(max(0, c - 80) for c in fg)
                        if bg:
                            bg = tuple(max(0, c - 40) for c in bg)
                    elif self.map_mgr.active_layer == "fg" and fg_char == " ":
                        bg_tile = TILE_PALETTE.get(char_code, TILE_PALETTE["."])
                        fg = tuple(max(0, c - 100) for c in bg_tile.fg_color)
                        bg = bg_tile.bg_color
                        if bg:
                            bg = tuple(max(0, c - 50) for c in bg)

                    # Highlights
                    if mx == self.cursor_x and my == self.cursor_y:
                        fg, bg = (0, 0, 0), (255, 255, 255)
                    elif sel:
                        bg = (40, 100, 200)

                    # Tool Ghosts
                    if self.mode == EditorMode.RECT and self.selection_start:
                        s1x, s1y = self.selection_start
                        if min(s1x, self.cursor_x) <= mx <= max(
                            s1x, self.cursor_x
                        ) and min(s1y, self.cursor_y) <= my <= max(s1y, self.cursor_y):
                            bg = (60, 60, 80)
                    elif self.mode == EditorMode.PASTE and self.clipboard:
                        if (
                            self.cursor_x <= mx < self.cursor_x + self.clipboard.width
                            and self.cursor_y
                            <= my
                            < self.cursor_y + self.clipboard.height
                        ):
                            bg = (50, 80, 50)
                    elif self.mode == EditorMode.DRAW and not self.paint_mode:
                        h = self.brush_size // 2
                        if (
                            self.cursor_x - h
                            <= mx
                            < self.cursor_x - h + self.brush_size
                            and self.cursor_y - h
                            <= my
                            < self.cursor_y - h + self.brush_size
                        ):
                            bg = (50, 50, 60)

                    if self.simple_mode:
                        fg, bg = (200, 200, 200), None

                    self.renderer.set_cell(sc_x, sc_y, tile.char, fg, bg)
                else:
                    # Void Area (outside map bounds)
                    vbg = (15, 15, 18) if (mx + my) % 2 == 0 else (10, 10, 12)
                    self.renderer.set_cell(sc_x, sc_y, "· ", (30, 30, 35), vbg)

        self._render_ui()
        self.renderer.flush()
        self.renderer.flush()

    def _render_ui(self):
        # UI starts below viewport + border
        y_base = self.viewport_height + 2
        sx = self.start_x

        # Clear the UI area below the map to prevent artifacts
        # We don't use draw_text with spaces because it might wrap if not careful.
        # Instead, we'll let the double-buffering handle it via renderer.clear()
        # But we need to ensure the renderer covers the whole screen height.

        # 1. Palette Section
        cat_name = self.categories[self.category_idx]
        self.renderer.draw_text(sx, y_base + 1, f"[{cat_name}]", (255, 180, 0))

        layout = get_category_layout(cat_name)
        for r, row in enumerate(layout):
            for c, t in enumerate(row):
                px, py = sx + c * 3, y_base + r + 2
                tile = TILE_PALETTE.get(t, TILE_PALETTE["."])

                # Selection highlight
                bg = (80, 80, 100) if t == self.current_tile else (-1, -1, -1)

                # Key Number
                idx = r * 6 + c + 1
                self.renderer.draw_text(px, py, f"{idx % 10}", (150, 150, 150), bg)
                self.renderer.set_cell(
                    px + 1, py, tile.char, tile.fg_color, tile.bg_color
                )

        # 2. Info Section
        info_x = sx + 22
        # Ensure map_mgr has maps list initialized
        num_maps = len(self.map_mgr.maps) if self.map_mgr.maps else 1
        map_count = f"{self.map_mgr.current_index + 1}/{num_maps}"

        info_lines = [
            f"MAP: {self.map_mgr.name[:10]} ({map_count})",
            f"POS: {self.cursor_x},{self.cursor_y}",
            f"LYR: {self.map_mgr.active_layer.upper()} | VIS: {self.layer_visibility.upper()[:2]}",
            f"TILE: {TILE_PALETTE.get(self.current_tile).name[:14]}",
        ]
        for i, text in enumerate(info_lines):
            self.renderer.draw_text(info_x, y_base + i + 1, text, (200, 200, 200))

        # 3. Status Bar
        status_y = self.term_rows - 1
        max_cells = self.term_cols // self.renderer.cell_width

        # Left: Status
        msg = f" {self.status_message} "
        self.renderer.draw_text(
            0, status_y, msg.ljust(max_cells), (255, 255, 255), (40, 40, 50)
        )

        # Right: Tool Info
        auto_str = "[AUTO]" if self.map_mgr.auto_tiling else ""
        tool_info = (
            f" {self.mode.name} | Z:{self.zoom_level} | B:{self.brush_size} {auto_str} "
        )
        tx = max_cells - (len(tool_info) // self.renderer.cell_width) - 1
        if tx > max_cells // 2:  # Only draw if it doesn't overlap too much
            self.renderer.draw_text(
                tx, status_y, tool_info, (255, 255, 0), (60, 60, 70)
            )

        if self.show_help:
            self._render_help()
        if self.show_prefabs:
            self._render_prefabs()
        if self.mode == EditorMode.BROWSE:
            self._render_map_browser()

    def _render_help(self):
        # Background
        sx, sy = 2, 2
        w, h = self.term_cols - 4, 10
        for y in range(h):
            self.renderer.draw_text(sx, sy + y, " " * w, (255, 255, 255), (20, 20, 40))

        # Column 1
        self.renderer.draw_text(
            sx + 2, sy + 1, "--- MOVEMENT ---", (255, 200, 0), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 2, sy + 2, "WASD: Move Cursor", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 2, sy + 3, "[, ]: Zoom Out/In", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 2, sy + 4, "<, >: Prev/Next Map", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 2, sy + 5, "H/J/K/L: Camera", (200, 200, 200), (20, 20, 40)
        )

        # Column 2
        self.renderer.draw_text(
            sx + 22, sy + 1, "--- DRAWING ---", (255, 200, 0), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 2, "SPACE: Paint/Commit", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 3, "P: Toggle Paint", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 4, "E: Erase Mode", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 5, "F: Flood Fill", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 6, "B: Rectangle", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 7, "V: Paste/Cycle Vis", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 22, sy + 8, "1-0: Select Tile", (200, 200, 200), (20, 20, 40)
        )

        # Column 3
        self.renderer.draw_text(
            sx + 44, sy + 1, "--- EDITING ---", (255, 200, 0), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 2, "S: Select", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 3, "C/X: Copy/Cut", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 4, "BS: Delete Sel", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 5, "Ctrl+D: Duplicate", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 6, "Ctrl+A: Auto-Tile", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 44, sy + 7, "Z/Y: Undo/Redo", (200, 200, 200), (20, 20, 40)
        )

        # Column 4
        self.renderer.draw_text(
            sx + 66, sy + 1, "--- SYSTEM ---", (255, 200, 0), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 2, "Ctrl+S: Save", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 3, "L: Load", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 4, "N: New Map", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 5, "Ctrl+B: Browser", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 6, "Ctrl+P/O: Prefabs", (200, 200, 200), (20, 20, 40)
        )
        self.renderer.draw_text(
            sx + 66, sy + 7, "Ctrl+G: Test Game", (200, 200, 200), (20, 20, 40)
        )

    def _render_map_browser(self):
        maps = self.map_mgr.maps
        h = [" --- MAP BROWSER --- "]
        for i, m in enumerate(maps):
            name = m.get("name", "Untitled")
            prefix = "> " if i == self.browser_idx else "  "
            h.append(f"{prefix}{i+1:2}: {name[:20]}")
        h.append("")
        h.append("ENTER: Select | D: Delete | B/Q: Back")

        bw, bh = (max(len(line) for line in h) // 2) + 2, len(h) + 2
        sx, sy = (
            self.start_x + (self.viewport_width - bw) // 2,
            (self.viewport_height - bh) // 2,
        )
        # Background
        for y in range(bh):
            for x in range(bw):
                self.renderer.set_cell(sx + x, sy + y, "  ", None, (20, 30, 40))
        for i, line in enumerate(h):
            color = (255, 255, 255)
            if "ENTER" in line or "D:" in line:
                color = (200, 200, 200)
            self.renderer.draw_text(sx + 1, sy + 1 + i, line, color, (20, 30, 40))

    def _render_prefabs(self):
        prefabs = self.prefab_mgr.list_prefabs()
        h = (
            [" --- PREFABS --- "]
            + prefabs
            + (["(No prefabs found)"] if not prefabs else [])
            + ["Press any key to close"]
        )
        bw, bh = (max(len(line) for line in h) // 2) + 2, len(h) + 2
        sx, sy = (
            self.start_x + (self.viewport_width - bw) // 2,
            (self.viewport_height - bh) // 2,
        )
        for y in range(bh):
            for x in range(bw):
                self.renderer.set_cell(sx + x, sy + y, "  ", None, (30, 20, 20))
        for i, line in enumerate(h):
            self.renderer.draw_text(
                sx + 1, sy + 1 + i, line, (255, 255, 255), (30, 20, 20)
            )

    def _handle_mouse(self, sequence: str):
        try:
            if not sequence.startswith("\x1b[<"):
                return
            parts = sequence[3:-1].split(";")
            if len(parts) != 3:
                return

            btn = int(parts[0])
            mx = int(parts[1])
            my = int(parts[2])
            is_release = sequence.endswith("m")

            # Convert to grid coordinates
            term_x = (mx - 1) // 2
            term_y = my - 1

            # 1. Palette Interaction
            if self._handle_mouse_palette(term_x, term_y):
                return

            # 3. Map Drawing Interaction
            self._handle_mouse_draw(btn, mx, my, is_release)

        except Exception:
            pass

    def _handle_mouse_palette(self, term_x: int, term_y: int) -> bool:
        y_base = self.viewport_height + 2
        sx = self.start_x

        # Check if click is within palette area
        # Palette tiles are rendered at px = sx + c * 3, where c is 0-5
        if not (y_base + 2 <= term_y < y_base + 4):  # 2 rows of tiles
            return False

        if not (sx <= term_x < sx + 18):  # 6 columns * 3 cells per tile
            return False

        row = term_y - (y_base + 2)
        col = (term_x - sx) // 3

        if 0 <= row < 2 and 0 <= col < 6:
            cat_name = self.categories[self.category_idx]
            layout = get_category_layout(cat_name)
            if row < len(layout) and col < len(layout[row]):
                self.current_tile = layout[row][col]
                self.status_message = f"Selected: {self.current_tile}"
                return True
        return False

    def _handle_mouse_draw(self, btn: int, mx: int, my: int, is_release: bool):
        # mx is 1-based char coordinate from terminal
        # term_x is 0-based cell coordinate
        term_x = (mx - 1) // self.zoom_level
        term_y = my - 1

        # map_vx is cell relative to viewport content start (after border and centering)
        map_vx = term_x - self.start_x - 1

        bw, bh = self.viewport_width, self.viewport_height
        ox = max(0, (bw - self.map_mgr.width) // 2) if self.map_mgr.width < bw else 0
        oy = max(0, (bh - self.map_mgr.height) // 2) if self.map_mgr.height < bh else 0

        mx_map = self.camera_x + map_vx - ox
        my_map = self.camera_y + (term_y - 1) - oy

        if 0 <= mx_map < self.map_mgr.width and 0 <= my_map < self.map_mgr.height:
            self.cursor_x = mx_map
            self.cursor_y = my_map
            if (btn == 0 or btn == 32) and not is_release:
                tools.draw_brush(
                    self.map_mgr,
                    self.undo_mgr,
                    self.cursor_x,
                    self.cursor_y,
                    self.current_tile,
                    self.brush_size,
                )

    def handle_input(self) -> bool:
        k = self.get_key()
        if not k:
            return True
        return self.input_handler.handle_key(k)

    def run(self, path=None):
        if path:
            self.map_mgr.load(path)
        try:
            self.setup_terminal()
            while True:
                self.render()
                if not self.handle_input():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.restore_terminal()
            print("\nEditor closed.")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("file", nargs="?")
    p.add_argument("-w", "--width", type=int, default=80)
    p.add_argument("-H", "--height", type=int, default=40)
    args = p.parse_args()
    MapEditor(args.width, args.height).run(args.file)
