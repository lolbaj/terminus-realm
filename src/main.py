"""
Main entry point for the roguelike game.
"""

import sys
import os

# Add the directory containing this file (src) to the Python path
# This allows imports like 'from core.engine import ...' to work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import GameEngine


def main():
    """Entry point for the game."""
    print("Starting the Roguelike Game...")

    # Initialize the game engine
    engine = GameEngine()

    # Start the main game loop
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
        sys.exit(0)
    except Exception as e:
        import traceback

        with open("game_debug.log", "w") as f:
            f.write(f"CRASH REPORT:\n{str(e)}\n\n{traceback.format_exc()}")
        print(f"An error occurred: {e}")
        print("See game_debug.log for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
