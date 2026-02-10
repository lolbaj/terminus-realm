"""
Input handling system for the roguelike game.
Supports VI-style movement keys and other controls.
"""

from typing import Optional
from dataclasses import dataclass
import sys
import select
import termios
import time


from config import CONFIG


@dataclass
class InputEvent:
    """Represents an input event."""

    key: str
    action_type: str = ""
    dx: int = 0
    dy: int = 0
    timestamp: float = 0.0


class InputHandler:
    """Handles keyboard input for the game."""

    def __init__(self):
        if sys.stdin.isatty():
            self.stdin_fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.stdin_fd)
            self.is_tty = True
            self.setup_terminal()
        else:
            self.stdin_fd = None
            self.old_settings = None
            self.is_tty = False

        # Load controls
        self.movement_map = CONFIG.controls.get("movement", {})
        self.action_map = CONFIG.controls.get("actions", {})

    def setup_terminal(self):
        """Setup terminal for raw input."""
        if not self.is_tty:
            return
        new_settings = termios.tcgetattr(self.stdin_fd)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, new_settings)

    def restore_terminal(self):
        """Restore terminal to original settings."""
        if not self.is_tty:
            return
        termios.tcsetattr(self.stdin_fd, termios.TCSADRAIN, self.old_settings)

    def _map_key_to_event(self, key: str) -> Optional[InputEvent]:
        """Map a raw key to an InputEvent."""
        if not key:
            return None

        # Check movement
        if key in self.movement_map:
            dx, dy = self.movement_map[key]
            return InputEvent(
                key=key, action_type="move", dx=dx, dy=dy, timestamp=time.time()
            )

        # Check actions
        if key in self.action_map:
            action = self.action_map[key]
            return InputEvent(key=key, action_type=action, timestamp=time.time())

        return InputEvent(key=key, action_type="unknown", timestamp=time.time())

    def get_input_non_blocking(self) -> Optional[InputEvent]:
        """Get input without blocking execution."""
        if not self.is_tty:
            return None

        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            key = sys.stdin.read(1)
            return self._map_key_to_event(key)
        return None

    def check_for_input(self) -> Optional[InputEvent]:
        """Alias for get_input_non_blocking to match GameEngine usage."""
        return self.get_input_non_blocking()

    def get_input_blocking(self) -> InputEvent:
        """Get input blocking until a key is pressed."""
        if not self.is_tty:
            # Avoid hanging forever in tests
            time.sleep(0.1)
            return InputEvent(key="", timestamp=time.time())

        key = sys.stdin.read(1)
        return self._map_key_to_event(key) or InputEvent(key="", timestamp=time.time())

    def __del__(self):
        """Cleanup when the handler is destroyed."""
        self.restore_terminal()
