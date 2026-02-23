# Game Data & Serialization

This directory manages all static game data and session persistence.

## Modules

- **`loader.py`**: A centralized class for loading game data from JSON and TOML files.
- **`static/`**: Folder containing all hand-written game data files:
  - `items.json`: Equipment, consumables, and loot.
  - `monsters.json`: Monster stats, templates, and behaviors.
  - `tiles.json`: Visual representation and properties of terrain.
  - `leveling.json`: Experience thresholds and stat gains.
  - `maps.toml`: Pre-defined static map layouts.
- **`saves/`**: Folder for persistent world data (e.g., `persistent_world.pkl`).

## Design Pattern

Data in this directory is intended to be decoupled from logic. This means you can add new monsters or items by simply editing JSON files, without writing new Python code.
