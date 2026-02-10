# Terminus Realm

A mobile-optimized roguelike game built with Python, designed specifically for Termux and Android devices.

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/lolbaj/terminus-realm)

## Overview

**Terminus Realm** is a high-performance, terminal-based roguelike designed from the ground up for mobile users using Termux. It utilizes an Entity Component System (ECS) architecture and is optimized for low-power devices without sacrificing depth or performance.

## Features

- **Mobile-First Controls:** Prioritizes VI-keys (`h`, `j`, `k`, `l`) for efficient one-handed or thumb-based navigation.
- **Procedural Generation:** Explore an infinite world generated on-the-fly.
- **ECS Architecture:** Modular design for entities, components, and systems.
- **Performance Optimized:** Uses `numpy` for map data and `numba` JIT compilation for FOV and pathfinding.
- **Battery Efficient:** Optimized game loop and rendering to preserve mobile battery life.

## Quick Start

### Prerequisites

- Python 3.11+
- Termux (for Android users)

### Installation

```bash
# Clone the repository
git clone https://github.com/lolbaj/terminus-realm.git
cd terminus-realm

# Install dependencies
pip install -r requirements.txt
```

### Running the Game

```bash
python src/main.py
```

## Controls

| Key | Action |
|-----|--------|
| `w`, `a`, `s`, `d` | Move North, West, South, East |
| `q`, `e`, `z`, `c` | Move NW, NE, SW, SE |
| `Arrows` | Move N, S, E, W |
| `Space` | Open Command Menu |
| `x` / `e` | Select / Interact |
| `i` | Inventory |
| `g` | Pickup Item |
| `t` | Fire Ranged Weapon |
| `p` | Quit Game |

## Architecture

- **Core Engine:** `src/core/engine.py` handles the main loop.
- **ECS:** Base implementation in `src/core/ecs.py`.
- **World Gen:** Chunk-based loading in `src/world/chunk_manager.py`.

## Development Roadmap

- [x] **Phase 0-1:** Foundation & Movement
- [x] **Phase 2:** Field of View & Visibility
- [x] **Phase 3:** World Expansion & Procedural Generation
- [ ] **Phase 4:** Advanced AI & Combat Systems (In Progress)
- [ ] **Phase 5:** Polish, Sound, and Optimization

---

Built with ❤️ for the Termux community.
