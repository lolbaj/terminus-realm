# Entity Component System (ECS) Implementation

This directory defines the "What" and "How" of the game world.

## Modules

- **`components.py`**: Dataclasses that define individual data properties for entities (e.g., `Position`, `Health`, `Render`).
- **`entities.py`**: The `EntityFactory` class for creating pre-defined entities like players, monsters, and items with specific component sets.
- **`ai_system.py`**: Controls monster behavior and decision-making.
- **`spawn_system.py`**: Manages the procedural placement of entities throughout the world chunks.
- **`boss_system.py`**: Logic for unique, high-difficulty encounters.

## Design Pattern

Systems in this directory are responsible for iterating over entities that possess a certain set of components and applying game logic to them each turn.
