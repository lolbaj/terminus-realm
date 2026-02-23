"""
Input handling logic for the Map Editor.
Separates key processing from the main editor loop.
"""

from typing import TYPE_CHECKING
from .models import EditorMode, Selection
from . import tools
import sys
import os
import copy

if TYPE_CHECKING:
    from .editor import MapEditor


class InputHandler:
    def __init__(self, editor: "MapEditor"):
        self.editor = editor

    def handle_key(self, k: str) -> bool:
        """
        Process a single key press.
        Returns False if the editor should exit, True otherwise.
        """
        if not k:
            return True

        # Global Quits
        if k.lower() == "q" or k == "\x03":
            if self.editor.mode in (EditorMode.BROWSE, EditorMode.PASTE):
                # Contextual back
                self.editor.mode = EditorMode.DRAW
                self.editor.status_message = "Mode cancelled."
                return True
            return False

        # Mouse Input
        if k.startswith("\x1b[<"):
            self.editor._handle_mouse(k)
            return True

        # Help Toggle
        if k.lower() == "h":
            self.editor.show_help = not self.editor.show_help
            return True
        if self.editor.show_help:
            self.editor.show_help = False
            return True

        # Prefab Loading Context
        if self.editor.show_prefabs:
            self.editor.show_prefabs = False
            prefabs = self.editor.prefab_mgr.list_prefabs()
            if prefabs:
                name = self.editor.prompt("Load prefab name:")
                if name in prefabs:
                    p = self.editor.prefab_mgr.load_prefab(name)
                    if p:
                        self.editor.clipboard, self.editor.status_message = (
                            p,
                            f"Prefab '{name}' loaded.",
                        )
            return True

        # Mode Specific Handling
        if self.editor.mode == EditorMode.BROWSE:
            return self._handle_browse(k)

        if self.editor.mode == EditorMode.PASTE:
            return self._handle_paste(k)

        # Standard Draw/Select Mode Handling
        return self._handle_draw_select(k)

    def _handle_browse(self, k: str) -> bool:
        if k in ("\x1b[A", "w"):
            self.editor.browser_idx = (self.editor.browser_idx - 1) % len(
                self.editor.map_mgr.maps
            )
        elif k in ("\x1b[B", "s"):
            self.editor.browser_idx = (self.editor.browser_idx + 1) % len(
                self.editor.map_mgr.maps
            )
        elif k == "\r":
            self.editor.map_mgr._sync_current_to_list()
            if self.editor.map_mgr._load_from_index(self.editor.browser_idx):
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows
                )
                self.editor.undo_mgr.clear()
                self.editor.mode = EditorMode.DRAW
                self.editor.status_message = f"Selected map: {self.editor.map_mgr.name}"
        elif k.lower() in ("b"):
            self.editor.mode = EditorMode.DRAW
            self.editor.status_message = "Map Browser closed."
        elif k.lower() == "d":
            if len(self.editor.map_mgr.maps) > 1:
                name = self.editor.map_mgr.maps[self.editor.browser_idx].get(
                    "name", "Untitled"
                )
                confirm = self.editor.prompt(f"Delete '{name}'? (y/n):")
                if confirm.lower() == "y":
                    if self.editor.browser_idx == self.editor.map_mgr.current_index:
                        self.editor.map_mgr.delete_current()
                        self.editor._detect_size()
                        self.editor.renderer.resize(
                            self.editor.term_cols, self.editor.term_rows
                        )
                        self.editor.undo_mgr.clear()
                    else:
                        self.editor.map_mgr.maps.pop(self.editor.browser_idx)
                        if self.editor.map_mgr.current_index > self.editor.browser_idx:
                            self.editor.map_mgr.current_index -= 1

                    self.editor.browser_idx = max(
                        0,
                        min(self.editor.browser_idx, len(self.editor.map_mgr.maps) - 1),
                    )
                    self.editor.status_message = f"Deleted '{name}'."
            else:
                self.editor.status_message = "Cannot delete the last map."
        return True

    def _handle_paste(self, k: str) -> bool:
        # Movement for ghost
        self._handle_movement(k)

        # Commit
        if k == " " or k.lower() == "v":
            if self.editor.clipboard:
                # Disable auto-tiling during mass paste
                was_auto = getattr(self.editor.map_mgr, "auto_tiling", False)
                self.editor.map_mgr.auto_tiling = False

                self.editor.undo_mgr.start_group()
                for dy in range(self.editor.clipboard.height):
                    for dx in range(self.editor.clipboard.width):
                        if self.editor.clipboard.bg_data:
                            tools.set_tile_with_undo_layer(
                                self.editor.map_mgr,
                                self.editor.undo_mgr,
                                self.editor.cursor_x + dx,
                                self.editor.cursor_y + dy,
                                self.editor.clipboard.bg_data[dy][dx],
                                "bg",
                            )
                        if self.editor.clipboard.fg_data:
                            tools.set_tile_with_undo_layer(
                                self.editor.map_mgr,
                                self.editor.undo_mgr,
                                self.editor.cursor_x + dx,
                                self.editor.cursor_y + dy,
                                self.editor.clipboard.fg_data[dy][dx],
                                "fg",
                            )
                self.editor.undo_mgr.end_group()

                # Restore auto-tiling and update area
                self.editor.map_mgr.auto_tiling = was_auto
                if was_auto:
                    from . import auto_tiler

                    for dy in range(self.editor.clipboard.height):
                        for dx in range(self.editor.clipboard.width):
                            auto_tiler.process_auto_tile(
                                self.editor.map_mgr,
                                self.editor.cursor_x + dx,
                                self.editor.cursor_y + dy,
                                "bg",
                                self.editor.undo_mgr,
                            )
                            auto_tiler.process_auto_tile(
                                self.editor.map_mgr,
                                self.editor.cursor_x + dx,
                                self.editor.cursor_y + dy,
                                "fg",
                                self.editor.undo_mgr,
                            )

                self.editor.mode = EditorMode.DRAW
                self.editor.status_message = "Pasted."
        return True

    def _handle_movement(self, k: str):
        px, py = self.editor.cursor_x, self.editor.cursor_y
        if k in ("\x1b[A", "w"):
            self.editor.cursor_y = max(0, self.editor.cursor_y - 1)
        elif k in ("\x1b[B", "s"):
            self.editor.cursor_y = min(
                self.editor.map_mgr.height - 1, self.editor.cursor_y + 1
            )
        elif k in ("\x1b[D", "a"):
            self.editor.cursor_x = max(0, self.editor.cursor_x - 1)
        elif k in ("\x1b[C", "d"):
            self.editor.cursor_x = min(
                self.editor.map_mgr.width - 1, self.editor.cursor_x + 1
            )

        # Draw line if paint mode and moved
        if (
            (px != self.editor.cursor_x or py != self.editor.cursor_y)
            and self.editor.paint_mode
            and self.editor.mode in (EditorMode.DRAW, EditorMode.ERASE)
        ):
            tools.draw_line(
                self.editor.map_mgr,
                self.editor.undo_mgr,
                px,
                py,
                self.editor.cursor_x,
                self.editor.cursor_y,
                self._get_active_tile(),
                self.editor.brush_size,
            )

    def _get_active_tile(self) -> str:
        if self.editor.mode == EditorMode.ERASE:
            return "." if self.editor.map_mgr.active_layer == "bg" else " "
        return self.editor.current_tile

    def _handle_draw_select(self, k: str) -> bool:
        from .palette import CATEGORIES

        self._handle_movement(k)

        # Layers / Maps
        if k == "\t":
            layer = self.editor.map_mgr.switch_layer()
            self.editor.status_message = f"Switched to {layer.upper()} layer."
        elif k == "\x1b[":  # Ctrl+[ (Escape sequence start, might be tricky)
            # Let's use different keys for Map cycling to avoid escape sequence conflict
            # or just use comma/period
            pass
        elif k == ",":
            if self.editor.map_mgr.prev_map():
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows, self.editor.zoom_level
                )
                self.editor.undo_mgr.clear()
                self.editor.status_message = "Previous map."
        elif k == ".":
            if self.editor.map_mgr.next_map():
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows, self.editor.zoom_level
                )
                self.editor.undo_mgr.clear()
                self.editor.status_message = "Next map."

        # Zoom
        elif k == "[":
            if self.editor.zoom_level > 1:
                self.editor.zoom_level = 1
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows, self.editor.zoom_level
                )
                sys.stdout.write("\033[2J\033[H")
                self.editor.status_message = "Zoom Out (1x1)"
        elif k == "]":
            if self.editor.zoom_level < 2:
                self.editor.zoom_level = 2
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows, self.editor.zoom_level
                )
                sys.stdout.write("\033[2J\033[H")
                self.editor.status_message = "Zoom In (2x1)"

        # Visibility
        elif k == "V":
            modes = ["both", "bg", "fg"]
            self.editor.layer_visibility = modes[
                (modes.index(self.editor.layer_visibility) + 1) % len(modes)
            ]
            self.editor.status_message = (
                f"Visibility: {self.editor.layer_visibility.upper()}"
            )

        # Erase Mode Toggle
        elif k.lower() == "e":
            if self.editor.mode == EditorMode.ERASE:
                self.editor.mode = EditorMode.DRAW
                self.editor.status_message = "DRAW Mode"
            else:
                self.editor.mode = EditorMode.ERASE
                self.editor.status_message = "ERASE Mode"

        # Ctrl Shortcuts
        elif k == "\x04":  # Ctrl+D
            if self.editor.map_mgr.duplicate_current():
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows
                )
                self.editor.undo_mgr.clear()
                self.editor.status_message = "Duplicated."
        elif k == "\x10":  # Ctrl+P
            if self.editor.selection:
                name = self.editor.prompt("Save prefab as:")
                if name and self.editor.prefab_mgr.save_prefab(
                    name, self.editor.selection
                ):
                    self.editor.status_message = f"Saved prefab '{name}'."
            else:
                self.editor.status_message = "No selection to save."
        elif k == "\x0f":  # Ctrl+O
            self.editor.show_prefabs = True
        elif k == "\x0b":  # Ctrl+K
            self.editor.category_idx = (self.editor.category_idx + 1) % len(
                self.editor.categories
            )
            self.editor.status_message = (
                f"Category: {self.editor.categories[self.editor.category_idx]}"
            )
        elif k == "\x01":  # Ctrl+A
            self.editor.map_mgr.auto_tiling = not self.editor.map_mgr.auto_tiling
            self.editor.status_message = (
                f"Auto-tiling {'ON' if self.editor.map_mgr.auto_tiling else 'OFF'}."
            )
        elif k == "\x17":  # Ctrl+W
            self.editor.minimap.visible = not self.editor.minimap.visible
            self.editor.status_message = (
                f"Minimap {'ON' if self.editor.minimap.visible else 'OFF'}."
            )
        elif k == "\x02":  # Ctrl+B
            self.editor.mode = EditorMode.BROWSE
            self.editor.browser_idx = self.editor.map_mgr.current_index
            self.editor.status_message = "Map Browser opened."
        elif k == "\x07":  # Ctrl+G
            self.editor.status_message = "Launching game..."
            self.editor.render()
            test_path = "src/data/static/test_map.toml"
            self.editor.map_mgr.save(test_path)
            self.editor.restore_terminal()
            cmd = f"python src/main.py --map {test_path} --pos {self.editor.cursor_x},{self.editor.cursor_y}"
            os.system(cmd)
            self.editor.setup_terminal()
            sys.stdout.write("\033[2J\033[H")
            self.editor.status_message = "Returned from game test."
        elif k == "\x0c":  # Ctrl+L
            self.editor._detect_size()
            self.editor.renderer.resize(self.editor.term_cols, self.editor.term_rows)
            sys.stdout.write("\033[2J\033[H")
            self.editor.status_message = "UI Refreshed."

        # Tools
        elif k.lower() == "p":
            self.editor.paint_mode = not self.editor.paint_mode
            if self.editor.paint_mode:
                self.editor.undo_mgr.start_group()
                tools.draw_brush(
                    self.editor.map_mgr,
                    self.editor.undo_mgr,
                    self.editor.cursor_x,
                    self.editor.cursor_y,
                    self._get_active_tile(),
                    self.editor.brush_size,
                )
            else:
                self.editor.undo_mgr.end_group()

        # Tile Selection
        elif k in "1234567890":
            n = int(k)
            if n == 0:
                n = 10
            flat = CATEGORIES.get(self.editor.categories[self.editor.category_idx], [])
            if n <= len(flat):
                self.editor.current_tile = flat[n - 1]
                # Auto-switch to DRAW mode if tile selected
                if self.editor.mode == EditorMode.ERASE:
                    self.editor.mode = EditorMode.DRAW
                    self.editor.status_message = f"DRAW: {self.editor.current_tile}"

        # Action
        elif k == " ":
            if self.editor.mode == EditorMode.PASTE:
                # Commit Paste from SPACE
                if self.editor.clipboard:
                    self.editor.undo_mgr.start_group()
                    for dy in range(self.editor.clipboard.height):
                        for dx in range(self.editor.clipboard.width):
                            if self.editor.clipboard.bg_data:
                                tools.set_tile_with_undo_layer(
                                    self.editor.map_mgr,
                                    self.editor.undo_mgr,
                                    self.editor.cursor_x + dx,
                                    self.editor.cursor_y + dy,
                                    self.editor.clipboard.bg_data[dy][dx],
                                    "bg",
                                )
                            if self.editor.clipboard.fg_data:
                                tools.set_tile_with_undo_layer(
                                    self.editor.map_mgr,
                                    self.editor.undo_mgr,
                                    self.editor.cursor_x + dx,
                                    self.editor.cursor_y + dy,
                                    self.editor.clipboard.fg_data[dy][dx],
                                    "fg",
                                )
                    self.editor.undo_mgr.end_group()
                    self.editor.mode = EditorMode.DRAW
                    self.editor.status_message = "Pasted."
            else:
                tools.draw_brush(
                    self.editor.map_mgr,
                    self.editor.undo_mgr,
                    self.editor.cursor_x,
                    self.editor.cursor_y,
                    self._get_active_tile(),
                    self.editor.brush_size,
                )
        elif k.lower() == "r":
            self.editor.current_tile = self.editor.map_mgr.get_tile(
                self.editor.cursor_x, self.editor.cursor_y
            )

        # Selection / Rect
        elif k.lower() == "b":
            if not self.editor.selection_start:
                self.editor.selection_start, self.editor.mode = (
                    (self.editor.cursor_x, self.editor.cursor_y),
                    EditorMode.RECT,
                )
            else:
                s1x, s1y = self.editor.selection_start
                tools.draw_rect(
                    self.editor.map_mgr,
                    self.editor.undo_mgr,
                    s1x,
                    s1y,
                    self.editor.cursor_x,
                    self.editor.cursor_y,
                    self._get_active_tile(),
                )
                self.editor.selection_start, self.editor.mode = None, EditorMode.DRAW
        elif k.lower() == "s":
            if not self.editor.selection_start:
                self.editor.selection_start, self.editor.mode = (
                    (self.editor.cursor_x, self.editor.cursor_y),
                    EditorMode.SELECT,
                )
            else:
                s1x, s1y = self.editor.selection_start
                sx, sy = min(s1x, self.editor.cursor_x), min(s1y, self.editor.cursor_y)
                ex, ey = max(s1x, self.editor.cursor_x), max(s1y, self.editor.cursor_y)
                w, h = ex - sx + 1, ey - sy + 1
                bg = [
                    [
                        self.editor.map_mgr.get_tile(x, y, "bg")
                        for x in range(sx, ex + 1)
                    ]
                    for y in range(sy, ey + 1)
                ]
                fg = [
                    [
                        self.editor.map_mgr.get_tile(x, y, "fg")
                        for x in range(sx, ex + 1)
                    ]
                    for y in range(sy, ey + 1)
                ]
                self.editor.selection = Selection(sx, sy, w, h, bg, fg)
                self.editor.selection_start, self.editor.mode = None, EditorMode.DRAW

        # Copy/Paste Operations
        elif k.lower() == "c" and self.editor.selection:
            self.editor.clipboard = copy.deepcopy(self.editor.selection)
            self.editor.status_message = "Copied."
        elif k.lower() == "v" and self.editor.clipboard:
            self.editor.mode = EditorMode.PASTE
            self.editor.status_message = (
                "PASTE MODE: Position ghost and press SPACE/V to commit, Q to cancel."
            )
        elif k.lower() == "x" and self.editor.selection:
            self.editor.clipboard = copy.deepcopy(self.editor.selection)
            self.editor.undo_mgr.start_group()
            for dy in range(self.editor.selection.height):
                for dx in range(self.editor.selection.width):
                    tools.set_tile_with_undo_layer(
                        self.editor.map_mgr,
                        self.editor.undo_mgr,
                        self.editor.selection.x + dx,
                        self.editor.selection.y + dy,
                        ".",
                        "bg",
                    )
                    tools.set_tile_with_undo_layer(
                        self.editor.map_mgr,
                        self.editor.undo_mgr,
                        self.editor.selection.x + dx,
                        self.editor.selection.y + dy,
                        " ",
                        "fg",
                    )
            self.editor.undo_mgr.end_group()
            self.editor.selection = None
            self.editor.status_message = "Cut."

        # Delete / Fill
        elif k in ("\x7f", "\x1b[3~", "DEL"):
            if self.editor.selection:
                self.editor.undo_mgr.start_group()
                for dy in range(self.editor.selection.height):
                    for dx in range(self.editor.selection.width):
                        if self.editor.map_mgr.active_layer == "bg":
                            tools.set_tile_with_undo_layer(
                                self.editor.map_mgr,
                                self.editor.undo_mgr,
                                self.editor.selection.x + dx,
                                self.editor.selection.y + dy,
                                ".",
                                "bg",
                            )
                        else:
                            tools.set_tile_with_undo_layer(
                                self.editor.map_mgr,
                                self.editor.undo_mgr,
                                self.editor.selection.x + dx,
                                self.editor.selection.y + dy,
                                " ",
                                "fg",
                            )
                self.editor.undo_mgr.end_group()
                self.editor.selection = None
                self.editor.status_message = "Selection Deleted."
            else:
                # Delete single tile under cursor
                char = "." if self.editor.map_mgr.active_layer == "bg" else " "
                tools.set_tile_with_undo(
                    self.editor.map_mgr,
                    self.editor.undo_mgr,
                    self.editor.cursor_x,
                    self.editor.cursor_y,
                    char,
                )
                self.editor.status_message = "Tile Deleted."
        elif k.lower() == "f":
            target = self.editor.map_mgr.get_tile(
                self.editor.cursor_x, self.editor.cursor_y
            )
            tools.flood_fill(
                self.editor.map_mgr,
                self.editor.undo_mgr,
                self.editor.cursor_x,
                self.editor.cursor_y,
                target,
                self._get_active_tile(),
            )

        # Brush Size
        elif k in ("+", "="):
            self.editor.brush_size = min(9, self.editor.brush_size + 1)
        elif k == "-":
            self.editor.brush_size = max(1, self.editor.brush_size - 1)

        # Undo/Redo
        elif k in ("z", "\x1a"):  # z or Ctrl+Z
            if self.editor.undo_mgr.undo(self.editor.map_mgr.layers):
                self.editor.status_message = "Undo."
        elif k in ("y", "\x19"):  # y or Ctrl+Y
            if self.editor.undo_mgr.redo(self.editor.map_mgr.layers):
                self.editor.status_message = "Redo."

        # File Operations
        elif k == "\x13":  # Ctrl+S
            p = self.editor.prompt("Save to:", "src/data/static/maps.toml")
            if p and self.editor.map_mgr.save(p):
                self.editor.status_message = f"Saved to {p}"
        elif k.lower() == "l":
            p = self.editor.prompt("Load from:", "src/data/static/maps.toml")
            if p and self.editor.map_mgr.load(p):
                self.editor._detect_size()
                self.editor.renderer.resize(
                    self.editor.term_cols, self.editor.term_rows, self.editor.zoom_level
                )
                sys.stdout.write("\033[2J\033[H")
                self.editor.undo_mgr.clear()
                self.editor.status_message = "Loaded."
        elif k == "n":
            name = self.editor.prompt("Name:", "New Map")
            if name:
                try:
                    w, h = int(self.editor.prompt("Width:", "80")), int(
                        self.editor.prompt("Height:", "40")
                    )
                    self.editor.map_mgr.new_map(name, w, h)
                    self.editor._detect_size()
                    self.editor.renderer.resize(
                        self.editor.term_cols,
                        self.editor.term_rows,
                        self.editor.zoom_level,
                    )
                    sys.stdout.write("\033[2J\033[H")
                    self.editor.undo_mgr.clear()
                    self.editor.cursor_x, self.editor.cursor_y = w // 2, h // 2
                except Exception:
                    pass
        elif k == "m":
            name = self.editor.prompt("Rename:", self.editor.map_mgr.name)
            if name:
                self.editor.map_mgr.name = name
            try:
                self.editor.map_mgr.world_x = int(
                    self.editor.prompt("X:", str(self.editor.map_mgr.world_x))
                )
            except Exception:
                pass
            try:
                self.editor.map_mgr.world_y = int(
                    self.editor.prompt("Y:", str(self.editor.map_mgr.world_y))
                )
            except Exception:
                pass

        # Camera
        elif k == "H":
            self.editor.camera_x = max(0, self.editor.camera_x - 5)
        elif k == "K":
            self.editor.camera_y = max(0, self.editor.camera_y - 5)
        elif k == "J":
            self.editor.camera_y = min(
                max(0, self.editor.map_mgr.height - self.editor.viewport_height),
                self.editor.camera_y + 5,
            )
        elif k == "L":
            self.editor.camera_x = min(
                max(0, self.editor.map_mgr.width - self.editor.viewport_width),
                self.editor.camera_x + 5,
            )

        self.editor.update_camera()
        return True
