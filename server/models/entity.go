package models

import "time"

type Player struct {
	ID          string    `json:"id"`
	Username    string    `json:"username"`
	X           int       `json:"x"`
	Y           int       `json:"y"`
	Z           int       `json:"z"` // For multi-level maps
	Icon        string    `json:"icon"`
	Color       []int     `json:"color"` // RGB values
	HP          int       `json:"hp"`
	MaxHP       int       `json:"max_hp"`
	Gold        int       `json:"gold"`
	Level       int       `json:"level"`
	Experience  int       `json:"experience"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type Monster struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	X        int    `json:"x"`
	Y        int    `json:"y"`
	Z        int    `json:"z"`
	Char     string `json:"char"`
	FgColor  []int  `json:"fg_color"` // RGB values
	HP       int    `json:"hp"`
	MaxHP    int    `json:"max_hp"`
	Attack   int    `json:"attack"`
	Defense  int    `json:"defense"`
	AIType   string `json:"ai_type"`
	XPReward int    `json:"xp_reward"`
}

type Item struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Type        string `json:"type"`
	Char        string `json:"char"`
	Color       []int  `json:"color"` // RGB values
	Description string `json:"description"`
	X           int    `json:"x"`
	Y           int    `json:"y"`
	Z           int    `json:"z"` // For multi-level maps
}

type Position struct {
	X int `json:"x"`
	Y int `json:"y"`
	Z int `json:"z"`
}