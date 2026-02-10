package persistence

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"

	"terminus-realm/server/models"

	_ "github.com/lib/pq" // PostgreSQL driver
)

// PostgresStore handles database operations using PostgreSQL
type PostgresStore struct {
	db *sql.DB
}

// NewPostgresStore creates a new PostgreSQL storage manager
func NewPostgresStore(connectionString string) (*PostgresStore, error) {
	db, err := sql.Open("postgres", connectionString)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %v", err)
	}

	// Test the connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %v", err)
	}

	store := &PostgresStore{db: db}
	
	// Initialize the database schema
	if err := store.initSchema(); err != nil {
		return nil, fmt.Errorf("failed to initialize schema: %v", err)
	}

	return store, nil
}

// initSchema initializes the database schema
func (dm *PostgresStore) initSchema() error {
	schema := `
	CREATE TABLE IF NOT EXISTS players (
		id TEXT PRIMARY KEY,
		username TEXT UNIQUE NOT NULL,
		x INTEGER NOT NULL,
		y INTEGER NOT NULL,
		z INTEGER NOT NULL,
		icon TEXT NOT NULL,
		color JSONB NOT NULL,
		hp INTEGER NOT NULL,
		max_hp INTEGER NOT NULL,
		gold INTEGER NOT NULL,
		level INTEGER NOT NULL,
		experience INTEGER NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS worlds (
		id SERIAL PRIMARY KEY,
		name TEXT UNIQUE NOT NULL,
		width INTEGER NOT NULL,
		height INTEGER NOT NULL,
		depth INTEGER NOT NULL,
		tiles JSONB NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS player_positions (
		player_id TEXT REFERENCES players(id),
		world_id INTEGER REFERENCES worlds(id),
		x INTEGER NOT NULL,
		y INTEGER NOT NULL,
		z INTEGER NOT NULL,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		UNIQUE(player_id)
	);
	`

	_, err := dm.db.Exec(schema)
	return err
}

// SavePlayer saves a player to the database
func (dm *PostgresStore) SavePlayer(player *models.Player) error {
	colorJSON, err := json.Marshal(player.Color)
	if err != nil {
		return fmt.Errorf("failed to marshal player color: %v", err)
	}

	query := `
	INSERT INTO players (id, username, x, y, z, icon, color, hp, max_hp, gold, level, experience) 
	VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	ON CONFLICT (id) 
	DO UPDATE SET 
		x = $3, y = $4, z = $5, 
		hp = $8, gold = $10, level = $11, experience = $12,
		updated_at = NOW()
	`

	_, err = dm.db.Exec(query,
		player.ID, player.Username, player.X, player.Y, player.Z,
		player.Icon, string(colorJSON), player.HP, player.MaxHP,
		player.Gold, player.Level, player.Experience)

	if err != nil {
		return fmt.Errorf("failed to save player: %v", err)
	}

	return nil
}

// LoadPlayer loads a player from the database by ID
func (dm *PostgresStore) LoadPlayer(playerID string) (*models.Player, error) {
	query := `SELECT id, username, x, y, z, icon, color, hp, max_hp, gold, level, experience, created_at, updated_at FROM players WHERE id = $1`
	
	var player models.Player
	var colorJSON string
	
	err := dm.db.QueryRow(query, playerID).Scan(
		&player.ID, &player.Username, &player.X, &player.Y, &player.Z,
		&player.Icon, &colorJSON, &player.HP, &player.MaxHP,
		&player.Gold, &player.Level, &player.Experience,
		&player.CreatedAt, &player.UpdatedAt,
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("player with ID %s not found", playerID)
		}
		return nil, fmt.Errorf("failed to load player: %v", err)
	}
	
	// Unmarshal the color JSON
	err = json.Unmarshal([]byte(colorJSON), &player.Color)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal player color: %v", err)
	}

	return &player, nil
}

// LoadPlayerByUsername loads a player from the database by username
func (dm *PostgresStore) LoadPlayerByUsername(username string) (*models.Player, error) {
	query := `SELECT id, username, x, y, z, icon, color, hp, max_hp, gold, level, experience, created_at, updated_at FROM players WHERE username = $1`
	
	var player models.Player
	var colorJSON string
	
	err := dm.db.QueryRow(query, username).Scan(
		&player.ID, &player.Username, &player.X, &player.Y, &player.Z,
		&player.Icon, &colorJSON, &player.HP, &player.MaxHP,
		&player.Gold, &player.Level, &player.Experience,
		&player.CreatedAt, &player.UpdatedAt,
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("player with username %s not found", username)
		}
		return nil, fmt.Errorf("failed to load player: %v", err)
	}
	
	// Unmarshal the color JSON
	err = json.Unmarshal([]byte(colorJSON), &player.Color)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal player color: %v", err)
	}

	return &player, nil
}

// SaveWorld saves a world to the database
func (dm *PostgresStore) SaveWorld(name string, gameMap *models.GameMap) error {
	tilesJSON, err := json.Marshal(gameMap.Tiles)
	if err != nil {
		return fmt.Errorf("failed to marshal world tiles: %v", err)
	}

	query := `
	INSERT INTO worlds (name, width, height, depth, tiles) 
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (name) 
	DO UPDATE SET 
		width = $2, height = $3, depth = $4, tiles = $5,
		updated_at = NOW()
	`

	_, err = dm.db.Exec(query,
		name, gameMap.Width, gameMap.Height, gameMap.Depth,
		string(tilesJSON))

	if err != nil {
		return fmt.Errorf("failed to save world: %v", err)
	}

	return nil
}

// LoadWorld loads a world from the database by name
func (dm *PostgresStore) LoadWorld(name string) (*models.GameMap, error) {
	query := `SELECT width, height, depth, tiles FROM worlds WHERE name = $1`
	
	var gameMap models.GameMap
	var tilesJSON string
	
	err := dm.db.QueryRow(query, name).Scan(
		&gameMap.Width, &gameMap.Height, &gameMap.Depth, &tilesJSON,
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("world with name %s not found", name)
		}
		return nil, fmt.Errorf("failed to load world: %v", err)
	}
	
	// Unmarshal the tiles JSON
	var tiles [][]int
	err = json.Unmarshal([]byte(tilesJSON), &tiles)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal world tiles: %v", err)
	}
	
	gameMap.Tiles = tiles

	return &gameMap, nil
}

// Close closes the database connection
func (dm *PostgresStore) Close() error {
	log.Println("Closing database connection...")
	return dm.db.Close()
}