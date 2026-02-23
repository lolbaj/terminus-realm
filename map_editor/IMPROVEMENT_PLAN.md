# Map Editor Improvement Plan

This document outlines the strategic roadmap for the Terminus Realm Map Editor. The goal is to evolve the editor from a basic tile-painter into a powerful world-building toolkit.

## Phase 1: Architectural Refactoring
The current `editor.py` is a monolithic class (~450 lines). To support advanced features, the logic should be decoupled.

- [x] **Modularization**: Split `editor.py` into specialized modules:
    - `renderer.py`: Handles buffer management, double-cell logic, and color escape codes.
    - `input_handler.py`: Maps keypresses to actions and manages input states (e.g., Paint Mode).
    - `map_manager.py`: Encapsulates the map grid, metadata, and validation.
    - `tools.py`: Contains logic for Brush, Rectangle, Flood Fill, and Selection.
- [x] **Error Handling**: Replace broad `except:` blocks with specific exception handling for file I/O and TOML parsing to provide better feedback to the user.

## Phase 2: Feature Set Expansion
Enhancing the capabilities of the editor to handle complex map scenarios.

- [x] **Layer Support**:
    - Implement a two-layer system: **Background** (Terrain) and **Foreground** (Decorations/Objects).
    - Toggle layer visibility and active editing layer.
- [x] **Multi-Map Management**:
    - Add a "Map Browser" mode to view, select, and delete maps within a single TOML file (currently only loads the first map).
    - Add a "Duplicate Map" feature for creating variations.
- [ ] **Structure Prefabs**:
    - Allow users to save selections as "Stamps" or "Prefabs" (e.g., a standard 5x5 house).
    - Provide a library of common structures (Added Basic Prefabs).
- [x] **Visual Feedback**:
    - Added "Ghost" indicators for Brush and Rectangle tools.
    - Implemented interactive "Ghost Paste" mode for precise clipboard placement.
- [x] **Zoom Functionality**:
    - Implemented Zoom Out (1x1 mode) and Zoom In (2x1 mode) using `[` and `]`.
    - Integrated with rendering engine for seamless scaling.

## Phase 3: UX & Integration
Polishing the user experience and deepening the connection with the game engine.

- [x] **Palette Organization**:
    - Reorganized tiles into logical categories (Ground, Plants, Walls, Special).
    - Added missing tiles (Pavement, Box Drawing characters).
- [ ] **Dynamic Overrides**:
    - Support custom tile overrides per map file.
- [ ] **Auto-Tiling Logic**: 
    - Implement basic edge-detection for walls (Done) and water (Pending specialized tiles).
- [x] **Game Engine Sync**:
    - Add a "Test in Game" hotkey that launches the game engine directly at the current map coordinates.
- [ ] **Undo/Redo Persistence**: 
    - Optionally save the undo history to a temporary file to prevent loss of work on accidental crashes.

## Phase 4: Technical Polish
- [x] **Performance**: Optimize the buffer-diff algorithm further for extremely large terminal windows.
- [ ] **Cross-Platform**: Ensure full compatibility with various terminal emulators (Termux, Alacritty, iTerm2, etc.) regarding emoji width and 24-bit color support.
- [x] **Mouse Support**: 
    - Basic drawing support.
    - Added UI Interaction: Click to select tiles from Palette.
