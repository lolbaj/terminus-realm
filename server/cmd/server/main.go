package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/websocket"

	"terminus-realm/server/handlers"
	"terminus-realm/server/persistence"
	"terminus-realm/server/services"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		// Allow connections from any origin during development
		// In production, restrict this to your client's domain
		return true
	},
}

func main() {
	// Initialize database
	dbType := os.Getenv("DB_TYPE")
	var db persistence.Storage
	var err error

	if dbType == "postgres" {
		dbConnectionString := os.Getenv("DATABASE_URL")
		if dbConnectionString == "" {
			dbConnectionString = "host=localhost user=terminus password=terminus dbname=terminus_realm sslmode=disable"
		}
		db, err = persistence.NewPostgresStore(dbConnectionString)
		log.Println("Using PostgreSQL persistence")
	} else {
		// Default to JSON store
		dbFile := os.Getenv("DB_FILE")
		if dbFile == "" {
			dbFile = "db.json"
		}
		db, err = persistence.NewJSONStore(dbFile)
		log.Println("Using JSON persistence")
	}

	if err != nil {
		log.Fatalf("Failed to initialize persistence: %v", err)
	}
	defer db.Close()
	
	log.Println("Persistence initialized successfully")

	// Initialize services
	worldService := services.NewWorldService(db)
	playerService := services.NewPlayerService(worldService, db)
	clientManager := handlers.NewClientManager()

	// Set up HTTP routes
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("Failed to upgrade connection: %v", err)
			return
		}
		defer conn.Close()

		// Handle client connection
		handlers.HandleClientConnection(conn, playerService, worldService, clientManager)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}