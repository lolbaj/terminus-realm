# Terminus Realm - Source Code

This directory contains the core game logic, entity management, world generation, and user interface for Terminus Realm.

## Structure

- **`core/`**: The heart of the game. Handles the main loop, time management, and the Entity Component System (ECS) foundation.
- **`entities/`**: Manages all game objects (player, monsters, items). Contains component definitions, entity factories, and systems that process game logic.
- **`world/`**: Handles the physical environment. Includes chunk-based procedural generation, map representation, and Field of View (FOV) logic.
- **`data/`**: Static game data (items, monsters, maps) stored in JSON/TOML, and save file management.
- **`ui/`**: Responsible for rendering the game to the terminal and managing the HUD and menus.
- **`input/`**: Processes user input and maps it to game actions.
- **`utils/`**: General helper functions and performance monitoring tools.

## Key Files

- **`main.py`**: The entry point of the application.
- **`config.py`**: Global settings and game constants.

## How to Run

From the project root:
```bash
python -m src.main
```
