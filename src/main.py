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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--map", help="Path to map file to load (overrides default)")
    parser.add_argument("--pos", help="Starting position x,y")
    args = parser.parse_args()

    engine = GameEngine()
    if args.map:
        engine.override_map_path = args.map
    if args.pos:
        try:
            x, y = map(int, args.pos.split(","))
            engine.override_start_pos = (x, y)
        except ValueError:
            print("Invalid position format. Use x,y")

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
