"""
Map data management and file I/O for the Map Editor.
Supports dual-layer editing and multi-map management.
"""

import os
import sys
import toml
import copy
from typing import Optional


class MapManager:
    def __init__(self, width: int = 80, height: int = 40):
        self.width = width
        self.height = height
        self.maps = []  # List of map dicts
        self.current_index = 0

        # Current active map data
        self.layers = {
            "bg": [["." for _ in range(width)] for _ in range(height)],
            "fg": [[" " for _ in range(width)] for _ in range(height)],
        }
        self.active_layer = "bg"
        self.name = "Untitled"
        self.world_x = 0
        self.world_y = 0
        self.auto_tiling = True

        # Initialize with one empty map
        self._sync_current_to_list()

    def _sync_current_to_list(self):
        """Saves current editing state into the maps list."""
        layout = "\n".join(["".join(r).rstrip(".") for r in self.layers["bg"]]).rstrip()
        fg_layout = "\n".join(["".join(r).rstrip() for r in self.layers["fg"]]).rstrip()

        m_data = {
            "name": self.name,
            "x": self.world_x,
            "y": self.world_y,
            "layout": layout,
        }
        if fg_layout.replace("\n", "").strip():
            m_data["fg_layout"] = fg_layout

        if not self.maps:
            self.maps.append(m_data)
            self.current_index = 0
        else:
            self.maps[self.current_index] = m_data

    def _load_from_index(self, index: int):
        """Loads map data from the maps list into editing state."""
        if not (0 <= index < len(self.maps)):
            return False

        m = self.maps[index]
        self.current_index = index
        self.name = m.get("name", "Untitled")
        self.world_x = m.get("x", 0)
        self.world_y = m.get("y", 0)

        layout = m.get("layout", "")
        lines = layout.strip().split("\n") if isinstance(layout, str) else layout
        self.height = len(lines)
        self.width = max(len(line) for line in lines) if lines else 0

        self.layers["bg"] = [list(line.ljust(self.width, ".")) for line in lines]
        self.layers["fg"] = [
            [" " for _ in range(self.width)] for _ in range(self.height)
        ]

        fg_layout = m.get("fg_layout", "")
        if fg_layout:
            fg_lines = fg_layout.strip().split("\n")
            for y, row in enumerate(fg_lines):
                if y < self.height:
                    for x, char in enumerate(row):
                        if x < self.width:
                            self.layers["fg"][y][x] = char
        return True

    def next_map(self):
        if len(self.maps) <= 1:
            return False
        self._sync_current_to_list()
        new_idx = (self.current_index + 1) % len(self.maps)
        return self._load_from_index(new_idx)

    def prev_map(self):
        if len(self.maps) <= 1:
            return False
        self._sync_current_to_list()
        new_idx = (self.current_index - 1) % len(self.maps)
        return self._load_from_index(new_idx)

    def new_map(self, name: str, width: int, height: int):
        self._sync_current_to_list()
        self.name = name
        self.width = width
        self.height = height
        self.layers = {
            "bg": [["." for _ in range(width)] for _ in range(height)],
            "fg": [[" " for _ in range(width)] for _ in range(height)],
        }
        self.world_x = 0
        self.world_y = 0
        # Add as new map
        self.maps.append({})  # Placeholder
        self.current_index = len(self.maps) - 1
        self._sync_current_to_list()

    def duplicate_current(self):
        self._sync_current_to_list()
        new_map = copy.deepcopy(self.maps[self.current_index])
        new_map["name"] += " (Copy)"
        self.maps.insert(self.current_index + 1, new_map)
        self.current_index += 1
        return self._load_from_index(self.current_index)

    def delete_current(self):
        if len(self.maps) <= 1:
            return False
        self.maps.pop(self.current_index)
        if self.current_index >= len(self.maps):
            self.current_index = len(self.maps) - 1
        return self._load_from_index(self.current_index)

    def switch_layer(self):
        self.active_layer = "fg" if self.active_layer == "bg" else "bg"
        return self.active_layer

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as f:
                data = toml.load(f)
            self.maps = data.get("maps", [])
            if not self.maps:
                # If file exists but no maps, initialize one
                self.maps = []
                self.new_map("Untitled", 80, 40)
                return True
            return self._load_from_index(0)
        except toml.TomlDecodeError as e:
            print(f"Error parsing TOML file {path}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error loading map file {path}: {e}", file=sys.stderr)
            return False

    def save(self, path: str) -> bool:
        try:
            self._sync_current_to_list()
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            with open(path, "w") as f:
                f.write("# Static Map Configurations\n# Generated by Map Editor\n\n")
                for m in self.maps:
                    f.write("[[maps]]\n")
                    f.write(f'name = "{m["name"]}"\n')
                    f.write(f'x = {m["x"]}\n')
                    f.write(f'y = {m["y"]}\n')
                    f.write(f'layout = """\n{m["layout"]}\n"""\n')
                    if "fg_layout" in m:
                        f.write(f'fg_layout = """\n{m["fg_layout"]}\n"""\n')
                    f.write("\n")
            return True
        except Exception as e:
            print(f"Error saving map file {path}: {e}", file=sys.stderr)
            return False

    def get_tile(self, x: int, y: int, layer: Optional[str] = None) -> str:
        lyr = layer if layer else self.active_layer
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.layers[lyr][y][x]
        return " " if lyr == "fg" else "."

    def set_tile(self, x: int, y: int, char: str, layer: Optional[str] = None):
        lyr = layer if layer else self.active_layer
        if 0 <= x < self.width and 0 <= y < self.height:
            self.layers[lyr][y][x] = char
