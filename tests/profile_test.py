#!/usr/bin/env python
"""
Performance profiling script for Terminus Realm.

Uses cProfile to analyze performance bottlenecks in the game engine.
Run with: python tests/profile_test.py

Output shows:
- Total execution time for startup + update cycles
- Top 50 functions by cumulative time
- Function call counts and timing breakdown
"""

import sys
import os
import cProfile
import pstats

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.engine import GameEngine


def run_simulation(num_updates: int = 100) -> GameEngine:
    """
    Run the game simulation for a specified number of update cycles.

    Args:
        num_updates: Number of update cycles to run

    Returns:
        The game engine instance (for inspection if needed)
    """
    engine = GameEngine()
    engine.initialize_game()

    # Run update cycles (simulating ~3.3 seconds at 30 FPS)
    for _ in range(num_updates):
        engine.update(0.033)

    return engine


def profile_simulation(
    num_updates: int = 100, sort_by: str = "cumulative"
) -> pstats.Stats:
    """
    Profile the game simulation.

    Args:
        num_updates: Number of update cycles to profile
        sort_by: Sort key for stats ('cumulative', 'time', 'calls', etc.)

    Returns:
        pstats.Stats object for further analysis
    """
    profiler = cProfile.Profile()
    profiler.enable()

    run_simulation(num_updates)

    profiler.disable()

    return pstats.Stats(profiler)


def print_profile_report(num_updates: int = 100, top_n: int = 50):
    """
    Print a profiling report to stdout.

    Args:
        num_updates: Number of update cycles to profile
        top_n: Number of top functions to display
    """
    stats = profile_simulation(num_updates)

    # Print summary
    print("=" * 70)
    print(f"PROFILING REPORT: {num_updates} Update Cycles")
    print("=" * 70)

    # Get total time
    total_time = stats.total_tt
    print(f"\nTotal execution time: {total_time:.3f} seconds")
    print(f"Time per update: {(total_time / num_updates) * 1000:.2f} ms")
    print(f"Estimated FPS: {num_updates / total_time:.1f}")

    print("\n" + "=" * 70)
    print(f"TOP {top_n} FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 70)

    # Print stats
    stats.sort_stats("cumulative")
    stats.print_stats(top_n)


def save_profile_report(output_path: str, num_updates: int = 100):
    """
    Save profiling report to a file.

    Args:
        output_path: Path to save the report
        num_updates: Number of update cycles to profile
    """
    stats = profile_simulation(num_updates)

    with open(output_path, "w") as f:
        # Redirect stdout to file
        old_stdout = sys.stdout
        sys.stdout = f

        print("=" * 70)
        print(f"PROFILING REPORT: {num_updates} Update Cycles")
        print("=" * 70)

        total_time = stats.total_tt
        print(f"\nTotal execution time: {total_time:.3f} seconds")
        print(f"Time per update: {(total_time / num_updates) * 1000:.2f} ms")
        print(f"Estimated FPS: {num_updates / total_time:.1f}")

        print("\n" + "=" * 70)
        print("TOP 50 FUNCTIONS BY CUMULATIVE TIME")
        print("=" * 70)

        stats.sort_stats("cumulative")
        stats.print_stats(50)

        sys.stdout = old_stdout

    print(f"Report saved to: {output_path}")


def compare_profiles(profile1_path: str, profile2_path: str):
    """
    Compare two profile stats files.

    Args:
        profile1_path: Path to first .prof file
        profile2_path: Path to second .prof file
    """
    stats1 = pstats.Stats(profile1_path)
    stats2 = pstats.Stats(profile2_path)

    print("Comparing profiles...")
    print(f"Profile 1: {profile1_path}")
    print(f"Profile 2: {profile2_path}")

    # Compare total times
    print(f"\nProfile 1 total time: {stats1.total_tt:.3f}s")
    print(f"Profile 2 total time: {stats2.total_tt:.3f}s")

    if stats2.total_tt > 0:
        improvement = ((stats1.total_tt - stats2.total_tt) / stats1.total_tt) * 100
        print(f"Change: {improvement:+.1f}%")


def main():
    """Main entry point for profiling."""
    import argparse

    parser = argparse.ArgumentParser(description="Profile Terminus Realm performance")
    parser.add_argument(
        "-n",
        "--updates",
        type=int,
        default=100,
        help="Number of update cycles to profile (default: 100)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Save report to file (default: print to stdout)",
    )
    parser.add_argument(
        "--save-raw",
        type=str,
        metavar="FILE",
        help="Save raw profile data to .prof file",
    )

    args = parser.parse_args()

    if args.output:
        save_profile_report(args.output, args.updates)
    else:
        print_profile_report(args.updates)

    if args.save_raw:
        profiler = cProfile.Profile()
        profiler.enable()
        run_simulation(args.updates)
        profiler.disable()
        profiler.dump_stats(args.save_raw)
        print(f"Raw profile data saved to: {args.save_raw}")


if __name__ == "__main__":
    main()
