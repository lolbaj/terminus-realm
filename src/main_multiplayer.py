"""
Main entry point for the multiplayer client of Terminus Realm.
Connects to the Go server via WebSocket.
"""

import sys
import os
import asyncio
import websockets
import json

# Add the directory containing this file (src) to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from input.handler import InputHandler
from ui.renderer import Renderer
from core.ecs import EntityManager
from world.map import GameMap
from entities.components import Position, Render, Player, Monster
from entities.entities import EntityManagerWrapper


class ClientEngine:
    """Main engine for the multiplayer client."""

    def __init__(self, server_uri: str = "ws://127.0.0.1:8080/ws"):
        self.server_uri = server_uri
        self.websocket = None
        self.connected = False
        self.input_handler = InputHandler()
        self.renderer = Renderer()

        # Local state that will be updated from server
        self.player_id = None  # This is the server string ID
        self.local_player_eid = None  # This is the local ECS int ID
        self.world_state = {}

        # ECS and Map for rendering
        self.entity_manager = EntityManager()
        self.entity_wrapper = EntityManagerWrapper(self.entity_manager)
        self.game_map = GameMap(21, 21)  # Matches server view radius 10 (10*2 + 1)

    async def connect_to_server(self):
        """Connect to the Go server."""
        try:
            self.websocket = await websockets.connect(self.server_uri)
            self.connected = True
            print(f"Connected to server at {self.server_uri}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for messages from the server."""
        print("Listening for messages...")
        try:
            async for message in self.websocket:
                await self.handle_server_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
            self.connected = False
        except Exception as e:
            print(f"Error receiving message from server: {e}")
            import traceback
            traceback.print_exc()

    async def handle_server_message(self, message):
        """Handle a message received from the server."""
        try:
            msg_type = message.get("type")

            if msg_type == "login_success":
                self.player_id = message.get("payload", {}).get("player_id")
                print(f"Logged in successfully with player ID: {self.player_id}")
                with open("client_debug.log", "a") as f:
                    f.write(f"Login success: {self.player_id}\n")
            elif msg_type == "update":
                payload = message.get("payload", {})
                self.world_state = payload
                self._update_local_state(payload)
            elif msg_type == "error":
                error_msg = message.get("payload", {})
                print(f"Server error: {error_msg}")
                with open("client_debug.log", "a") as f:
                    f.write(f"Server error: {error_msg}\n")
        except Exception as e:
            print(f"Error handling message: {e}")
            import traceback
            traceback.print_exc()
            with open("client_debug.log", "a") as f:
                f.write(f"Error handling message: {e}\n{traceback.format_exc()}\n")

    def _update_local_state(self, payload):
        """Update local ECS and Map from server payload."""
        try:
            # 1. Update Map
            map_data = payload.get("map", {})
            tiles = map_data.get("tiles")
            if tiles:
                for y, row in enumerate(tiles):
                    for x, tile_type in enumerate(row):
                        if y < self.game_map.height and x < self.game_map.width:
                            self.game_map.tiles[y, x] = int(tile_type)

            # Offset for entities
            center_x = int(map_data.get("center_x", 0))
            center_y = int(map_data.get("center_y", 0))
            view_radius = int(map_data.get("radius", 10))
            start_x = center_x - view_radius
            start_y = center_y - view_radius

            # 2. Update Entities
            self.entity_manager = EntityManager()
            self.entity_wrapper = EntityManagerWrapper(self.entity_manager)

            def to_local(wx, wy):
                return int(wx) - start_x, int(wy) - start_y

            # Local Player
            local_px, local_py = to_local(center_x, center_y)
            self.local_player_eid = self.entity_wrapper.factory.create_player(
                local_px, local_py
            )

            # Other Players
            players = payload.get("players", [])
            for p in players:
                if p.get("id") == self.player_id:
                    continue
                lx, ly = to_local(p.get("x"), p.get("y"))
                if 0 <= lx < self.game_map.width and 0 <= ly < self.game_map.height:
                    eid = self.entity_manager.create_entity()
                    self.entity_manager.add_component(eid, Position(lx, ly))
                    char = p.get("icon", "@")
                    self.entity_manager.add_component(
                        eid, Render(char=char, fg_color=(200, 200, 255))
                    )
                    self.entity_manager.add_component(eid, Player())

            # Monsters
            monsters = payload.get("monsters", [])
            for m in monsters:
                lx, ly = to_local(m.get("x"), m.get("y"))
                if 0 <= lx < self.game_map.width and 0 <= ly < self.game_map.height:
                    eid = self.entity_manager.create_entity()
                    self.entity_manager.add_component(eid, Position(lx, ly))
                    char = m.get("char", "M")
                    self.entity_manager.add_component(
                        eid, Render(char=char, fg_color=(255, 100, 100))
                    )
                    self.entity_manager.add_component(
                        eid, Monster(name=m.get("name", "Monster"))
                    )
        except Exception as e:
            import traceback
            with open("client_debug.log", "a") as f:
                f.write(f"Error in _update_local_state: {e}\n{traceback.format_exc()}\n")

    async def login(self, username: str):
        """Send a login request to the server."""
        login_msg = {
            "type": "login",
            "payload": {
                "username": username,
                "password": "",
            },
        }
        if self.websocket and self.connected:
            await self.websocket.send(json.dumps(login_msg))

    async def send_move(self, direction: str):
        """Send a movement request to the server."""
        move_msg = {"type": "move", "payload": {"direction": direction}}
        if self.websocket and self.connected:
            await self.websocket.send(json.dumps(move_msg))

    async def game_loop(self):
        """Main game loop for input and rendering."""
        await self.login("Player1")

        while self.connected:
            # Handle input
            input_event = self.input_handler.get_input_non_blocking()
            if input_event:
                if input_event.action_type == "move":
                    dx, dy = input_event.dx, input_event.dy
                    direction = None
                    if dx == 0 and dy == -1:
                        direction = "north"
                    elif dx == 0 and dy == 1:
                        direction = "south"
                    elif dx == -1 and dy == 0:
                        direction = "west"
                    elif dx == 1 and dy == 0:
                        direction = "east"
                    elif dx == -1 and dy == -1:
                        direction = "northwest"
                    elif dx == 1 and dy == -1:
                        direction = "northeast"
                    elif dx == -1 and dy == 1:
                        direction = "southwest"
                    elif dx == 1 and dy == 1:
                        direction = "southeast"
                    
                    if direction:
                        await self.send_move(direction)
                elif input_event.key == "p" or input_event.action_type == "quit":
                    self.connected = False
                    break

            # Render
            if self.local_player_eid is not None:
                self.renderer.render(
                    game_map=self.game_map,
                    entity_manager=self.entity_manager,
                    entity_wrapper=self.entity_wrapper,
                    player_id=self.local_player_eid,
                    game_state="PLAYING",
                )
            else:
                self.renderer.render() # Fallback to waiting screen

            await asyncio.sleep(0.016)

    async def run(self):
        """Start the client."""
        if not await self.connect_to_server():
            print("Could not connect to server. Exiting.")
            return

        self.renderer.start()
        try:
            await asyncio.gather(self.listen_for_messages(), self.game_loop())
        except Exception as e:
            print(f"Client loop error: {e}")
        finally:
            self.renderer.stop()
            await self.shutdown()

    async def shutdown(self):
        """Clean up resources."""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
        self.input_handler.restore_terminal()


async def main():
    """Entry point for the multiplayer client."""
    print("Starting Terminus Realm Multiplayer Client...")
    client_engine = ClientEngine()
    try:
        await client_engine.run()
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        await client_engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())