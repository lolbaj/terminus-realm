package persistence

import "terminus-realm/server/models"

// Storage defines the interface for data persistence
type Storage interface {
	SavePlayer(player *models.Player) error
	LoadPlayer(playerID string) (*models.Player, error)
	LoadPlayerByUsername(username string) (*models.Player, error)
	SaveWorld(name string, gameMap *models.GameMap) error
	LoadWorld(name string) (*models.GameMap, error)
	Close() error
}
