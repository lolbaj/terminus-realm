# Terminus Realm

A mobile-optimized roguelike game built with Python, designed specifically for Termux and Android devices.

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/lolbaj/terminus-realm)

## Overview

**Terminus Realm** is a high-performance, terminal-based roguelike designed from the ground up for mobile users using Termux. It utilizes an Entity Component System (ECS) architecture and is optimized for low-power devices without sacrificing depth or performance.

## Features

- **Mobile-First Controls:** Prioritizes VI-keys (`w`, `a`, `s`, `d`) for efficient one-handed or thumb-based navigation.
- **Procedural Generation:** Explore an infinite world generated on-the-fly.
- **ECS Architecture:** Modular design for entities, components, and systems.
- **Performance Optimized:** Uses `numpy` for map data and double-buffered rendering.
- **Battery Efficient:** Optimized game loop and rendering to preserve mobile battery life.

## Installation 

```bash
# Clone the repository
git clone https://github.com/lolbaj/terminus-realm.git
cd terminus-realm

# Install dependencies
pip install -r requirements.txt
```

### Quick Start / Running the Game
```bash
python -m src.main
```

### Prerequisites

- Python 3.11+
- Termux (for Android users)

## Controls

| Key        | Action |
|-----       |--------|
| `w`, `a`, `s`, `d` | Move North, West, South, East |
| `q`, `e`, `z`, `c` | Move NW, NE, SW, SE |
| `Arrows`  | Move N, S, E, W   |
| `Space`   | Open Command Menu |
| `x` / `e` | Select / Interact |
| `i`       | Inventory         |
| `g`       | Pickup Item       |
| `t`       | Fire Ranged Weapon|
| `p`       | Quit Game         |

## Architecture

The project follows a modular structure focused on the **Entity Component System (ECS)** pattern.

- **`src/`**: Main game source code.
  - **`core/`**: Engine, Clock, and ECS base.
  - **`world/`**: Map generation, chunk management, and FOV.
  - **`entities/`**: Components, Entity Factory, and Systems.
  - **`ui/`**: Terminal rendering and HUD.
- **`map_editor/`**: Specialized tool for creating static maps.

## Development Status & Roadmap

### Current Progress
- [x] **Phase 1: Foundation** - Movement, ECS, and basic rendering.
- [x] **Phase 2: World** - Infinite chunk-based world and procedural generation.
- [x] **Phase 3: Loot 2.0** - Rarity, affixes, and equipment system.
- [ ] **Phase 4: Combat & Skills** - Active skills and advanced AI.
- [ ] **Phase 5: UX & Content** - Detailed character sheets and points of interest.

### Immediate Goals
1.  **Active Skills System:** Add mana/energy and castable spells.
2.  **Stat Allocation:** Manual stat points on level up.
3.  **Procedural Structures:** Place ruins and monster camps in the wilderness.

## Performance Report Summary

The game has been significantly optimized for mobile/Termux environments:
- **Rendering:** Uses double buffering and cell diffing to minimize ANSI escape codes and flicker.
- **Memory:** Employs `__slots__` in components to reduce footprint by ~40%.
- **World Gen:** Vectorized cellular automata with NumPy for fast, lag-free exploration.

---

Built with ❤️ for the Termux community.
