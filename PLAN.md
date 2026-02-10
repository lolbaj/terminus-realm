# 🧠 ENHANCED CORE VISION

## Input Paradigm
- **VI Keys**: h, j, k, l for movement (mobile-friendly)
- **Command Palette**: Space/Enter for menu navigation
- **Touch Support**: Mouse reporting in terminals when available
- **Input Buffer**: Prevent key-spam lag with queue system

## Pacing & Visual Style
- **Turn-Based**: Conserves battery and prevents lag during GC
- **Semi-Graphical**: Nerd fonts when available, fallback to ASCII
- **Optimized Rendering**: Dirty rectangle tracking and diffing

# 🗺️ ENHANCED WORLD & MAP SYSTEM

## 1. Infinite Rolling Buffer
- Maintain 3x3 grid of chunks in memory
- Dynamic loading/unloading as player moves
- Memory cap regardless of world size

## 2. Procedural Generation Pipeline
- **Noise Maps**: Perlin/Simplex with numba acceleration
- **Layered Approach**: Elevation → Biomes → Structures
- **Cellular Automata**: Cave/dungeon generation
- **Bitmasking**: Connected texture rendering

## 3. Sparse Entity Storage
- **Terrain**: Dense numpy array (uint8)
- **Entities**: Spatial hash dictionary
- **Spatial Indexing**: Quadtree for collision detection

# 🧍 ENHANCED PLAYER & INPUT SYSTEM

## Input Abstraction Layer
- **VI Movement**: h/j/k/l + diagonal keys (y/u/b/n)
- **Action Keys**: Space for menu, Enter for selection
- **Command Queue**: Single action per tick to prevent spam

## Configuration System
- **Pydantic Models**: Type-safe configuration
- **TOML Files**: Human-readable settings
- **Hot Reload**: Config changes without restart

# 👁️ ENHANCED VISUALS & RENDERING

## Field of View
- **Recursive Shadowcasting**: Efficient ray casting
- **Visibility Layers**: Current, previously seen, hidden
- **Lighting System**: Dynamic light sources and shadows

## Rendering Engine
- **Double Buffer**: Current vs previous frame
- **Diff Algorithm**: Only render changed cells
- **Batch Output**: Single terminal write per frame
- **Rich/Blessed**: Advanced terminal formatting

# ⚔️ ENHANCED COMBAT & SYSTEMS

## ECS Architecture
- **Dataclasses**: Memory-efficient components
- **EntityManager**: Component-based entity management
- **Systems**: Process entities with specific component sets
- **Event Bus**: Decoupled system communication

## Data-Driven Design
- **JSON/TOML Schemas**: Structured game data
- **Asset Pipeline**: Hot-loading of game assets
- **Modular Systems**: Easy to extend and modify

# ⚙️ DETAILED MODULE STRUCTURE

```
/src
├── __init__.py
├── main.py                 # Entry point
├── config.py              # Game settings and constants
├── /core
│   ├── __init__.py
│   ├── engine.py          # Main game loop
│   ├── clock.py           # Turn-based timing system
│   └── ecs.py             # Entity Component System base classes
├── /utils
│   ├── __init__.py
│   ├── math.py            # Vector math, distance calculations
│   ├── perf.py            # Performance monitoring tools
│   └── serialization.py   # Save/load utilities
├── /data
│   ├── __init__.py
│   ├── loader.py          # Data loading from JSON/TOML
│   ├── /schemas           # Pydantic schemas for validation
│   └── /static            # JSON files (items, enemies, etc.)
├── /world
│   ├── __init__.py
│   ├── generator.py       # Procedural generation (using numpy)
│   ├── map.py             # Map representation and FOV
│   ├── chunk_manager.py   # Chunk loading/unloading
│   └── pathfinding.py     # A* pathfinding algorithm
├── /entities
│   ├── __init__.py
│   ├── components.py      # Component definitions
│   ├── entities.py        # Entity factory and management
│   ├── systems.py         # System implementations
│   └── templates.py       # Entity templates from data files
├── /systems
│   ├── __init__.py
│   ├── movement.py        # Movement system
│   ├── combat.py          # Combat system
│   ├── fov.py             # Field of view system
│   ├── ai.py              # AI behaviors
│   └── rendering.py       # Rendering system
├── /input
│   ├── __init__.py
│   ├── handler.py         # Input processing
│   └── bindings.py        # Key bindings configuration
└── /ui
    ├── __init__.py
    ├── renderer.py        # Terminal rendering (using rich/blessed)
    ├── menus.py           # Menu screens
    └── hud.py             # Heads-up display elements
```

# 🚀 ENHANCED PERFORMANCE STRATEGIES

## Memory Management
- `__slots__` for all classes (40-50% memory reduction)
- Object pooling for temporary entities
- Weak references where appropriate
- Generational garbage collection tuning

## Processing Optimization
- `numba.jit` for critical functions (FOV, pathfinding)
- Spatial indexing (quadtree) for collision detection
- Batch processing of similar operations
- Caching of expensive calculations

## I/O Optimization
- Async asset loading with threading
- Compressed save files (gzip/lzma)
- Asset caching during gameplay

## Rendering Optimization
- Dirty rectangle tracking
- Character tile-based rendering
- Pre-computed lighting maps
- FPS limiting (15-30 FPS for battery conservation)

# 📚 RECOMMENDED LIBRARIES

## Core Libraries
- `numpy`: Array operations and mathematical computations
- `numba`: JIT compilation for performance-critical code
- `rich`: Advanced terminal UI and formatting
- `blessed`: Cross-platform terminal handling
- `pydantic`: Data validation and settings management
- `tcod`: Roguelike-specific utilities (optional)

## Utility Libraries
- `orjson`: Faster JSON processing (optional)
- `structlog`: Structured logging
- `click`: Command-line interface
- `toml`: Configuration file parsing (built-in in Python 3.11+)

# 🚧 REVISED DEVELOPMENT PHASES

## Phase 0: Foundation Setup (Week 1)
- Project structure and dependency setup
- Basic ECS framework implementation
- Configuration system with pydantic
- Data loading from JSON/TOML

## Phase 1: Basic World (Week 2)
- Simple 20x20 map generation with numpy
- Player character with position component
- Basic terminal rendering using blessed/rich
- Simple vi-key input handling

## Phase 2: Movement & Visibility (Week 3)
- Player movement with collision detection
- Basic FOV implementation (recursive shadowcasting)
- Wall/floor rendering with visibility states
- Basic enemy following behavior

## Phase 3: World Expansion (Week 4-5)
- Chunked world system (rolling 3x3 buffer)
- Procedural generation with noise algorithms
- Item system and inventory implementation
- Multiple dungeon levels

## Phase 4: Advanced Features (Week 6-7)
- Advanced AI behaviors (patrol, chase, flee)
- Equipment and stat system
- Shop/trading mechanics
- Save/load functionality

## Phase 5: Polish & Optimization (Week 8)
- Mobile-specific performance optimization
- UI improvements and menu systems
- Gameplay balance adjustments
- Bug fixes and stability improvements

This enhanced plan provides a more structured approach with better libraries, clearer architecture, and more realistic development phases for a mobile-optimized roguelike game.
