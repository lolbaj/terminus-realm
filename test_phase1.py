"""
Test script to verify Phase 1 functionality.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from core.engine import GameEngine


def test_phase1():
    """Test Phase 1 functionality."""
    print("Testing Phase 1: Basic World and Player Movement")

    # Create a game engine instance
    engine = GameEngine()

    # Initialize the game
    engine.initialize_game()

    # Verify that the game has a map and player
    assert engine.game_map is not None, "Game map should be created"
    assert engine.player_id is not None, "Player should be created"

    print(
        f"✓ Game map created with dimensions {engine.game_map.width}x{engine.game_map.height}"
    )
    print(f"✓ Player created with ID {engine.player_id}")

    # Get initial player position
    from entities.components import Position

    initial_pos = engine.entity_manager.get_component(engine.player_id, Position)
    print(f"✓ Player initial position: ({initial_pos.x}, {initial_pos.y})")

    # Test player movement
    initial_x, initial_y = initial_pos.x, initial_pos.y

    # Move player right
    engine.move_player(1, 0)
    pos_after_move = engine.entity_manager.get_component(engine.player_id, Position)

    assert (
        pos_after_move.x == initial_x + 1
    ), f"Player should have moved right from {initial_x} to {initial_x + 1}"
    assert pos_after_move.y == initial_y, f"Player Y position should remain {initial_y}"

    print(
        f"✓ Player moved right successfully: ({initial_x}, {initial_y}) -> ({pos_after_move.x}, {pos_after_move.y})"
    )

    # Test movement validation (try to move into a wall)

    # Find a wall position to try to move into
    wall_x, wall_y = None, None
    for y in range(engine.game_map.height):
        for x in range(engine.game_map.width):
            if not engine.game_map.is_walkable(x, y):
                wall_x, wall_y = x, y
                break
        if wall_x is not None:
            break

    if wall_x is not None and wall_y is not None:
        # Temporarily move player near the wall
        pos_after_move.x = wall_x - 1
        pos_after_move.y = wall_y

        # Try to move into the wall
        engine.move_player(1, 0)  # Try to move right into the wall
        pos_after_wall_attempt = engine.entity_manager.get_component(
            engine.player_id, Position
        )

        # Position should not have changed since the target is not walkable
        assert (
            pos_after_wall_attempt.x == wall_x - 1
        ), "Player should not move into a wall"
        assert pos_after_wall_attempt.y == wall_y, "Player should not move into a wall"

        print(
            f"✓ Player correctly prevented from moving into wall at ({wall_x}, {wall_y})"
        )

    print("\n✓ All Phase 1 tests passed!")
    print(
        "Basic world generation, player creation, and movement are working correctly."
    )


if __name__ == "__main__":
    test_phase1()
