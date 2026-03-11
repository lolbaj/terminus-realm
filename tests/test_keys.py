"""
Verification tests for the WASD+QEZC movement keys in InputHandler.
"""

import sys
import io
import select
from unittest.mock import MagicMock
from input.handler import InputHandler


def test_wasd_movement():
    """Verify that WASD and diagonal keys map to correct directions."""
    # Mocking select.select BEFORE creating InputHandler
    select.select = MagicMock(return_value=([sys.stdin], [], []))

    handler = InputHandler()

    # Store original stdin to restore it later
    original_stdin = sys.stdin

    keys = ["w", "a", "s", "d", "q", "e", "z", "c"]
    expected = [
        (0, -1),
        (-1, 0),
        (0, 1),
        (1, 0),
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
    ]

    for key, (ex_dx, ex_dy) in zip(keys, expected):
        sys.stdin = io.StringIO(key)
        # Mock select again for the check
        select.select = MagicMock(return_value=([sys.stdin], [], []))

        event = handler.check_for_input()
        if event is None:
            raise ValueError(f"Failed for key {key}: event is None")
        if event.action_type != "move":
            raise ValueError(f"Wrong action for key {key}: got {event.action_type}")
        if event.dx != ex_dx or event.dy != ex_dy:
            raise ValueError(
                f"Wrong direction for key {key}: got ({event.dx}, {event.dy}), expected ({ex_dx}, {ex_dy})"
            )
        print(f"Key {key} works correctly for movement ({ex_dx}, {ex_dy})")

    sys.stdin = original_stdin


if __name__ == "__main__":
    try:
        test_wasd_movement()
        print("\nAll WASD+QEZC movement keys verified successfully!")
    except (ValueError, ImportError) as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
