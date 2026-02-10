package services

import (
	"errors"
	"math/rand"
	"sync"

	"terminus-realm/server/messages"
	"terminus-realm/server/models"
	"terminus-realm/server/persistence"
)

// WorldService manages the game world
type WorldService struct {
	chunkManager *ChunkManager
	players      map[string]*models.Player
	monsters     map[string]*models.Monster
	items        map[string]*models.Item
	db           persistence.Storage
	worldMutex   sync.RWMutex
}

// NewWorldService creates a new world service
func NewWorldService(db persistence.Storage) *WorldService {
	ws := &WorldService{
		chunkManager: NewChunkManager(50, 1), // Chunk size 50, buffer radius 1
		players:      make(map[string]*models.Player),
		monsters:     make(map[string]*models.Monster),
		items:        make(map[string]*models.Item),
		db:           db,
	}

	// Initialize the world with some content
	ws.initializeWorld()

	return ws
}

// initializeWorld sets up the initial world state
func (ws *WorldService) initializeWorld() {
	// For now, we'll just create a basic map
	// In a real implementation, this would load from persistent storage or generate procedurally
}

// AddPlayer adds a player to the world
func (ws *WorldService) AddPlayer(player *models.Player) {
	ws.worldMutex.Lock()
	defer ws.worldMutex.Unlock()

	ws.players[player.ID] = player
}

// RemovePlayer removes a player from the world
func (ws *WorldService) RemovePlayer(playerID string) {
	ws.worldMutex.Lock()
	defer ws.worldMutex.Unlock()

	delete(ws.players, playerID)
}

// MovePlayer processes a player movement request
func (ws *WorldService) MovePlayer(playerID string, direction string) (*models.Position, error) {
	ws.worldMutex.Lock()
	defer ws.worldMutex.Unlock()

	player, exists := ws.players[playerID]
	if !exists {
		return nil, errors.New("player not found")
	}

	// Determine new position based on direction
	newPos := models.Position{
		X: player.X,
		Y: player.Y,
		Z: player.Z,
	}

	switch direction {
	case "north":
		newPos.Y--
	case "south":
		newPos.Y++
	case "east":
		newPos.X++
	case "west":
		newPos.X--
	case "northeast":
		newPos.X++
		newPos.Y--
	case "northwest":
		newPos.X--
		newPos.Y--
	case "southeast":
		newPos.X++
		newPos.Y++
	case "southwest":
		newPos.X--
		newPos.Y++
	default:
		return nil, errors.New("invalid direction")
	}

	// Check if the new position is walkable
	chunk := ws.chunkManager.GetChunk(newPos.X, newPos.Y)
	localX := newPos.X - chunk.X*ws.chunkManager.chunkSize
	localY := newPos.Y - chunk.Y*ws.chunkManager.chunkSize

	// Correct for negative coordinates if necessary (though getChunkCoordinates handles chunk selection, 
	// we still need correct local indexing if we crossed a boundary)
	if localX < 0 {
		localX += ws.chunkManager.chunkSize
	}
	if localY < 0 {
		localY += ws.chunkManager.chunkSize
	}

	if localX >= 0 && localX < ws.chunkManager.chunkSize && localY >= 0 && localY < ws.chunkManager.chunkSize {
		tileType := chunk.Tiles[localY][localX]
		if tileType == models.TileWall {
			return nil, errors.New("cannot walk through walls")
		}
	}

	// Update player position
	player.X = newPos.X
	player.Y = newPos.Y
	player.Z = newPos.Z

	return &newPos, nil
}

// ProcessCombat handles combat between entities
func (ws *WorldService) ProcessCombat(attackerID string, targetID string, action string) (interface{}, error) {
	ws.worldMutex.Lock()
	defer ws.worldMutex.Unlock()

	attacker, attackerExists := ws.players[attackerID]
	if !attackerExists {
		return nil, errors.New("attacker not found")
	}

	// For now, we'll just simulate a simple combat action
	// In a real implementation, this would involve more complex combat mechanics

	damage := rand.Intn(10) + 1 // Random damage between 1 and 10

	result := map[string]interface{}{
		"type":     "combat_result",
		"attacker": attacker.Username,
		"target":   targetID,
		"action":   action,
		"damage":   damage,
		"result":   "hit",
	}

	return result, nil
}

