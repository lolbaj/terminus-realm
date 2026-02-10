"""
Turn-based timing system for the roguelike game.
"""

from enum import Enum
from typing import Callable
import time


class TurnState(Enum):
    """Possible states of the turn system."""

    PLAYER_TURN = "player_turn"
    ENEMY_TURN = "enemy_turn"
    PROCESSING = "processing"
    WAITING = "waiting"


class TurnClock:
    """Manages turn-based timing for the game."""

    def __init__(self):
        self.state = TurnState.WAITING
        self.current_entity = None
        self.turn_callback = None
        self.action_queue = []
        self.last_action_time = time.time()

    def start_player_turn(self):
        """Start the player's turn."""
        self.state = TurnState.PLAYER_TURN
        self.last_action_time = time.time()

    def end_player_turn(self):
        """End the player's turn and start enemy turns."""
        self.state = TurnState.ENEMY_TURN
        self.process_enemy_turns()

    def process_enemy_turns(self):
        """Process all enemy turns."""
        # In a real implementation, this would iterate through all enemies
        # and allow them to take their actions
        self.state = TurnState.PROCESSING
        # Simulate enemy processing
        time.sleep(0.1)  # Simulate processing time
        self.state = TurnState.WAITING

    def wait_for_input(self):
        """Wait for player input."""
        self.state = TurnState.WAITING
        return self.state == TurnState.PLAYER_TURN

    def schedule_action(self, callback: Callable, delay: float = 0.0):
        """Schedule an action to happen after a delay."""
        scheduled_time = time.time() + delay
        self.action_queue.append((scheduled_time, callback))

    def process_scheduled_actions(self):
        """Process any scheduled actions that are due."""
        current_time = time.time()
        completed = []

        for scheduled_time, callback in self.action_queue:
            if current_time >= scheduled_time:
                callback()
                completed.append((scheduled_time, callback))

        # Remove completed actions
        for item in completed:
            self.action_queue.remove(item)

    def reset(self):
        """Reset the turn clock."""
        self.state = TurnState.WAITING
        self.current_entity = None
        self.action_queue.clear()
