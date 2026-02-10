package handlers

import (
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/gorilla/websocket"

	"terminus-realm/server/messages"
	"terminus-realm/server/models"
	"terminus-realm/server/network"
	"terminus-realm/server/services"
)

// ClientHandler manages a single client connection
type ClientHandler struct {
	conn          *network.Connection
	playerService *services.PlayerService
	worldService  *services.WorldService
	clientManager *ClientManager
	player        *models.Player
}

// HandleClientConnection handles a new client connection
func HandleClientConnection(wsConn *websocket.Conn, playerService *services.PlayerService, worldService *services.WorldService, clientManager *ClientManager) {
	// Log connection
	f, _ := os.OpenFile("server_debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(fmt.Sprintf("New connection from %s\n", wsConn.RemoteAddr().String()))
		f.Close()
	}

	conn := network.NewConnection(wsConn)
	handler := &ClientHandler{
		conn:          conn,
		playerService: playerService,
		worldService:  worldService,
		clientManager: clientManager,
	}

	// Start the write pump in a goroutine
	go conn.WritePump()

	// Handle the read pump in the current goroutine
	conn.ReadPump(handler)

	// Clean up when the connection is closed
	if handler.player != nil {
		worldService.RemovePlayer(handler.player.ID)
		clientManager.RemoveClient(handler.player.ID)
		log.Printf("Player %s disconnected and removed from world", handler.player.Username)
		
		// Notify others
		handler.broadcastPlayerUpdate()
	}
}

// HandleMessage handles incoming messages from the client
func (h *ClientHandler) HandleMessage(conn *network.Connection, message []byte) {
	// Log raw message
	f, _ := os.OpenFile("server_debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString(fmt.Sprintf("Received: %s\n", string(message)))
		f.Close()
	}

	var baseMsg messages.BaseMessage
	if err := json.Unmarshal(message, &baseMsg); err != nil {
		log.Printf("Error unmarshaling message: %v", err)
		return
	}

	switch baseMsg.Type {
	case messages.MessageTypeLogin:
		h.handleLogin(baseMsg.Payload)
	case messages.MessageTypeMove:
		h.handleMove(baseMsg.Payload)
	case messages.MessageTypeChat:
		h.handleChat(baseMsg.Payload)
	case messages.MessageTypeCombat:
		h.handleCombat(baseMsg.Payload)
	case messages.MessageTypeItemUse:
		h.handleItemUse(baseMsg.Payload)
	default:
		log.Printf("Unknown message type: %s", baseMsg.Type)
		errMsg := messages.BaseMessage{
			Type: messages.MessageTypeError,
			Payload: messages.ErrorMessage{
				Code:    "UNKNOWN_MESSAGE_TYPE",
				Message: "Unknown message type received",
			},
		}
		h.conn.SendMessage(errMsg)
	}
}

// handleLogin handles login requests
func (h *ClientHandler) handleLogin(payload interface{}) {
	f, _ := os.OpenFile("server_debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		f.WriteString("Starting handleLogin\n")
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling login payload: %v", err)
		return
	}

	var loginMsg messages.LoginMessage
	if err := json.Unmarshal(data, &loginMsg); err != nil {
		log.Printf("Error unmarshaling login message: %v", err)
		return
	}

	if f != nil {
		f.WriteString(fmt.Sprintf("Logging in user: %s\n", loginMsg.Username))
	}

	// Authenticate and create/get player
	player, err := h.playerService.GetOrCreatePlayer(loginMsg.Username)
	if err != nil {
		if f != nil {
			f.WriteString(fmt.Sprintf("Error getting player: %v\n", err))
		}
		log.Printf("Error getting/creating player: %v", err)
		errMsg := messages.BaseMessage{
			Type: messages.MessageTypeError,
			Payload: messages.ErrorMessage{
				Code:    "LOGIN_FAILED",
				Message: "Failed to log in",
			},
		}
		h.conn.SendMessage(errMsg)
		if f != nil { f.Close() }
		return
	}

	h.player = player
	
	// Register with ClientManager
	h.clientManager.AddClient(player.ID, h)

	if f != nil {
		f.WriteString(fmt.Sprintf("Player loaded: %s. Sending login success...\n", player.ID))
	}

	// Send login success message
	loginSuccessMsg := messages.BaseMessage{
		Type: messages.MessageTypeLoginSuccess,
		Payload: messages.LoginSuccessMessage{
			PlayerID: player.ID,
			Message:  "Login successful",
		},
	}
	
	if err := h.conn.SendMessage(loginSuccessMsg); err != nil {
		if f != nil {
			f.WriteString(fmt.Sprintf("Error sending login success: %v\n", err))
		}
		log.Printf("Error sending login success: %v", err)
		if f != nil { f.Close() }
		return
	}

	if f != nil {
		f.WriteString("Login success sent. Sending world update...\n")
	}

	// Send initial world state
	h.sendWorldUpdate()
	
	// Notify others of new player
	h.broadcastPlayerUpdate()
	
	if f != nil {
		f.WriteString("World update sent.\n")
		f.Close()
	}
}

