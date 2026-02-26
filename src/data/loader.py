"""
Data loading system for the game.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import toml


class DataLoader:
    """Handles loading game data from various file formats."""

    def __init__(self, data_dir: str = "src/data/static"):
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, Any] = {}

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load data from a JSON file."""
        if f"json_{filename}" in self._cache:
            return self._cache[f"json_{filename}"]

        filepath = self.data_dir / f"{filename}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._cache[f"json_{filename}"] = data
        return data

    def load_toml(self, filename: str) -> Dict[str, Any]:
        """Load data from a TOML file."""
        if f"toml_{filename}" in self._cache:
            return self._cache[f"toml_{filename}"]

        filepath = self.data_dir / f"{filename}.toml"
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = toml.load(f)

        self._cache[f"toml_{filename}"] = data
        return data

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load data from a YAML file."""
        if f"yaml_{filename}" in self._cache:
            return self._cache[f"yaml_{filename}"]

        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required to load YAML files")

        filepath = self.data_dir / f"{filename}.yaml"
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._cache[f"yaml_{filename}"] = data
        return data

    def get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific item."""
        try:
            items_data = self.load_json("items")
            return items_data.get(item_id)
        except FileNotFoundError:
            return None

    def get_monster_data(self, monster_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific monster."""
        try:
            monsters_data = self.load_json("monsters")
            return monsters_data.get(monster_id)
        except FileNotFoundError:
            return None

    def get_tile_data(self, tile_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific tile type."""
        try:
            tiles_data = self.load_json("tiles")
            return tiles_data.get(tile_id)
        except FileNotFoundError:
            return None

    def get_leveling_data(self) -> Optional[Dict[str, Any]]:
        """Get leveling configuration."""
        try:
            return self.load_json("leveling")
        except FileNotFoundError:
            return None

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# Global data loader instance
DATA_LOADER = DataLoader()
