"""
AI system for NPCs and monsters in the roguelike game.
"""

import random
import heapq
from core.ecs import EntityManager
from entities.components import Position, Monster
from world.map import GameMap


class AISystem:
    """System for managing AI behavior of NPCs and monsters."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.tick_counter = 0

    def update(
        self,
        game_map: GameMap,
        player_pos: Position,
        spatial_index=None,
        combat_callback=None,
        num_batches: int = 1,
    ):
        """Update AI for all monsters, optionally batching across multiple frames."""
        self.tick_counter = (self.tick_counter + 1) % num_batches

        monster_components = self.entity_manager.components_by_type.get(Monster, {})
        pos_components = self.entity_manager.components_by_type.get(Position, {})

        # Update loop for monsters
        for eid in list(monster_components.keys()):
            # Batching: Only update if it belongs to current tick's batch
            if num_batches > 1 and (eid % num_batches) != self.tick_counter:
                continue

            monster = monster_components.get(eid)
            pos = pos_components.get(eid)

            if not monster or not pos:
                continue

            # Different AI based on monster type
            if monster.ai_type == "aggressive":
                self._aggressive_ai(
                    eid, pos, player_pos, game_map, spatial_index, combat_callback
                )
            elif monster.ai_type == "passive":
                self._passive_ai(eid, pos, game_map, spatial_index)
            elif monster.ai_type == "patrol":
                self._patrol_ai(eid, pos, game_map, spatial_index)
            elif monster.ai_type == "static":
                pass

    def _get_path_to(self, start_x, start_y, end_x, end_y, game_map, spatial_index):
        """Simple A* pathfinding."""

        def heuristic(x1, y1, x2, y2):
            return max(abs(x1 - x2), abs(y1 - y2))

        frontier = []
        heapq.heappush(frontier, (0, (start_x, start_y)))
        came_from = {}
        cost_so_far = {}
        came_from[(start_x, start_y)] = None
        cost_so_far[(start_x, start_y)] = 0

        # Limit search depth for performance
        max_nodes = 100
        nodes_searched = 0

        target = (end_x, end_y)

        while frontier and nodes_searched < max_nodes:
            nodes_searched += 1
            current = heapq.heappop(frontier)[1]

            if current == target:
                break

            for dx, dy in [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]:
                nx, ny = current[0] + dx, current[1] + dy
                next_node = (nx, ny)

                if not (0 <= nx < game_map.width and 0 <= ny < game_map.height):
                    continue
                if not game_map.is_walkable(nx, ny):
                    continue

                # Check if occupied by something OTHER than the target or the start
                if (
                    spatial_index
                    and spatial_index.is_occupied(nx, ny)
                    and next_node != target
                ):
                    continue

                new_cost = cost_so_far[current] + 1
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + heuristic(nx, ny, end_x, end_y)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        if target not in came_from:
            return None

        # Reconstruct path
        path = []
        current = target
        while current != (start_x, start_y):
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

    def _aggressive_ai(
        self,
        eid: int,
        monster_pos: Position,
        player_pos: Position,
        game_map: GameMap,
        spatial_index,
        combat_callback=None,
    ):
        """Aggressive AI that moves toward the player using pathfinding."""
        dist_x = abs(player_pos.x - monster_pos.x)
        dist_y = abs(player_pos.y - monster_pos.y)
        distance = max(dist_x, dist_y)

        aggro_range = 10

        if distance > aggro_range:
            self._passive_ai(eid, monster_pos, game_map, spatial_index)
            return

        if distance == 1:
            # Adjacent to player, attack
            if combat_callback:
                combat_callback(eid)
            return

        # Find path to player
        path = self._get_path_to(
            monster_pos.x,
            monster_pos.y,
            player_pos.x,
            player_pos.y,
            game_map,
            spatial_index,
        )

        if path:
            new_x, new_y = path[0]

            # Final check if new position is actually free now
            if not spatial_index or not spatial_index.is_occupied(new_x, new_y):
                monster_pos.x = new_x
                monster_pos.y = new_y
                self.entity_manager.notify_component_change(eid, Position)
        else:
            # Fallback: Simple vector approach if A* fails due to depth limit but player is close
            dx = 0
            if player_pos.x > monster_pos.x: dx = 1
            elif player_pos.x < monster_pos.x: dx = -1
                
            dy = 0
            if player_pos.y > monster_pos.y: dy = 1
            elif player_pos.y < monster_pos.y: dy = -1
            
            new_x, new_y = monster_pos.x + dx, monster_pos.y + dy
            if game_map.is_walkable(new_x, new_y) and (not spatial_index or not spatial_index.is_occupied(new_x, new_y)):
                monster_pos.x = new_x
                monster_pos.y = new_y
                self.entity_manager.notify_component_change(eid, Position)
            else:
                self._passive_ai(eid, monster_pos, game_map, spatial_index)

    def _passive_ai(
        self,
        eid: int,
        monster_pos: Position,
        game_map: GameMap,
        spatial_index,
    ):
        """Passive AI that occasionally moves randomly."""
        if random.random() < 0.1:
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

            if (
                0 <= new_x < game_map.width
                and 0 <= new_y < game_map.height
                and game_map.is_walkable(new_x, new_y)
            ):
                if not spatial_index or not spatial_index.is_occupied(new_x, new_y):
                    monster_pos.x = new_x
                    monster_pos.y = new_y
                    self.entity_manager.notify_component_change(eid, Position)

    def _patrol_ai(
        self,
        eid: int,
        monster_pos: Position,
        game_map: GameMap,
        spatial_index,
    ):
        """Patrol AI that moves randomly but stays in a general area."""
        if random.random() < 0.4:
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

            if (
                0 <= new_x < game_map.width
                and 0 <= new_y < game_map.height
                and game_map.is_walkable(new_x, new_y)
            ):
                if not spatial_index or not spatial_index.is_occupied(new_x, new_y):
                    monster_pos.x = new_x
                    monster_pos.y = new_y
                    self.entity_manager.notify_component_change(eid, Position)
