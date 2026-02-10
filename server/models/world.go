package models

// GameMap represents the game world map
type GameMap struct {
	Width   int       `json:"width"`
	Height  int       `json:"height"`
	Depth   int       `json:"depth"` // For multi-level maps
	Tiles   [][]int   `json:"tiles"` // 2D array of tile types
	Entities []Entity `json:"entities"` // Entities on the map
}

// Tile types represented as integers for memory efficiency
const (
	TileFloor = iota
	TileWall
	TileDoor
	TileWater
	TileGrass
	TileTree
	TileStairsUp
	TileStairsDown
	TileSand
	TilePavement
	TileSnow
	TileLava
	TileAsh
	TileCactus
	TileIce
)

// Entity interface for anything that can exist on the map
type Entity interface {
	GetPosition() Position
	GetID() string
}