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
| `Ctrl+W` | Toggle Minimap |
| `Ctrl+G` | Test Current Map in Game |
| `Ctrl+S` | Save map |
| `l` / `n` / `m` | Load / New / Metadata |
| `q` | Quit |

## Tile Palette

```
Row 1: . # + | -   (Floor, Wall, Door, Vertical Wall, Horizontal Wall)
Row 2: , T ~ S *   (Grass, Tree, Water, Sand, Snow)
Row 3: = A C I P   (Lava, Ash, Cactus, Ice, Pavement)
Row 4: > < @       (Stairs Down, Stairs Up, Player Start)
```

Press `1-9` to select tiles in order from the palette.

## Map Format

Maps are saved in TOML format:

```toml
[[maps]]
name = "Town Center"
x = 0
y = 0
layout = """
TTTTT.....TTTTT
TTTT#.....#TTTT
TT..#.....#..TT
TT..+.....+..TT
TT..#.....#..TT
TTTT#.....#TTTT
TTTTT.....TTTTT
"""
```

- `x`, `y`: World coordinates for map positioning
- `layout`: ASCII art map representation

## Tips

1. **Start with a border**: Create walls or trees around your map edges
2. **Use selection for structures**: Draw a room once, then copy/paste
3. **Flood fill for terrain**: Quickly fill large areas
4. **Number keys for speed**: Memorize tile positions for fast switching
5. **Undo liberally**: `z` is your friend when experimenting

## Troubleshooting

### Flickering display
The editor uses optimized single-pass rendering to minimize flicker. If you still experience issues:

1. **Use simple mode**: Run with `-s` flag or press `t` in the editor
   ```bash
   python map_editor/editor.py -s
   ```

2. **Ensure your terminal supports ANSI escape codes**
3. **Try a different terminal emulator**
4. **Reduce the viewport size**

### Colors not showing
Some terminals may not support 256-color mode. Use simple mode (`-s` flag or press `t`) for ASCII-only display.
