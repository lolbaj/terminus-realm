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
        from config import CONFIG

        # Load controls from config or use defaults
        if CONFIG.controls and "movement" in CONFIG.controls:
            # Convert list coords to tuples for internal logic
            self.movement_keys = {
                k: tuple(v) for k, v in CONFIG.controls["movement"].items()
            }
        else:
            # Default Movement keys: WASD, Vi-keys, and Numpad
            self.movement_keys = {
                # WASD + Diagonals
                "w": (0, -1),
                "a": (-1, 0),
                "s": (0, 1),
                "d": (1, 0),
                "q": (-1, -1),
                "e": (1, -1),
                "z": (-1, 1),
                "c": (1, 1),
                # Vi-keys
                "h": (-1, 0),
                "j": (0, 1),
                "k": (0, -1),
                "l": (1, 0),
                "y": (-1, -1),
                "u": (1, -1),
                "b": (-1, 1),
                "n": (1, 1),
                # Numpad
                "8": (0, -1),
                "2": (0, 1),
                "4": (-1, 0),
                "6": (1, 0),
                "7": (-1, -1),
                "9": (1, -1),
                "1": (-1, 1),
                "3": (1, 1),
            }

        if CONFIG.controls and "actions" in CONFIG.controls:
            self.action_keys = CONFIG.controls["actions"]
        else:
            # Default Action keys
            self.action_keys = {
                " ": "action_menu",
                "o": "action_menu",  # 'o' for open/interact
                "\r": "select",  # Enter
                "\n": "select",  # Enter (sometimes)
                "x": "select",
                "p": "quit",
                "Q": "quit",
                "i": "inventory",
                "I": "inventory",
                "g": "pickup",
                ",": "pickup",
                "f": "fire",  # 'f' for fire/target
                "t": "fire",
                "C": "stats",  # Shift-C for stats to avoid 'c' diagonal
                "K": "stats",  # Shift-K
                "k": "stats",  # Also allow 'k' (Vi-Up will take precedence if checked first, but let's see)
                "5": "wait",  # Numpad 5
                ".": "wait",
                "?": "help",  # Help Menu
                "1": "cast_1",
                "2": "cast_2",
                "3": "cast_3",
            }

        # Store original terminal settings
        self.original_settings = None

    def setup_terminal(self):
        """Setup terminal for non-blocking input."""
        try:
            self.original_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
            # Hide cursor
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
        except (termios.error, io.UnsupportedOperation):
            # Handle cases where stdin is not a TTY (e.g., when running tests)
            self.original_settings = None

    def restore_terminal(self):
        """Restore terminal to original settings."""
        if self.original_settings:
            try:
                # Show cursor
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()
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
                # Single Esc key - return quit
                return InputEvent("quit")

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
                elif action == "fire":
                    return InputEvent("fire")
                elif action == "stats":
                    return InputEvent("stats")
                elif action == "wait":
                    return InputEvent("wait")
                elif action == "help":
                    return InputEvent("help")
                elif action.startswith("cast_"):
                    return InputEvent(action)

            return None

        return None

    def wait_for_input(self) -> Optional[InputEvent]:
        """
        Wait for and return the next input event.
        This is a blocking call.
        """
        # Read a single character
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
            return InputEvent("quit")

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
            elif action == "fire":
                return InputEvent("fire")
            elif action == "stats":
                return InputEvent("stats")
            elif action == "wait":
                return InputEvent("wait")
            elif action == "help":
                return InputEvent("help")
            elif action.startswith("cast_"):
                return InputEvent(action)

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
