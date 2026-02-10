package persistence

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"terminus-realm/server/models"
)

// JSONStore handles data persistence using a local JSON file
type JSONStore struct {
	filePath string
	mutex    sync.RWMutex
	data     *JSONData
}

// JSONData represents the structure of the JSON database
type JSONData struct {
	Players map[string]*models.Player  `json:"players"`
	Worlds  map[string]*models.GameMap `json:"worlds"`
}

// NewJSONStore creates a new JSON storage manager
func NewJSONStore(filePath string) (*JSONStore, error) {
	store := &JSONStore{
		filePath: filePath,
		data: &JSONData{
			Players: make(map[string]*models.Player),
			Worlds:  make(map[string]*models.GameMap),
		},
	}

	// Load existing data if file exists
	if _, err := os.Stat(filePath); err == nil {
		if err := store.loadFromFile(); err != nil {
			return nil, fmt.Errorf("failed to load JSON store: %v", err)
		}
	} else {
		// Create file if it doesn't exist
		if err := store.saveToFile(); err != nil {
			return nil, fmt.Errorf("failed to create JSON store file: %v", err)
		}
	}

	return store, nil
}

// loadFromFile loads data from the JSON file
func (js *JSONStore) loadFromFile() error {
	js.mutex.Lock()
	defer js.mutex.Unlock()

	file, err := os.ReadFile(js.filePath)
	if err != nil {
		return err
	}

	return json.Unmarshal(file, js.data)
}

// saveToFile saves data to the JSON file
func (js *JSONStore) saveToFile() error {
	js.mutex.Lock()
	defer js.mutex.Unlock()

	data, err := json.MarshalIndent(js.data, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(js.filePath, data, 0644)
}

// SavePlayer saves a player to the store
func (js *JSONStore) SavePlayer(player *models.Player) error {
	js.mutex.Lock()
	js.data.Players[player.ID] = player
	js.mutex.Unlock()

	return js.saveToFile()
}

// LoadPlayer loads a player by ID
func (js *JSONStore) LoadPlayer(playerID string) (*models.Player, error) {
	js.mutex.RLock()
	defer js.mutex.RUnlock()

	player, exists := js.data.Players[playerID]
	if !exists {
		return nil, fmt.Errorf("player with ID %s not found", playerID)
	}

	return player, nil
}

// LoadPlayerByUsername loads a player by username
func (js *JSONStore) LoadPlayerByUsername(username string) (*models.Player, error) {
	js.mutex.RLock()
	defer js.mutex.RUnlock()

	for _, player := range js.data.Players {
		if player.Username == username {
			return player, nil
		}
	}

	return nil, fmt.Errorf("player with username %s not found", username)
}

// SaveWorld saves a world to the store
func (js *JSONStore) SaveWorld(name string, gameMap *models.GameMap) error {
	js.mutex.Lock()
	js.data.Worlds[name] = gameMap
	js.mutex.Unlock()

	return js.saveToFile()
}

// LoadWorld loads a world by name
func (js *JSONStore) LoadWorld(name string) (*models.GameMap, error) {
	js.mutex.RLock()
	defer js.mutex.RUnlock()

	world, exists := js.data.Worlds[name]
	if !exists {
		return nil, fmt.Errorf("world with name %s not found", name)
	}

	return world, nil
}

// Close closes the store (no-op for JSON store)
func (js *JSONStore) Close() error {
	return nil
}
