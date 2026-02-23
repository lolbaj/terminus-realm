"""
Prefab and Stamp management for the Map Editor.
Allows saving and loading rectangular snippets of maps with dual-layer support.
"""

import os
import json
from typing import List, Optional
from .models import Selection


class PrefabManager:
    def __init__(self, prefab_dir: str = "map_editor/prefabs"):
        self.prefab_dir = prefab_dir
        if not os.path.exists(self.prefab_dir):
            os.makedirs(self.prefab_dir)

    def save_prefab(self, name: str, selection: Selection) -> bool:
        """Saves a Selection object as a JSON prefab."""
        if not selection.is_valid():
            return False

        path = os.path.join(self.prefab_dir, f"{name}.json")
        try:
            data = {
                "width": selection.width,
                "height": selection.height,
                "bg_data": selection.bg_data,
                "fg_data": selection.fg_data,
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def load_prefab(self, name: str) -> Optional[Selection]:
        """Loads a Selection object from a JSON prefab."""
        path = os.path.join(self.prefab_dir, f"{name}.json")
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)
            return Selection(
                x=0,
                y=0,
                width=data["width"],
                height=data["height"],
                bg_data=data.get("bg_data", []),
                fg_data=data.get("fg_data", []),
            )
        except Exception:
            return None

    def list_prefabs(self) -> List[str]:
        """Returns a list of available prefab names."""
        try:
            return sorted(
                [f[:-5] for f in os.listdir(self.prefab_dir) if f.endswith(".json")]
            )
        except Exception:
            return []
