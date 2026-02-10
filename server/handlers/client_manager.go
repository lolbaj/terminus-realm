package handlers

import (
	"log"
	"sync"
)

// ClientManager manages connected clients
type ClientManager struct {
	clients map[string]*ClientHandler // Map PlayerID to ClientHandler
	mutex   sync.RWMutex
}

// NewClientManager creates a new client manager
func NewClientManager() *ClientManager {
	return &ClientManager{
		clients: make(map[string]*ClientHandler),
	}
}

// AddClient adds a client to the manager
func (cm *ClientManager) AddClient(playerID string, handler *ClientHandler) {
	cm.mutex.Lock()
	defer cm.mutex.Unlock()
	cm.clients[playerID] = handler
}

// RemoveClient removes a client from the manager
func (cm *ClientManager) RemoveClient(playerID string) {
	cm.mutex.Lock()
	defer cm.mutex.Unlock()
	delete(cm.clients, playerID)
}

// BroadcastToAll sends a message to all connected clients
func (cm *ClientManager) BroadcastToAll(msg interface{}) {
	cm.mutex.RLock()
	defer cm.mutex.RUnlock()

	for id, client := range cm.clients {
		if err := client.conn.SendMessage(msg); err != nil {
			log.Printf("Error broadcasting to client %s: %v", id, err)
		}
	}
}

// BroadcastToOthers sends a message to all connected clients except the specified one
func (cm *ClientManager) BroadcastToOthers(excludePlayerID string, msg interface{}) {
	cm.mutex.RLock()
	defer cm.mutex.RUnlock()

	for id, client := range cm.clients {
		if id == excludePlayerID {
			continue
		}
		if err := client.conn.SendMessage(msg); err != nil {
			log.Printf("Error broadcasting to client %s: %v", id, err)
		}
	}
}

// ExecuteOnAllClients executes a function for each connected client
func (cm *ClientManager) ExecuteOnAllClients(action func(*ClientHandler)) {
	cm.mutex.RLock()
	defer cm.mutex.RUnlock()

	for _, client := range cm.clients {
		action(client)
	}
}
