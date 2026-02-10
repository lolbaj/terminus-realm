# Terminus Realm Go Server

This is the Go-based server for the Terminus Realm MMORPG. It handles multiple concurrent players, world state management, and data persistence.

## Architecture

The server is built with the following components:

- **Handlers**: Manage client connections and message routing
- **Messages**: Define the communication protocol between client and server
- **Models**: Define the data structures for game entities
- **Network**: Handle WebSocket connections and communication
- **Persistence**: Manage database operations for player and world data
- **Services**: Core game logic and business rules

## Dependencies

- Go 1.21+
- PostgreSQL database
- `github.com/gorilla/websocket` - For WebSocket connections
- `github.com/lib/pq` - For PostgreSQL connectivity

## Setup

1. Install Go 1.21+ and PostgreSQL
2. Set up the database with appropriate credentials
3. Set the DATABASE_URL environment variable:
   ```bash
   export DATABASE_URL="host=localhost user=terminus password=terminus dbname=terminus_realm sslmode=disable"
   ```
4. Run the server:
   ```bash
   cd cmd/server
   go run main.go
   ```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (defaults to local development settings)
- `PORT`: Port to run the server on (defaults to 8080)

## API

The server communicates with clients via WebSocket using JSON messages. Supported message types include:

- `login`: Authenticate a player
- `move`: Move a player in a direction
- `chat`: Send a chat message
- `combat`: Perform a combat action
- `item_use`: Use an item
- `update`: Receive world state updates