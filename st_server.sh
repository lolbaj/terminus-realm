#!/bin/bash

# Terminus Realm MMORPG Startup Script

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
SERVER_DIR="$PROJECT_ROOT/server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Terminus Realm MMORPG...${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
if ! command_exists go; then
    echo -e "${RED}Error: Go is not installed${NC}" >&2
    exit 1
fi

if ! command_exists psql; then
    echo -e "${RED}Error: PostgreSQL client (psql) is not installed${NC}" >&2
    exit 1
fi

# Start PostgreSQL if not running
echo -e "${YELLOW}Checking PostgreSQL status...${NC}"
if pg_ctl -D ~/postgres-data status >/dev/null 2>&1; then
    echo -e "${GREEN}PostgreSQL is already running${NC}"
else
    echo -e "${YELLOW}Starting PostgreSQL...${NC}"
    pg_ctl -D ~/postgres-data -l logfile start
    sleep 2  # Give PostgreSQL time to start
fi

# Wait a bit more for PostgreSQL to be fully ready
sleep 2

# Check if database exists, create if not
echo -e "${YELLOW}Checking database...${NC}"
if psql -h localhost -p 5432 -U u0_a377 -lqt | cut -d \| -f 1 | grep -qw terminus_realm; then
    echo -e "${GREEN}Database 'terminus_realm' exists${NC}"
else
    echo -e "${YELLOW}Creating database 'terminus_realm'...${NC}"
    createdb -h localhost -p 5432 -U u0_a377 terminus_realm
    echo -e "${GREEN}Database created successfully${NC}"
fi

# Set environment variables
export DATABASE_URL="${DATABASE_URL:-host=localhost port=5432 user=u0_a377 dbname=terminus_realm sslmode=disable}"
export PORT="${PORT:-8080}"

echo -e "${YELLOW}Environment variables:${NC}"
echo "DATABASE_URL: $DATABASE_URL"
echo "PORT: $PORT"

# Build the server (optional, but good for verifying everything compiles)
echo -e "${YELLOW}Building server...${NC}"
cd "$SERVER_DIR"
go build ./cmd/server
echo -e "${GREEN}Server built successfully${NC}"

# Start the Go server
echo -e "${YELLOW}Starting Go server on port $PORT...${NC}"
echo -e "${GREEN}Server is now running!${NC}"
echo -e "${GREEN}Connect with the Python client using: python src/main_multiplayer.py${NC}"
echo -e "${GREEN}Press Ctrl+C to stop the server${NC}"

# Run the server
go run cmd/server/main.go

# Cleanup function (called on script exit)
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    # Optionally stop PostgreSQL here if you started it just for this session
    # pg_ctl -D ~/postgres-data stop
}

trap cleanup EXIT