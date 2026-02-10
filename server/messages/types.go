package messages

// MessageType defines the type of message being sent
type MessageType string

const (
	MessageTypeLogin       MessageType = "login"
	MessageTypeLoginSuccess MessageType = "login_success"
	MessageTypeMove        MessageType = "move"
	MessageTypeChat        MessageType = "chat"
	MessageTypeUpdate      MessageType = "update"
	MessageTypeCombat      MessageType = "combat"
	MessageTypeItemUse     MessageType = "item_use"
	MessageTypeError       MessageType = "error"
)

// BaseMessage is the base structure for all messages
type BaseMessage struct {
	Type    MessageType   `json:"type"`
	Payload interface{}   `json:"payload"`
}

// LoginMessage represents a login request
type LoginMessage struct {
	Username string `json:"username"`
	Password string `json:"password"` // In a real app, use secure authentication
}

// LoginSuccessMessage represents a successful login response
type LoginSuccessMessage struct {
	PlayerID string `json:"player_id"`
	Message  string `json:"message"`
}

// MoveMessage represents a player movement request
type MoveMessage struct {
	Direction string `json:"direction"` // north, south, east, west, northeast, northwest, southeast, southwest
}

// ChatMessage represents a chat message
type ChatMessage struct {
	Sender    string `json:"sender"`
	Message   string `json:"message"`
	Timestamp int64  `json:"timestamp"`
}

// UpdateMessage represents a world update
type UpdateMessage struct {
	Players  []interface{} `json:"players"`  // Simplified for now
	Monsters []interface{} `json:"monsters"` // Simplified for now
	Items    []interface{} `json:"items"`    // Simplified for now
	Map      interface{}   `json:"map"`      // Simplified for now
}

// CombatMessage represents a combat action
type CombatMessage struct {
	TargetID string `json:"target_id"`
	Action   string `json:"action"` // attack, spell, etc.
}

// ErrorMessage represents an error response
type ErrorMessage struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

// ItemUseMessage represents using an item
type ItemUseMessage struct {
	ItemID string `json:"item_id"`
	Target string `json:"target"` // player ID or self
}