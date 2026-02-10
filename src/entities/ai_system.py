"""
AI system for NPCs and monsters in the roguelike game.
"""

import random
from core.ecs import EntityManager
from entities.components import Position, Monster
from world.map import GameMap


class AISystem:
    """System for managing AI behavior of NPCs and monsters."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def update(self, game_map: GameMap, player_pos: Position, combat_callback=None):
        """Update AI for all monsters."""
        # Pre-calculate occupied positions for faster collision detection
        # Optimization: Only check blocking entities (Monsters and Player)
        # instead of iterating over ALL entities.
        occupied_positions = set()

        # Add Monsters
        monster_entities = self.entity_manager.get_all_entities_with_component(Monster)
        for eid in monster_entities:
            pos = self.entity_manager.get_component(eid, Position)
            if pos:
                occupied_positions.add((pos.x, pos.y))

        # Add Player
        from entities.components import Player

        player_entities = self.entity_manager.get_all_entities_with_component(Player)
        for eid in player_entities:
            pos = self.entity_manager.get_component(eid, Position)
            if pos:
                occupied_positions.add((pos.x, pos.y))

        # Update loop for monsters
        for eid in monster_entities:
            monster = self.entity_manager.get_component(eid, Monster)
            pos = self.entity_manager.get_component(eid, Position)

            if not monster or not pos:
                continue

            # Different AI based on monster type
            if monster.ai_type == "aggressive":
                self._aggressive_ai(
                    eid, pos, player_pos, game_map, occupied_positions, combat_callback
                )
            elif monster.ai_type == "passive":
                self._passive_ai(eid, pos, game_map, occupied_positions)
            elif monster.ai_type == "patrol":
                self._patrol_ai(eid, pos, game_map, occupied_positions)
            elif monster.ai_type == "static":
                pass

    def _aggressive_ai(
        self,
        eid: int,
        monster_pos: Position,
        player_pos: Position,
        game_map: GameMap,
        occupied_positions: set,
        combat_callback=None,
    ):
        """Aggressive AI that moves toward the player if close enough."""
        # Calculate distance to player (Chebyshev distance for grid)
        dist_x = abs(player_pos.x - monster_pos.x)
        dist_y = abs(player_pos.y - monster_pos.y)
        distance = max(dist_x, dist_y)

        aggro_range = 8

        if distance > aggro_range:
            # Too far, act passively
            self._passive_ai(eid, monster_pos, game_map, occupied_positions)
            return

        # Calculate desired direction
        dx = player_pos.x - monster_pos.x
        dy = player_pos.y - monster_pos.y

        # Normalize direction
        move_x = 0
        move_y = 0
        if dx != 0:
            move_x = 1 if dx > 0 else -1
        if dy != 0:
            move_y = 1 if dy > 0 else -1

        # Determine possible moves
        # Prioritize diagonal if both match, then axis-aligned
        candidates = []
        if move_x != 0 and move_y != 0:
            candidates.append((move_x, move_y))  # Diagonal
            candidates.append((move_x, 0))       # Horizontal slide
            candidates.append((0, move_y))       # Vertical slide
        elif move_x != 0:
            candidates.append((move_x, 0))
            # Optional: try diagonal if straight blocked? (maybe too smart for basic mobs)
        elif move_y != 0:
            candidates.append((0, move_y))

        # Try to move
        # moved = False
        for d_x, d_y in candidates:
            target_x = monster_pos.x + d_x
            target_y = monster_pos.y + d_y

            # Check if it's the player (Combat)
            if target_x == player_pos.x and target_y == player_pos.y:
                if combat_callback:
                    combat_callback(eid)
                else:
                    print(f"Monster {eid} bumps into player!")
                # moved = True
                break
            
            # Check walkability
            if (
                0 <= target_x < game_map.width
                and 0 <= target_y < game_map.height
                and game_map.is_walkable(target_x, target_y)
            ):
                # Check collision with other entities
                if (target_x, target_y) not in occupied_positions:
                    # Move!
                    occupied_positions.remove((monster_pos.x, monster_pos.y))
                    occupied_positions.add((target_x, target_y))
                    monster_pos.x = target_x
                    monster_pos.y = target_y
                    # moved = True
                    break
        
        # If couldn't move aggressively, maybe just wait or act passively?
        # For now, just stay put if blocked.

    def _passive_ai(
        self,
        eid: int,
        monster_pos: Position,
        game_map: GameMap,
        occupied_positions: set,
    ):
        """Passive AI that occasionally moves randomly."""
        # 10% chance to move randomly (reduced from 20%)
        if random.random() < 0.1:
            # Choose a random direction (including diagonals)
            directions = [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]
            dx, dy = random.choice(directions)

            new_x = monster_pos.x + dx
            new_y = monster_pos.y + dy

            # Check if the new position is walkable
            if (
                0 <= new_x < game_map.width
                and 0 <= new_y < game_map.height
                and game_map.is_walkable(new_x, new_y)
            ):
                # Check collision using the set
                if (new_x, new_y) not in occupied_positions:
                    # Update occupied positions
                    occupied_positions.remove((monster_pos.x, monster_pos.y))
                    occupied_positions.add((new_x, new_y))

                    # Move the monster
                    monster_pos.x = new_x
                    monster_pos.y = new_y

    def _patrol_ai(
        self,
        eid: int,
        monster_pos: Position,
        game_map: GameMap,
        occupied_positions: set,
    ):
        """Patrol AI that moves randomly but stays in a general area."""
        # For now, implement as slightly more active passive AI
        # 40% chance to move randomly (more than passive)
        if random.random() < 0.4:
            # Choose a random direction (including diagonals)
            directions = [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]
            dx, dy = random.choice(directions)

            new_x = monster_pos.x + dx
            new_y = monster_pos.y + dy

            # Check if the new position is walkable
            if (
                0 <= new_x < game_map.width
                and 0 <= new_y < game_map.height
                and game_map.is_walkable(new_x, new_y)
            ):
                # Check collision using the set
                if (new_x, new_y) not in occupied_positions:
                    # Update occupied positions
                    occupied_positions.remove((monster_pos.x, monster_pos.y))
                    occupied_positions.add((new_x, new_y))

                    # Move the monster
                    monster_pos.x = new_x
                    monster_pos.y = new_y