// handleMove handles player movement requests
func (h *ClientHandler) handleMove(payload interface{}) {
	if h.player == nil {
		log.Println("Player not authenticated")
		return
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling move payload: %v", err)
		return
	}

	var moveMsg messages.MoveMessage
	if err := json.Unmarshal(data, &moveMsg); err != nil {
		log.Printf("Error unmarshaling move message: %v", err)
		return
	}

	// Process the move
	newPos, err := h.worldService.MovePlayer(h.player.ID, moveMsg.Direction)
	if err != nil {
		log.Printf("Error moving player: %v", err)
		errMsg := messages.BaseMessage{
			Type: messages.MessageTypeError,
			Payload: messages.ErrorMessage{
				Code:    "MOVE_FAILED",
				Message: err.Error(),
			},
		}
		h.conn.SendMessage(errMsg)
		return
	}

	// Update player position
	h.player.X = newPos.X
	h.player.Y = newPos.Y
	h.player.Z = newPos.Z

	// Broadcast the move to other players
	h.broadcastPlayerUpdate()

	// Send updated world state to self
	h.sendWorldUpdate()
}

// handleChat handles chat messages
func (h *ClientHandler) handleChat(payload interface{}) {
	if h.player == nil {
		log.Println("Player not authenticated")
		return
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling chat payload: %v", err)
		return
	}

	var chatMsg messages.ChatMessage
	if err := json.Unmarshal(data, &chatMsg); err != nil {
		log.Printf("Error unmarshaling chat message: %v", err)
		return
	}

	// Set sender to current player
	chatMsg.Sender = h.player.Username

	// Broadcast the chat message to other players
	h.broadcastChatMessage(chatMsg)
}

// handleCombat handles combat actions
func (h *ClientHandler) handleCombat(payload interface{}) {
	if h.player == nil {
		log.Println("Player not authenticated")
		return
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling combat payload: %v", err)
		return
	}

	var combatMsg messages.CombatMessage
	if err := json.Unmarshal(data, &combatMsg); err != nil {
		log.Printf("Error unmarshaling combat message: %v", err)
		return
	}

	// Process the combat action
	result, err := h.worldService.ProcessCombat(h.player.ID, combatMsg.TargetID, combatMsg.Action)
	if err != nil {
		log.Printf("Error processing combat: %v", err)
		errMsg := messages.BaseMessage{
			Type: messages.MessageTypeError,
			Payload: messages.ErrorMessage{
				Code:    "COMBAT_FAILED",
				Message: err.Error(),
			},
		}
		h.conn.SendMessage(errMsg)
		return
	}

	// Send combat result to the player
	h.conn.SendMessage(result)
}

// handleItemUse handles using items
func (h *ClientHandler) handleItemUse(payload interface{}) {
	if h.player == nil {
		log.Println("Player not authenticated")
		return
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling item use payload: %v", err)
		return
	}

	var itemUseMsg messages.ItemUseMessage
	if err := json.Unmarshal(data, &itemUseMsg); err != nil {
		log.Printf("Error unmarshaling item use message: %v", err)
		return
	}

	// Process the item use
	result, err := h.playerService.UseItem(h.player.ID, itemUseMsg.ItemID, itemUseMsg.Target)
	if err != nil {
		log.Printf("Error using item: %v", err)
		errMsg := messages.BaseMessage{
			Type: messages.MessageTypeError,
			Payload: messages.ErrorMessage{
				Code:    "ITEM_USE_FAILED",
				Message: err.Error(),
			},
		}
		h.conn.SendMessage(errMsg)
		return
	}

	// Send result to the player
	h.conn.SendMessage(result)
}

// sendWorldUpdate sends the current world state to the player
func (h *ClientHandler) sendWorldUpdate() {
	if h.player == nil {
		return
	}

	worldUpdate := h.worldService.GetWorldUpdateForPlayer(h.player.ID)
	updateMsg := messages.UpdateMessage{
		Players:  worldUpdate.Players,
		Monsters: worldUpdate.Monsters,
		Items:    worldUpdate.Items,
		Map:      worldUpdate.Map,
	}

	msg := messages.BaseMessage{
		Type:    messages.MessageTypeUpdate,
		Payload: updateMsg,
	}

	if err := h.conn.SendMessage(msg); err != nil {
		log.Printf("Error sending world update: %v", err)
	}
}

// broadcastPlayerUpdate broadcasts the player's position to other players
func (h *ClientHandler) broadcastPlayerUpdate() {
	// Trigger a world update for everyone so they see the change
	// In a real app we'd optimize this to only update relevant players
	h.clientManager.ExecuteOnAllClients(func(client *ClientHandler) {
		client.sendWorldUpdate()
	})
}

// broadcastChatMessage broadcasts a chat message to all connected players
func (h *ClientHandler) broadcastChatMessage(chatMsg messages.ChatMessage) {
	msg := messages.BaseMessage{
		Type:    messages.MessageTypeChat,
		Payload: chatMsg,
	}
	h.clientManager.BroadcastToAll(msg)
}