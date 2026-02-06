"""
Input handling system for the roguelike game.
Supports VI-style movement keys and other controls.
"""

from typing import Optional
from dataclasses import dataclass
import sys
import select
import tty
import termios
import io


@dataclass
class InputEvent:
    """Represents an input event."""

    action_type: str
    dx: int = 0
    dy: int = 0


class InputHandler:
    """Handles keyboard input for the game."""

    def __init__(self):
        # Movement keys: WASD, WASF, and diagonals
        self.movement_keys = {
            # WASD
            "w": (0, -1),  # Up
            "a": (-1, 0),  # Left
            "s": (0, 1),  # Down
            "d": (1, 0),  # Right
            # WASF support (user requested)
            "f": (1, 0),  # Right (if using WASF)
            # Diagonals (using keys around WASD)
            "q": (-1, -1),  # Up-left
            "e": (
                1,
                -1,
            ),  # Up-right (Note: 'e' is also used for select below, but we'll prioritize movement if it's here)
            "z": (-1, 1),  # Down-left
            "c": (1, 1),  # Down-right
        }

        # Action keys
        self.action_keys = {
            " ": "action_menu",  # Space for action menu
            "e": "select",  # 'e' for selection (common interact key)
            "x": "select",  # 'x' for selection
            "p": "quit",  # 'p' to quit (instead of 'q' which is now move)
            "i": "inventory",  # Inventory
            "I": "inventory",
            "g": "pickup",  # Get/Pickup
            "t": "fire",  # Target/Fire ranged weapon
        }

        # Store original terminal settings
        self.original_settings = None

    def setup_terminal(self):
        """Setup terminal for non-blocking input."""
        try:
            self.original_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
        except (termios.error, io.UnsupportedOperation):
            # Handle cases where stdin is not a TTY (e.g., when running tests)
            self.original_settings = None

    def restore_terminal(self):
        """Restore terminal to original settings."""
        if self.original_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
            except termios.error:
                # Handle cases where stdin is not a TTY
                pass

    def check_for_input(self) -> Optional[InputEvent]:
        """
        Check for input without blocking.
        Returns an InputEvent if available, otherwise None.
        """
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            key = sys.stdin.read(1)

            # Handle Escape Sequences (Arrow Keys)
            if key == "\x1b":
                # Check if there's more data (non-blocking read for sequence)
                if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                    next1 = sys.stdin.read(1)
                    if next1 == "[":
                        if select.select([sys.stdin], [], [], 0.01) == (
                            [sys.stdin],
                            [],
                            [],
                        ):
                            next2 = sys.stdin.read(1)
                            if next2 == "A":
                                return InputEvent("move", 0, -1)  # Up
                            elif next2 == "B":
                                return InputEvent("move", 0, 1)  # Down
                            elif next2 == "C":
                                return InputEvent("move", 1, 0)  # Right
                            elif next2 == "D":
                                return InputEvent("move", -1, 0)  # Left
                return None

            # Handle movement keys
            if key in self.movement_keys:
                dx, dy = self.movement_keys[key]
                return InputEvent("move", dx, dy)

            # Handle action keys
            if key in self.action_keys:
                action = self.action_keys[key]
                if action == "quit":
                    return InputEvent("quit")
                elif action == "action_menu":
                    return InputEvent("action_menu")
                elif action == "select":
                    return InputEvent("select")
                elif action == "inventory":
                    return InputEvent("inventory")
                elif action == "pickup":
                    return InputEvent("pickup")

            return None

        return None

    def wait_for_input(self) -> Optional[InputEvent]:
        """
        Wait for and return the next input event.
        This is a blocking call.
        """
        # Read a single character
        key = sys.stdin.read(1)

        # Handle movement keys
        if key in self.movement_keys:
            dx, dy = self.movement_keys[key]
            return InputEvent("move", dx, dy)

        # Handle action keys
        if key in self.action_keys:
            action = self.action_keys[key]
            if action == "quit":
                return InputEvent("quit")
            elif action == "action_menu":
                return InputEvent("action_menu")
            elif action == "select":
                return InputEvent("select")

        # Return None for unrecognized keys
        return None


class InputBuffer:
    """Buffer for storing and processing input events."""

    def __init__(self):
        self.buffer = []

    def add_input(self, event: InputEvent):
        """Add an input event to the buffer."""
        self.buffer.append(event)

    def get_next_event(self) -> Optional[InputEvent]:
        """Get the next event from the buffer."""
        if self.buffer:
            return self.buffer.pop(0)
        return None

    def clear(self):
        """Clear the input buffer."""
        self.buffer.clear()

    def has_events(self) -> bool:
        """Check if there are events in the buffer."""
        return len(self.buffer) > 0
