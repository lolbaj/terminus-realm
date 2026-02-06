# Terminus Realm

A mobile-optimized roguelike game built with Python, designed specifically for Termux and mobile devices.

## Features

- Mobile-friendly controls (VI keys)
- Procedurally generated worlds
- Entity Component System (ECS) architecture
- Turn-based gameplay optimized for mobile
- Memory-efficient design for mobile devices

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the game: `python -m src.main`

## Controls

- `h`, `j`, `k`, `l`: Move left, down, up, right
- `y`, `u`, `b`, `n`: Move diagonally
- `Space`: Open command menu
- `Enter`: Select menu options

## Architecture

The game follows an Entity Component System (ECS) architecture:

- **Entities**: Unique IDs that represent game objects
- **Components**: Data containers that hold properties
- **Systems**: Functions that operate on entities with specific components

## Development Phases

1. **Phase 0**: Foundation Setup (Complete)
2. **Phase 1**: Basic World and Player Movement
3. **Phase 2**: Field of View and Visibility
4. **Phase 3**: World Expansion and Procedural Generation
5. **Phase 4**: Advanced Features and AI
6. **Phase 5**: Polish and Optimization

## Performance Optimizations

- Memory-efficient data structures (`__slots__`)
- Numba JIT compilation for critical functions
- Efficient rendering with diff algorithms
- Chunked world loading system