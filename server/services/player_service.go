package services

import (
	"errors"
	"fmt"
	"sync"
	"time"

	"terminus-realm/server/models"
	"terminus-realm/server/persistence"
)

// PlayerService manages player-related operations
type PlayerService struct {
	players    map[string]*models.Player
	world      *WorldService
	db         persistence.Storage
	mutex      sync.RWMutex
}

// NewPlayerService creates a new player service
func NewPlayerService(world *WorldService, db persistence.Storage) *PlayerService {
	ps := &PlayerService{
		players: make(map[string]*models.Player),
		world:   world,
		db:      db,
	}
	
	// Load existing players from database
	ps.loadPlayersFromDB()
	
	return ps
}

// loadPlayersFromDB loads all players from the database
func (ps *PlayerService) loadPlayersFromDB() {
	// For now, we'll just log that this would happen
	// In a real implementation, we would load all players from the DB
}

// GetOrCreatePlayer gets an existing player or creates a new one
func (ps *PlayerService) GetOrCreatePlayer(username string) (*models.Player, error) {
	ps.mutex.Lock()
	defer ps.mutex.Unlock()

	// Check if player already exists in memory
	for _, player := range ps.players {
		if player.Username == username {
			return player, nil
		}
	}

	// Try to load player from database
	player, err := ps.db.LoadPlayerByUsername(username)
	if err != nil {
		// Player doesn't exist in DB, create a new one
		player = &models.Player{
			ID:         fmt.Sprintf("player_%d", time.Now().UnixNano()),
			Username:   username,
			X:          25, // Starting position from config
			Y:          25,
			Z:          0,
			Icon:       "🧙", // Default player icon
			Color:      []int{255, 255, 255}, // White color
			HP:         100, // From config
			MaxHP:      100,
			Gold:       0,
			Level:      1,
			Experience: 0,
			CreatedAt:  time.Now(),
			UpdatedAt:  time.Now(),
		}

		// Save the new player to the database
		if err := ps.db.SavePlayer(player); err != nil {
			return nil, fmt.Errorf("failed to save new player to database: %v", err)
		}
	} else {
		// Player loaded from DB, update in-memory cache
		ps.players[player.ID] = player
	}

	// Add player to the world if not already added
	ps.world.AddPlayer(player)

	return player, nil
}

// GetPlayer retrieves a player by ID
func (ps *PlayerService) GetPlayer(playerID string) (*models.Player, error) {
	ps.mutex.RLock()
	defer ps.mutex.RUnlock()

	player, exists := ps.players[playerID]
	if !exists {
		return nil, errors.New("player not found")
	}
	return player, nil
}

// UpdatePlayer updates a player's information
func (ps *PlayerService) UpdatePlayer(player *models.Player) error {
	ps.mutex.Lock()
	defer ps.mutex.Unlock()

	if _, exists := ps.players[player.ID]; !exists {
		return errors.New("player not found")
	}

	player.UpdatedAt = time.Now()
	ps.players[player.ID] = player
	
	// Save the updated player to the database
	if err := ps.db.SavePlayer(player); err != nil {
		return fmt.Errorf("failed to save updated player to database: %v", err)
	}
	
	return nil
}

// UseItem handles using an item
func (ps *PlayerService) UseItem(playerID string, itemID string, target string) (interface{}, error) {
	// For now, just return a success message
	// In a real implementation, this would process the item effect
	return map[string]interface{}{
		"type":    "item_used",
		"item_id": itemID,
		"result":  "success",
	}, nil
}