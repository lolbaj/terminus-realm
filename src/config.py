"""
Configuration settings for the roguelike game.
"""

from pydantic import BaseModel, ConfigDict
from typing import Tuple


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

    model_config = ConfigDict(extra="allow")


# Global config instance
CONFIG = GameConfig()