// GetWorldUpdateForPlayer gets the world state for a specific player
func (ws *WorldService) GetWorldUpdateForPlayer(playerID string) *messages.UpdateMessage {
	ws.worldMutex.RLock()
	defer ws.worldMutex.RUnlock()

	player, exists := ws.players[playerID]
	if !exists {
		return &messages.UpdateMessage{}
	}

	// For now, return a simplified view
	// In a real implementation, this would return only what the player can see

	// Create a list of nearby players
	nearbyPlayers := make([]interface{}, 0)
	for id, p := range ws.players {
		if id != playerID {
			// Check if player is within viewing distance (simplified)
			distX := abs(p.X - player.X)
			distY := abs(p.Y - player.Y)
			if distX <= 10 && distY <= 10 {
				nearbyPlayers = append(nearbyPlayers, map[string]interface{}{
					"id":       p.ID,
					"username": p.Username,
					"x":        p.X,
					"y":        p.Y,
					"icon":     p.Icon,
				})
			}
		}
	}

	// Create a list of nearby monsters
	nearbyMonsters := make([]interface{}, 0)
	for _, m := range ws.monsters {
		// Check if monster is within viewing distance (simplified)
		distX := abs(m.X - player.X)
		distY := abs(m.Y - player.Y)
		if distX <= 10 && distY <= 10 {
			nearbyMonsters = append(nearbyMonsters, map[string]interface{}{
				"id":    m.ID,
				"name":  m.Name,
				"x":     m.X,
				"y":     m.Y,
				"char":  m.Char,
				"hp":    m.HP,
				"maxHp": m.MaxHP,
			})
		}
	}

	// Create a list of nearby items
	nearbyItems := make([]interface{}, 0)
	for _, i := range ws.items {
		// Check if item is within viewing distance (simplified)
		distX := abs(i.X - player.X)
		distY := abs(i.Y - player.Y)
		if distX <= 10 && distY <= 10 {
			nearbyItems = append(nearbyItems, map[string]interface{}{
				"id":   i.ID,
				"name": i.Name,
				"x":    i.X,
				"y":    i.Y,
				"char": i.Char,
			})
		}
	}

	// Get map tiles around player
	viewRadius := 10
	viewDiameter := viewRadius*2 + 1
	tiles := make([][]int, viewDiameter)
	
	for i := 0; i < viewDiameter; i++ {
		tiles[i] = make([]int, viewDiameter)
		for j := 0; j < viewDiameter; j++ {
			worldX := player.X - viewRadius + j
			worldY := player.Y - viewRadius + i
			
			// Get chunk for this position
			chunk := ws.chunkManager.GetChunk(worldX, worldY)
			
			// Calculate local coordinates within chunk
			localX := worldX - chunk.X*ws.chunkManager.chunkSize
			localY := worldY - chunk.Y*ws.chunkManager.chunkSize
			
			// Check bounds (handle negative coordinates correctly if world allows it, 
			// but here we assume chunks handle local indexing correctly or we fix it)
			// Assuming simple positive world for now or simple mod arithmetic:
			if localX < 0 { localX += ws.chunkManager.chunkSize }
			if localY < 0 { localY += ws.chunkManager.chunkSize }
			
			// Safety check for array bounds
			if localX >= 0 && localX < ws.chunkManager.chunkSize && localY >= 0 && localY < ws.chunkManager.chunkSize {
				tiles[i][j] = chunk.Tiles[localY][localX]
			} else {
				tiles[i][j] = models.TileWall // Default to wall if out of bounds
			}
		}
	}

	mapView := map[string]interface{}{
		"center_x": player.X,
		"center_y": player.Y,
		"radius":   viewRadius,
		"tiles":    tiles,
	}

	return &messages.UpdateMessage{
		Players:  nearbyPlayers,
		Monsters: nearbyMonsters,
		Items:    nearbyItems,
		Map:      mapView,
	}
}

// Helper function to calculate absolute value
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}