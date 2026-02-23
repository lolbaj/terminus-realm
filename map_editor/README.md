# Map Editor for Terminus Realm

A sprite sheet-style terminal map editor with a clean layout:
- **Map view** occupies the upper portion in 16:9 aspect ratio
- **Tile palette, info, and controls** are displayed at the bottom

## Features

- **16:9 Aspect Ratio**: Map viewport maintains 16:9 proportions
- **Tile Palette**: Select from predefined tiles (walls, floors, water, trees, etc.)
- **Drawing Tools**: Paint tiles with adjustable brush size
- **Selection System**: Select, copy, cut, paste, and move regions
- **Flood Fill**: Fill connected areas with a single tile
- **Undo/Redo**: Full undo/redo support
- **Save/Load**: Edit maps in TOML format compatible with the game
- **Auto-sized viewport**: Adapts to your terminal size while keeping 16:9
- **Simple ASCII mode**: Press `t` for reduced flicker

## Running the Editor

```bash
# Run with Python
python map_editor/editor.py

# Edit an existing map
python map_editor/editor.py src/data/static/maps.toml

# Create a new map with custom size
python map_editor/editor.py -w 80 -H 60

# Run as module
python -m map_editor

# Simple ASCII mode (no colors - less flicker)
python map_editor/editor.py -s
```

## Controls

### Movement & Selection
| Key | Action |
|-----|--------|
| `WASD` or `Arrow Keys` | Move cursor |
| `Mouse` | Click or Drag to draw |
| `[` / `]` | Switch between multiple maps in file |
| `TAB` | Switch between BG and FG layers |

### Tile Selection
| Key | Action |
|-----|--------|
| `1-9` | Select tile from current category |
| `Ctrl+K` | Cycle tile categories (Terrain, Architecture, Special) |
| `r` | Pick tile from map (eyedropper) |

### Drawing Tools
| Key | Action |
|-----|--------|
| `Space` | Paint current tile |
| `p` | Toggle continuous Paint Mode |
| `b` | Start/end Rectangle tool |
| `+` / `-` | Increase/decrease brush size |
| `f` | Flood fill |
| `Ctrl+A` | Toggle Auto-Tiling (Wall connection logic) |

### Selection & Prefabs
| Key | Action |
|-----|--------|
| `s` | Start/end selection |
| `c` / `v` / `x` | Copy / Paste / Cut |
| `d` or `Backspace` | Delete selection |
| `Ctrl+P` | Save selection as Prefab (Stamp) |
| `Ctrl+O` | Load Prefab into clipboard |

### Editor System
| Key | Action |
|-----|--------|
| `z` / `y` | Undo / Redo |
| `Ctrl+G` | Test Current Map in Game |
| `Ctrl+S` | Save map |
| `l` / `n` / `m` | Load / New / Metadata |
| `q` | Quit |

## Roadmap & Progress

The goal is to evolve the editor into a powerful world-building toolkit.

### Phase 1: Architectural Refactoring
- [x] **Modularization**: Decoupled monolithic `editor.py` into specialized modules (`renderer`, `input_handler`, `map_manager`, etc.)
- [x] **Error Handling**: Improved feedback for I/O and parsing errors.

### Phase 2: Feature Expansion
- [x] **Layer Support**: Two-layer system (BG/FG) with visibility toggles.
- [x] **Multi-Map Management**: Map browser and duplication within TOML files.
- [x] **Visual Feedback**: "Ghost" indicators and interactive "Ghost Paste" mode.
- [x] **Zoom Functionality**: Scale between 1x1 and 2x1 cell modes.
- [ ] **Structure Prefabs**: Expand library of common structures (Basic Prefabs implemented).

### Phase 3: UX & Integration
- [x] **Palette Organization**: Tile categories and new drawing characters.
- [x] **Game Engine Sync**: Hotkey to test current map in-game.
- [ ] **Auto-Tiling Logic**: Full edge-detection for all terrain types.
- [ ] **Undo/Redo Persistence**: Optional save for undo history.

### Phase 4: Technical Polish
- [x] **Performance**: Optimized buffer-diff for large terminals.
- [x] **Mouse Support**: Drawing and UI interaction.
- [ ] **Cross-Platform**: Compatibility across various terminal emulators.

---

Built for building worlds in Terminus Realm.
