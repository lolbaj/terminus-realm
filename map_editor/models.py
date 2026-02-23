"""
Core models and data structures for the Map Editor.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


@dataclass
class TileDef:
    char: str
    name: str
    walkable: bool = True
    transparent: bool = True
    fg_color: Tuple[int, int, int] = (255, 255, 255)
    bg_color: Optional[Tuple[int, int, int]] = None


class EditorMode(Enum):
    DRAW = "DRAW"
    SELECT = "SELECT"
    RECT = "RECT"
    BROWSE = "BROWSE"
    PASTE = "PASTE"
    ERASE = "ERASE"


@dataclass
class Selection:
    x: int
    y: int
    width: int
    height: int
    bg_data: List[List[str]] = field(default_factory=list)
    fg_data: List[List[str]] = field(default_factory=list)

    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0 and (self.bg_data or self.fg_data)


@dataclass
class UndoAction:
    x: int
    y: int
    old_char: str
    new_char: str
    layer: str = "bg"
