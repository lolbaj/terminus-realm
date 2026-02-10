package network

import (
	"encoding/json"
	"log"

	"github.com/gorilla/websocket"
)

// Connection wraps the WebSocket connection with additional fields
type Connection struct {
	ws   *websocket.Conn
	send chan []byte
}

// NewConnection creates a new connection wrapper
func NewConnection(ws *websocket.Conn) *Connection {
	return &Connection{
		ws:   ws,
		send: make(chan []byte, 256), // Buffered channel for outgoing messages
	}
}

// ReadPump reads messages from the WebSocket connection
func (c *Connection) ReadPump(h MessageHandler) {
	defer func() {
		c.ws.Close()
	}()

	for {
		_, message, err := c.ws.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("Error reading message: %v", err)
			}
			break
		}

		// Handle the incoming message
		h.HandleMessage(c, message)
	}
}

// WritePump writes messages to the WebSocket connection
func (c *Connection) WritePump() {
	defer func() {
		c.ws.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			if !ok {
				// Channel closed, exit the loop
				c.ws.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.ws.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			if _, err := w.Write(message); err != nil {
				return
			}

			if err := w.Close(); err != nil {
				return
			}
		}
	}
}

// SendMessage sends a message to the client
func (c *Connection) SendMessage(msg interface{}) error {
	messageBytes, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	select {
	case c.send <- messageBytes:
	default:
		// If the send channel is full, close the connection
		c.ws.Close()
	}
	return nil
}

// MessageHandler interface for handling messages
type MessageHandler interface {
	HandleMessage(conn *Connection, message []byte)
}