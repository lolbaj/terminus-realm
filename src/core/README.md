# Core Engine & ECS

The `core` module provides the fundamental building blocks of Terminus Realm.

## Modules

- **`engine.py`**: The `GameEngine` class coordinates all systems, manages state transitions, and runs the main game loop.
- **`ecs.py`**: A custom, lightweight Entity Component System implementation. It provides the `EntityManager` for tracking components and their associations with entities.
- **`clock.py`**: Manages turn-based timing and ensures consistent game pacing.

## Design Philosophy

The core is designed to be as decoupled as possible. The `GameEngine` doesn't know about specific entity types; instead, it delegates logic to specialized **Systems** (found in `src/entities/`) that operate on entities with specific sets of **Components**.
