"""
Terminal rendering system for the roguelike game using rich.
"""

from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.live import Live
from typing import TYPE_CHECKING, Optional, Any, List

from config import CONFIG
from entities.components import Position, Render, Health, Monster, Level, Skills, Equipment, Inventory, Item, Shop, WeaponStats

if TYPE_CHECKING:
    from world.map import GameMap
    from core.ecs import EntityManager
    from entities.entities import EntityManagerWrapper


class Renderer:
    def __init__(self):
        self.console = Console()
        self.screen_width = CONFIG.screen_width
        self.screen_height = CONFIG.screen_height

        # Initialize with empty world state (for multiplayer)
        self.world_state = {"players": [], "monsters": [], "items": [], "map": {}}
        
        # Initialize Live display
        # Start with an empty layout or panel
        self.live = Live(
            Panel("Initializing..."),
            console=self.console, 
            screen=True, 
            auto_refresh=False
        )

    def start(self):
        """Start the live rendering."""
        self.live.start()

    def stop(self):
        """Stop the live rendering."""
        self.live.stop()

    def update_world_state(self, world_state):
        """Update the renderer with new world state from the server."""
        self.world_state = world_state

    def render(
        self,
        game_map: Optional["GameMap"] = None,
        entity_manager: Optional["EntityManager"] = None,
        entity_wrapper: Optional["EntityManagerWrapper"] = None,
        player_id: Optional[int] = None,
        message_log: Optional[List[Any]] = None,
        game_state: str = "PLAYING",
        inventory_selection: int = 0,
        shop_id: Optional[int] = None,
    ):
        """Render the current game state to the terminal."""
        if game_map and entity_manager and player_id is not None:
            # Local Mode rendering
            self._render_local(
                game_map,
                entity_manager,
                entity_wrapper,
                player_id,
                message_log,
                game_state,
                inventory_selection,
                shop_id,
            )
        else:
            # Multiplayer Mode rendering (original logic)
            self._render_multiplayer()

    def _render_multiplayer(self):
        """Original multiplayer rendering logic."""
        content = Text()
        content.append("Terminus Realm - Multiplayer\n", style="bold blue")
        content.append(f"Players: {len(self.world_state.get('players', []))}\n")
        content.append(f"Monsters: {len(self.world_state.get('monsters', []))}\n\n")

        player = None
        for p in self.world_state.get("players", []):
            if p.get("is_local", False):
                player = p
                break

        if player:
            content.append(f"You are at ({player['x']}, {player['y']})\n")
            grid_str = self.render_area_around_player(player)
            content.append(grid_str)
        else:
            content.append("Waiting for player data from server...")
            
        self.live.update(Panel(content), refresh=True)

    def _render_local(
        self,
        game_map,
        entity_manager,
        entity_wrapper,
        player_id,
        message_log,
        game_state,
        inventory_selection,
        shop_id,
    ):
        """Rich-based local game rendering."""
        # Create Layout
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=4),
            Layout(name="footer", ratio=1)
        )
        layout["main"].split_row(
            Layout(name="world", ratio=3),
            Layout(name="stats", ratio=1)
        )

        # 1. Render World
        world_text = self._get_world_text(game_map, entity_manager, player_id)
        layout["world"].update(
            Panel(world_text, title="Terminus Realm", border_style="green")
        )

        # 2. Render Stats
        stats_panel = self._get_stats_panel(entity_manager, player_id)
        layout["stats"].update(stats_panel)

        # 3. Render Log
        log_panel = self._get_log_panel(message_log)
        layout["footer"].update(log_panel)

        # 4. Handle Overlays (Inventory, Shop)
        if game_state == "INVENTORY":
            overlay = self._get_inventory_overlay(entity_manager, player_id, inventory_selection)
            self.live.update(Group(layout, Align.center(overlay)), refresh=True)
            
        elif game_state == "SHOPPING" and shop_id is not None:
            overlay = self._get_shop_overlay(entity_manager, shop_id, inventory_selection)
            self.live.update(Group(layout, Align.center(overlay)), refresh=True)
        else:
            self.live.update(layout, refresh=True)

    def _get_world_text(self, game_map, entity_manager, player_id) -> Text:
        """Get the character-based representation of the visible world."""
        player_pos = entity_manager.get_component(player_id, Position)
        if not player_pos:
            return Text("Player position not found")

        # Calculate viewport
        view_w = self.screen_width - 25 # Reserve space for stats
        view_h = self.screen_height - 8
        
        start_x = player_pos.x - view_w // 4
        start_y = player_pos.y - view_h // 2
        
        # Adjust start_x/y to stay in bounds
        start_x = max(0, min(start_x, game_map.width - view_w // 2))
        start_y = max(0, min(start_y, game_map.height - view_h))

        lines = []
        for y in range(start_y, start_y + view_h):
            line = Text()
            for x in range(start_x, start_x + view_w // 2):
                # Get tile background for consistent look
                bg = game_map.get_tile_bg_color(x, y)
                bg_style = ""
                if bg:
                    bg_style = f" on rgb({bg[0]},{bg[1]},{bg[2]})"

                # 1. Check for entities
                found_entity = False
                # Simple optimization: only check entities at this x,y
                # In a real engine we'd use a spatial grid, here we iterate (slow but okay for small view)
                
                # Check Player
                if x == player_pos.x and y == player_pos.y:
                    render = entity_manager.get_component(player_id, Render)
                    line.append(render.char, style=f"rgb({render.fg_color[0]},{render.fg_color[1]},{render.fg_color[2]}){bg_style}")
                    found_entity = True
                
                if not found_entity:
                    # Check Monsters
                    monsters = entity_manager.get_all_entities_with_component(Monster)
                    for eid in monsters:
                        pos = entity_manager.get_component(eid, Position)
                        if pos and pos.x == x and pos.y == y:
                            render = entity_manager.get_component(eid, Render)
                            line.append(render.char, style=f"rgb({render.fg_color[0]},{render.fg_color[1]},{render.fg_color[2]}){bg_style}")
                            found_entity = True
                            break
                
                if not found_entity:
                    # Check Items
                    items = entity_manager.get_all_entities_with_component(Item)
                    for eid in items:
                        pos = entity_manager.get_component(eid, Position)
                        if pos and pos.x == x and pos.y == y:
                            render = entity_manager.get_component(eid, Render)
                            line.append(render.char, style=f"rgb({render.fg_color[0]},{render.fg_color[1]},{render.fg_color[2]}){bg_style}")
                            found_entity = True
                            break

                # 2. Render Map
                if not found_entity:
                    char = game_map.get_tile_char(x, y)
                    fg = game_map.get_tile_fg_color(x, y)
                    
                    style = f"rgb({fg[0]},{fg[1]},{fg[2]}){bg_style}"
                    
                    line.append(char, style=style)
            
            lines.append(line)
        
        return Text("\n").join(lines)

    def _get_stats_panel(self, entity_manager, player_id) -> Panel:
        """Render player statistics."""
        health = entity_manager.get_component(player_id, Health)
        level = entity_manager.get_component(player_id, Level)
        skills = entity_manager.get_component(player_id, Skills)
        equip = entity_manager.get_component(player_id, Equipment)
        pos = entity_manager.get_component(player_id, Position)

        stats_text = Text()
        stats_text.append(f"Position: {pos.x},{pos.y}\n", style="cyan")
        
        if health:
            hp_color = "green" if health.current / health.maximum > 0.5 else "yellow"
            if health.current / health.maximum < 0.2:
                hp_color = "red"
            stats_text.append(f"HP: {health.current}/{health.maximum}\n", style=hp_color)
        
        if level:
            stats_text.append(f"Level: {level.current_level}\n", style="bold magenta")
            stats_text.append(f"XP: {level.current_xp}/{level.xp_to_next_level}\n\n", style="magenta")

        if skills:
            stats_text.append("Skills:\n", style="bold yellow")
            stats_text.append(f" Melee: {skills.melee}\n", style="red")
            stats_text.append(f" Dist:  {skills.distance}\n", style="green")
            stats_text.append(f" Magic: {skills.magic}\n\n", style="blue")

        if equip:
            stats_text.append("Equipment:\n", style="bold white")
            stats_text.append(f" Wep: {equip.weapon_type.capitalize()}\n", style="yellow")

        return Panel(stats_text, title="Stats", border_style="blue")

    def _get_log_panel(self, message_log) -> Panel:
        """Render the message log."""
        log_text = Text()
        if message_log:
            for msg, color in message_log:
                log_text.append(f"{msg}\n", style=f"rgb({color[0]},{color[1]},{color[2]})")
        
        return Panel(log_text, title="Messages", border_style="white")

    def _get_inventory_overlay(self, entity_manager, player_id, selection) -> Panel:
        """Render the inventory overlay."""
        inv = entity_manager.get_component(player_id, Inventory)
        if not inv:
            return Panel("No inventory found")

        table = Table(title="Inventory", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=2)
        table.add_column("Item", width=30)
        table.add_column("Type")

        for i, item_id in enumerate(inv.items):
            item_comp = entity_manager.get_component(item_id, Item)
            style = "reverse" if i == selection else ""
            
            item_name = item_comp.name if item_comp else "Unknown"
            rarity_color = "white"
            if item_comp and hasattr(item_comp, 'rarity'):
                from entities.entities import RARITY_CONFIG
                rc = RARITY_CONFIG.get(item_comp.rarity, {"color": (255,255,255)})
                rarity_color = f"rgb({rc['color'][0]},{rc['color'][1]},{rc['color'][2]})"

            item_type = "Misc"
            if entity_manager.has_component(item_id, WeaponStats):
                item_type = "Weapon"
            
            table.add_row(
                str(i),
                Text(item_name, style=f"{style} {rarity_color}"),
                item_type,
                style=style
            )

        return Panel(table, border_style="magenta", expand=False)

    def _get_shop_overlay(self, entity_manager, shop_id, selection) -> Panel:
        """Render the shop overlay."""
        shop = entity_manager.get_component(shop_id, Shop)
        if not shop:
            return Panel("Shop not found")

        table = Table(title=shop.shop_name, show_header=True, header_style="bold yellow")
        table.add_column("#", style="dim", width=2)
        table.add_column("Item", width=25)
        table.add_column("Price", justify="right")

        for i, (item_type, price) in enumerate(shop.items):
            style = "reverse" if i == selection else ""
            table.add_row(str(i), item_type.replace("_", " ").capitalize(), f"{price}g", style=style)

        return Panel(table, border_style="yellow", expand=False)

    def render_area_around_player(self, player) -> str:
        """Render a small area around the player (multiplayer mode)."""
        center_x, center_y = player["x"], player["y"]
        view_radius = 5
        grid = [["." for _ in range(view_radius * 2 + 1)] for _ in range(view_radius * 2 + 1)]
        grid[view_radius][view_radius] = "@"

        for p in self.world_state.get("players", []):
            if p.get("id") != player["id"]:
                rel_x = p["x"] - center_x
                rel_y = p["y"] - center_y
                if abs(rel_x) <= view_radius and abs(rel_y) <= view_radius:
                    grid[view_radius + rel_y][view_radius + rel_x] = "P"

        for m in self.world_state.get("monsters", []):
            rel_x = m["x"] - center_x
            rel_y = m["y"] - center_y
            if abs(rel_x) <= view_radius and abs(rel_y) <= view_radius:
                grid[view_radius + rel_y][view_radius + rel_x] = "M"

        rows = []
        for row in grid:
            rows.append("".join(row))
        return "\n".join(rows)
