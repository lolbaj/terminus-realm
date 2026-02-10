package services

import (
	"fmt"
	"sync"

	"terminus-realm/server/models"
)

// Chunk represents a section of the game world
type Chunk struct {
	X      int               `json:"x"`
	Y      int               `json:"y"`
	Tiles  [][]int           `json:"tiles"`
	Entities []models.Entity `json:"entities"`
	mutex  sync.RWMutex
}

// ChunkManager manages world chunks
type ChunkManager struct {
	chunkSize    int
	bufferRadius int
	chunks       map[string]*Chunk
	worldMutex   sync.RWMutex
}

// NewChunkManager creates a new chunk manager
func NewChunkManager(chunkSize int, bufferRadius int) *ChunkManager {
	return &ChunkManager{
		chunkSize:    chunkSize,
		bufferRadius: bufferRadius,
		chunks:       make(map[string]*Chunk),
	}
}

// getChunkCoordinates calculates the chunk coordinates for a given position
func (cm *ChunkManager) getChunkCoordinates(x, y int) (int, int) {
	cx := x / cm.chunkSize
	if x < 0 && x%cm.chunkSize != 0 {
		cx--
	}
	cy := y / cm.chunkSize
	if y < 0 && y%cm.chunkSize != 0 {
		cy--
	}
	return cx, cy
}

// getChunkKey generates a unique key for a chunk
func (cm *ChunkManager) getChunkKey(chunkX, chunkY int) string {
	return fmt.Sprintf("%d,%d", chunkX, chunkY)
}

// GetChunk retrieves a chunk by coordinates
func (cm *ChunkManager) GetChunk(x, y int) *Chunk {
	chunkX, chunkY := cm.getChunkCoordinates(x, y)
	key := cm.getChunkKey(chunkX, chunkY)

	cm.worldMutex.RLock()
	chunk, exists := cm.chunks[key]
	cm.worldMutex.RUnlock()

	if !exists {
		// Create a new chunk if it doesn't exist
		chunk = cm.createChunk(chunkX, chunkY)
	}

	return chunk
}

// createChunk creates a new chunk with the given coordinates
func (cm *ChunkManager) createChunk(x, y int) *Chunk {
	cm.worldMutex.Lock()
	defer cm.worldMutex.Unlock()

	key := cm.getChunkKey(x, y)
	
	// Check again if chunk was created by another goroutine
	if chunk, exists := cm.chunks[key]; exists {
		return chunk
	}

	// Create a new chunk with default tiles
	tiles := make([][]int, cm.chunkSize)
	for i := range tiles {
		tiles[i] = make([]int, cm.chunkSize)
		// Fill with grass tiles by default
		for j := range tiles[i] {
			tiles[i][j] = models.TileGrass
		}
	}

	chunk := &Chunk{
		X:      x,
		Y:      y,
		Tiles:  tiles,
		Entities: make([]models.Entity, 0),
	}

	cm.chunks[key] = chunk
	return chunk
}

// LoadChunksAround loads chunks around a given position
func (cm *ChunkManager) LoadChunksAround(centerX, centerY int) []*Chunk {
	centerChunkX, centerChunkY := cm.getChunkCoordinates(centerX, centerY)
	
	var chunks []*Chunk
	
	// Load chunks in a square around the center chunk
	for dx := -cm.bufferRadius; dx <= cm.bufferRadius; dx++ {
		for dy := -cm.bufferRadius; dy <= cm.bufferRadius; dy++ {
			chunkX := centerChunkX + dx
			chunkY := centerChunkY + dy
			chunk := cm.GetChunk(chunkX*cm.chunkSize, chunkY*cm.chunkSize)
			chunks = append(chunks, chunk)
		}
	}
	
	return chunks
}