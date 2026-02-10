# Terminus Realm

A mobile-optimized MMORPG game with a Python client and Go server, designed specifically for Termux and Android devices.

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/lolbaj/terminus-realm)

## Overview

**Terminus Realm** is a high-performance, terminal-based MMORPG designed from the ground up for mobile users using Termux. It features a Python client for the terminal UI and a Go-based server for handling multiple players, world state management, and data persistence. The architecture utilizes an Entity Component System (ECS) and is optimized for low-power devices without sacrificing depth or performance.

## Architecture

- **Client (Python)**: Terminal-based UI using Rich and ECS for local rendering
- **Server (Go)**: Concurrent WebSocket server handling multiple players, game logic, and persistence
- **Database**: PostgreSQL for persistent player and world data

## Features

- **Mobile-First Controls:** Prioritizes VI-keys (`h`, `j`, `k`, `l`) for efficient one-handed or thumb-based navigation.
- **Procedural Generation:** Explore an infinite world generated on-the-fly.
- **ECS Architecture:** Modular design for entities, components, and systems.
- **Performance Optimized:** Uses `numpy` for map data and `numba` JIT compilation for FOV and pathfinding.
- **Battery Efficient:** Optimized game loop and rendering to preserve mobile battery life.
- **Multiplayer Support:** Connect with other players in a persistent world.
- **Data Persistence:** Player progress and world state saved to database.

## Quick Start

### Prerequisites

- Python 3.8+
- Go 1.21+
- PostgreSQL

### Server Setup

1. Install PostgreSQL and create a database
2. Set up environment variables:
   ```bash
   export DATABASE_URL="host=localhost user=terminus password=terminus dbname=terminus_realm sslmode=disable"
   ```
3. Navigate to the server directory and run:
   ```bash
   cd server
   go run cmd/server/main.go
   ```

### Client Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the multiplayer client:
   ```bash
   python src/main_multiplayer.py
   ```

## Project Structure

```
terminus-realm/
├── src/                 # Python client source code
├── server/              # Go server source code
│   ├── cmd/             # Main application
│   ├── handlers/        # WebSocket connection handlers
│   ├── messages/        # Message types and protocols
│   ├── models/          # Data models
│   ├── network/         # Network layer
│   ├── persistence/     # Database operations
│   └── services/        # Business logic
├── requirements.txt     # Python dependencies
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details.