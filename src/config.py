"""
Configuration settings for the roguelike game.
"""

from pydantic import BaseModel, ConfigDict
from typing import Tuple, Dict, Any
import toml
import os


class GameConfig(BaseModel):
    """Configuration settings for the game."""

    # Game Metadata
    game_title: str = "Terminus Realm"
    version: str = "0.1.0"

    # Display settings
    screen_width: int = 80
    screen_height: int = 25
    tile_size: Tuple[int, int] = (1, 1)  # Width, Height in terminal chars

    # World settings
    chunk_size: int = 50  # Size of each world chunk
    max_chunks_loaded: int = 9  # 3x3 grid of chunks
    world_width: int = 2000
    world_height: int = 2000

    # Performance settings
    target_fps: int = 30
    max_frameskip: int = 5
    ai_move_delay: float = 0.5  # Seconds between AI moves

    # Game settings
    player_start_x: int = 25
    player_start_y: int = 25
    max_player_hp: int = 100

    # Pathfinding
    max_path_length: int = 100  # Maximum path length to calculate

    # Paths
    paths: Dict[str, str] = {}

    # Controls
    controls: Dict[str, Any] = {}

    model_config = ConfigDict(extra="allow")

    @classmethod
    def load_from_toml(cls, path: str = "config.toml") -> "GameConfig":
        """Load configuration from a TOML file."""
        if not os.path.exists(path):
            print(f"Warning: Config file {path} not found. Using defaults.")
            return cls()

        try:
            with open(path, "r") as f:
                data = toml.load(f)

            # Flatten game settings for Pydantic
            game_settings = data.get("game", {})

            # Create instance with game settings
            config = cls(**game_settings)

            # Attach complex structures
            config.paths = data.get("paths", {})
            config.controls = data.get("controls", {})

            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return cls()


# Global config instance
CONFIG = GameConfig.load_from_toml()
