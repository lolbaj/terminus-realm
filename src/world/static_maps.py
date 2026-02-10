"""
Manually designed static map chunks loaded from configuration.
"""

import toml
import os
from typing import Dict, List, Tuple

# Path to the maps configuration file
MAPS_CONFIG_PATH = os.path.join("src", "data", "static", "maps.toml")


def load_static_chunks() -> Dict[Tuple[int, int], List[str]]:
    """Load static map chunks from the TOML configuration file."""
    static_chunks = {}

    if not os.path.exists(MAPS_CONFIG_PATH):
        print(f"Warning: Maps config file not found at {MAPS_CONFIG_PATH}")
        return {}

    try:
        with open(MAPS_CONFIG_PATH, "r") as f:
            data = toml.load(f)

        for map_entry in data.get("maps", []):
            x = map_entry.get("x")
            y = map_entry.get("y")
            layout = map_entry.get("layout")

            if x is not None and y is not None and layout:
                # Handle multi-line string format
                if isinstance(layout, str):
                    layout = layout.strip().split("\n")

                static_chunks[(x, y)] = layout

        print(f"Loaded {len(static_chunks)} static map chunks from config.")
        return static_chunks

    except Exception as e:
        print(f"Error loading static maps: {e}")
        return {}


# Dictionary mapping chunk coordinates (x, y) to map data
# Populated at runtime
STATIC_CHUNKS = load_static_chunks()
