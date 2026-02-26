"""
Main game engine for the roguelike game.
"""

import time
from typing import Optional
from collections import deque
from rich.console import Console
from core.ecs import EntityManager, SystemManager
from config import CONFIG
from world.map import GameMap, CHAR_MAP
from entities.entities import EntityManagerWrapper
from entities.components import Position
from ui.renderer import Renderer
from input.handler import InputHandler, InputEvent
from entities.spawn_system import SpawnSystem
from entities.ai_system import AISystem
from entities.boss_system import BossSystem
from world.fov import calculate_fov
from core.spatial import SpatialIndex


class GameEngine:
    """Main game engine that manages the game loop and systems."""

    def __init__(self):
        self.running = True
        self.entity_manager = EntityManager()
        self.system_manager = SystemManager(self.entity_manager)
        self.last_time = time.time()
        self.accumulator = 0.0
        self.target_fps = 30
        self.frame_duration = 1.0 / self.target_fps
        self.fixed_timestep = 1.0 / CONFIG.target_fps

        # Override configurations for testing
        self.override_map_path: Optional[str] = None
        self.override_start_pos: Optional[tuple[int, int]] = None

        # Initialize game components
        self.game_map: Optional[GameMap] = None
        self.entity_wrapper = EntityManagerWrapper(self.entity_manager)
        self.player_id: Optional[int] = None

        # Initialize spatial index
        self.spatial_index = SpatialIndex(self.entity_manager)
        # Inject spatial index into wrapper
        self.entity_wrapper.spatial_index = self.spatial_index

        # Initialize rendering
        import shutil

        t_cols, t_lines = shutil.get_terminal_size(
            (CONFIG.screen_width, CONFIG.screen_height)
        )
        self.console = Console()
        self.renderer = Renderer(self.console, t_cols, t_lines)

        # Initialize input handling
        self.input_handler = InputHandler()
        self.input_handler.setup_terminal()

        # Initialize spawn system
        self.spawn_system = SpawnSystem(
            self.entity_manager, self.entity_wrapper.factory, self.spatial_index
        )

        # Initialize AI system
        self.ai_system = AISystem(self.entity_manager)

        # Initialize boss system
        self.boss_system = BossSystem(self.entity_manager, self.entity_wrapper.factory)

        # VFX system
        from entities.vfx_system import VFXSystem

        self.vfx_system = VFXSystem(self.entity_manager)

        # Timers
        self.ai_timer = 0.0
        self.mana_regen_timer = 0.0

        # Message Log
        self.message_log = deque(maxlen=5)
        self.log("Welcome to the dungeon!", (255, 255, 0))

        # Game State
        self.game_state = "PLAYING"  # PLAYING, INVENTORY
        self.inventory_selection = 0
        self.current_shop_id = None
        self._last_fov_pos = None

    def update_fov(self):
        """Update the field of view based on player position."""
        if self.player_id is None or self.game_map is None:
            return

        pos = self.entity_manager.get_component(self.player_id, Position)
        if pos:
            # Check if player has moved
            current_pos = (pos.x, pos.y)
            if self._last_fov_pos == current_pos:
                return

            self._last_fov_pos = current_pos
            fov_radius = 8  # Default radius
            fov_array = calculate_fov(self.game_map, pos.x, pos.y, fov_radius)
            self.game_map.update_fov(fov_array)

    def log(self, text: str, color: tuple = (255, 255, 255)):
        """Add a message to the log."""
        self.message_log.append((text, color))

    def run(self):
        """Run the main game loop."""
        print("Game engine started...")
        print("Controls: WASD/Arrows to move, Space/Enter for Actions, ? for Help")
        print("Note: Diagonal movement uses Q, E, Z, C around the WASD keys.")

        # Initialize the game
        self.initialize_game()

        # Main game loop
        loop_count = 0
        while self.running:
            try:
                loop_count += 1
                current_time = time.time()
                delta_time = current_time - self.last_time
                self.last_time = current_time

                # Update accumulator
                self.accumulator += delta_time

                # Process fixed updates
                while self.accumulator >= self.fixed_timestep:
                    self.update(self.fixed_timestep)
                    self.accumulator -= self.fixed_timestep

                # Check for input
                input_event = self.input_handler.check_for_input()
                if input_event:
                    self.handle_input(input_event)

                # Render (variable rate)
                self.render()

                # Control frame rate
                self.throttle_framerate()
            except Exception as e:
                import traceback

                self.input_handler.restore_terminal()

                with open("game_debug.log", "a") as f:
                    f.write(
                        f"Loop Crash at iteration {loop_count}: {e}\n{traceback.format_exc()}\n"
                    )
                raise e

    def initialize_game(self):
        """Initialize game state."""
        print("Initializing game...")

        if self.override_map_path:
            # Load specific map for testing
            try:
                import toml
                from world.map import GameMap

                with open(self.override_map_path, "r") as f:
                    data = toml.load(f)

                maps = data.get("maps", [])
                if not maps:
                    raise ValueError("No maps found in file")

                # assume first map for now or we could add another arg for map name
                m_data = maps[0]
                layout = m_data["layout"].strip().split("\n")
                h = len(layout)
                w = max(len(row) for row in layout) if h > 0 else 0

                self.game_map = GameMap(w, h)

                for y, row in enumerate(layout):
                    for x, char in enumerate(row):
                        if x < w:
                            if char == "@":
                                self.override_start_pos = (x, y)
                                tid = 0
                            else:
                                tid = CHAR_MAP.get(char, 0)  # Default to floor

                            self.game_map.tiles[y, x] = tid

                print(f"Loaded Test Map: {m_data.get('name', 'Untitled')}")
                start_x, start_y = (
                    self.override_start_pos
                    if self.override_start_pos
                    else (w // 2, h // 2)
                )

            except Exception as e:
                print(f"Failed to load test map: {e}")
                import sys

                sys.exit(1)
        else:
            # Get the persistent world
            from world.persistent_world import get_persistent_world

            persistent_world = get_persistent_world()

            # Load the FULL world map for seamless scrolling
            self.game_map = persistent_world.get_full_game_map()
            print("Loaded Full World Map")

            # Start player
            if self.override_start_pos:
                start_x, start_y = self.override_start_pos
            elif persistent_world.player_start_pos:
                start_x, start_y = persistent_world.player_start_pos
            else:
                # Fallback: Start player in the center of the Town (Chunk 0,0)
                start_x = persistent_world.center_x + 25
                start_y = persistent_world.center_y + 25

            # Ensure we don't spawn in a wall
        # Spiral search for free spot
        found = False
        for r in range(0, 50):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    tx, ty = start_x + dx, start_y + dy
                    if self.game_map.is_walkable(tx, ty):
                        start_x, start_y = tx, ty
                        found = True
                        break
                if found:
                    break
            if found:
                break

        self.player_id = self.entity_wrapper.factory.create_player(start_x, start_y)

        print(f"Player created at ({start_x}, {start_y})")

        # Spawn pre-placed entities (Monsters/Items from Static Maps)
        self.spawn_preplaced_entities()

        # Spawn static shopkeeper nearby
        self.entity_wrapper.factory.create_shopkeeper(
            start_x + 5,
            start_y,
            "Market Vendor",
            [
                ("health_potion", 20),
                ("sword", 100),
                ("shield", 50),
                ("bow", 120),
                ("wand", 150),
            ],
        )

        # Initial monster spawn around player
        self.update_active_region()
        print("Initial monsters spawned")

        # Initial FOV update
        self.update_fov()

    def spawn_preplaced_entities(self):
        """Spawn entities that were hand-placed in static map chunks."""
        from world.persistent_world import get_persistent_world
        world = get_persistent_world()
        
        count = 0
        for entry in world.preplaced_entities:
            e_type = entry["type"]
            e_subtype = entry["subtype"]
            ex, ey = entry["x"], entry["y"]
            
            if e_type == "monster":
                self.entity_wrapper.factory.create_monster(ex, ey, e_subtype)
                count += 1
            elif e_type == "item":
                self.entity_wrapper.factory.create_item(ex, ey, e_subtype)
                count += 1
                
        if count > 0:
            print(f"Spawned {count} pre-placed entities from static maps.")

    def update_active_region(self):
        """
        Dynamically manage entities based on player position.
        Despawn far away monsters and spawn new ones nearby.
        """
        if self.player_id is None:
            return

        pos = self.entity_manager.get_component(self.player_id, Position)
        if not pos:
            return

        # Despawn Radius (e.g. 60 tiles)
        despawn_radius = 60
        # Spawn Radius (e.g. 40 tiles)
        spawn_radius = 40

        # Despawn far entities
        from entities.components import Monster

        monsters = self.entity_manager.get_all_entities_with_component(Monster)
        count = 0
        for eid in monsters:
            m_pos = self.entity_manager.get_component(eid, Position)
            m_comp = self.entity_manager.get_component(eid, Monster)
            if m_pos:
                dist = max(abs(pos.x - m_pos.x), abs(pos.y - m_pos.y))
                if dist > despawn_radius:
                    # Don't despawn static NPCs like shopkeepers
                    if m_comp and m_comp.ai_type != "static":
                        self.entity_manager.destroy_entity(eid)
                else:
                    count += 1

        # Spawn new entities if density is low
        target_monsters = 20  # Keep around 20 monsters active
        if count < target_monsters:
            needed = target_monsters - count
            self.spawn_system.spawn_monsters_around_player(
                self.game_map, pos.x, pos.y, radius=spawn_radius, num_monsters=needed
            )

    def find_free_position(self) -> tuple[int, int]:
        """Find a free position on the map for the player."""
        if self.game_map is None:
            return CONFIG.player_start_x, CONFIG.player_start_y

        # Check configured start position first
        if (
            0 <= CONFIG.player_start_x < self.game_map.width
            and 0 <= CONFIG.player_start_y < self.game_map.height
            and self.game_map.is_walkable(CONFIG.player_start_x, CONFIG.player_start_y)
        ):
            return CONFIG.player_start_x, CONFIG.player_start_y

        # Look for a floor tile to place the player
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                if self.game_map.is_walkable(x, y):
                    return x, y

        # If no walkable tile found, return default position
        return CONFIG.player_start_x, CONFIG.player_start_y

    def update(self, dt: float):
        """Update game state."""
        # Update all systems
        self.system_manager.update_all(dt)

        # Update VFX system
        self.vfx_system.update(dt)

        # Update Temperature System
        self.update_temperature(dt)

        # Handle any game-specific updates
        self.handle_updates(dt)

    def update_temperature(self, dt: float):
        """Update entity temperatures and apply effects."""
        from entities.components import Temperature, Position, Health
        from world.map import TILE_LAVA, TILE_WATER, TILE_ICE
        from world.persistent_world import get_persistent_world
        import random
        
        world = get_persistent_world()
        
        # Get all entities with Temperature
        entities = self.entity_manager.get_all_entities_with_component(Temperature)
        
        for eid in entities:
            temp = self.entity_manager.get_component(eid, Temperature)
            pos = self.entity_manager.get_component(eid, Position)
            health = self.entity_manager.get_component(eid, Health)
            
            if not temp or not pos or not health:
                continue
                
            # 1. Determine Target Temperature based on biome and tile
            biome = world.get_biome(pos.x, pos.y)
            tile = self.game_map.tiles[pos.y, pos.x]
            
            target_temp = 25.0 # Comfortable baseline
            
            # Biome baselines
            if biome == "volcanic":
                target_temp = 60.0
            elif biome == "desert":
                target_temp = 45.0
            elif biome == "snow":
                target_temp = -10.0
            elif biome == "ocean":
                target_temp = 15.0
            
            # Tile overrides (Direct contact)
            if tile == TILE_LAVA:
                target_temp = 1000.0 # Incinerating
                temp.lava_contact_time += dt
                # Direct death if on lava for 3 seconds
                if temp.lava_contact_time >= 3.0:
                    self.log("You have been incinerated by direct lava contact!", (255, 50, 50))
                    temp.lava_contact_time = 0 # Reset
                    self.respawn_player()
                    continue
            else:
                temp.lava_contact_time = max(0, temp.lava_contact_time - dt * 2)
                
            if tile == TILE_WATER:
                target_temp -= 15.0
            if tile == TILE_ICE:
                target_temp = -30.0
            
            # 2. Equalize Temperature (Slowly move current towards target)
            # Normalization rate: 5 degrees per second base
            rate = 5.0
            if tile == TILE_LAVA:
                rate = 100.0 # Heating up VERY fast
            
            diff = target_temp - temp.current
            temp.current += diff * min(1.0, dt * (rate / 100.0))
            
            # 3. Apply Temperature Effects (Damage)
            # Heatstroke / Burning
            if temp.current > 50.0:
                heat_damage = (temp.current - 50.0) * 0.1 * dt
                if tile == TILE_LAVA:
                    heat_damage *= 5.0 # Extra damage for direct lava
                
                health.current -= heat_damage
                if random.random() < 0.05: # Occasional message
                    self.log("The heat is unbearable!", (255, 100, 0))
                    
            # Hypothermia / Freezing
            elif temp.current < 5.0:
                cold_damage = (5.0 - temp.current) * 0.05 * dt
                health.current -= cold_damage
                if random.random() < 0.05:
                    self.log("You are freezing to death!", (150, 200, 255))
            
            # Check death from cumulative temp damage
            if health.current <= 0:
                self.respawn_player()

    def render(self):
        """Render the game."""
        if self.game_map and self.player_id is not None:
            self.renderer.render(
                self.game_map,
                self.entity_manager,
                self.entity_wrapper,
                self.player_id,
                self.message_log,
                self.game_state,
                self.inventory_selection,
                shop_id=self.current_shop_id,
            )

    def handle_updates(self, dt: float):
        """Handle game-specific updates."""
        # Get player position once for all updates
        player_pos = self.entity_manager.get_component(self.player_id, Position)

        # Update AI for monsters (Batched across multiple frames)
        if player_pos:

            def combat_callback(attacker_id):
                self.handle_combat(attacker_id, self.player_id)

            # Calculate number of batches based on move delay and target FPS
            # e.g., 0.5s delay @ 30fps = 15 batches
            num_batches = max(1, int(CONFIG.ai_move_delay * CONFIG.target_fps))

            self.ai_system.update(
                self.game_map,
                player_pos,
                self.spatial_index,
                combat_callback,
                num_batches=num_batches,
            )

        # Check for boss encounters
        if player_pos:
            boss_encounter = self.boss_system.check_for_boss_encounter(
                player_pos.x, player_pos.y
            )
            if boss_encounter:
                self.log(
                    f"Danger approaches: {boss_encounter.name} is nearby!",
                    (255, 50, 50),
                )
                self.boss_system.trigger_boss_encounter(boss_encounter)

        # Mana regeneration
        self.mana_regen_timer += dt

        if self.mana_regen_timer >= 1.0:  # Regen every 1 second
            self.mana_regen_timer -= 1.0
            from entities.components import Mana

            if self.player_id is not None:
                mana = self.entity_manager.get_component(self.player_id, Mana)
                if mana and mana.current < mana.maximum:
                    mana.current = min(mana.maximum, mana.current + 2)

    def handle_input(self, event: InputEvent):
        """Handle input events based on game state."""
        if self.game_state == "PLAYING":
            if event.action_type == "move":
                self.move_player(event.dx, event.dy)
            elif event.action_type == "quit":
                self.quit()
            elif event.action_type == "action_menu":
                # Check for shop interaction first
                if self.check_for_shop():
                    return
                # Check for adjacent enemies to attack
                if self.check_for_attack():
                    return
                # Space bar - Swap Weapon
                self.swap_weapon()
            elif event.action_type == "select":
                # Enter key - Interact/Select
                pass
            elif event.action_type == "pickup":
                self.pickup_item()
            elif event.action_type == "inventory":
                self.game_state = "INVENTORY"
                self.inventory_selection = 0
            elif event.action_type == "stats":
                self.game_state = "STATS"
                self.inventory_selection = 0  # Re-use for menu index
            elif event.action_type == "help":
                self.game_state = "HELP"
            elif event.action_type == "fire":
                self.game_state = "TARGETING"
                self.log("Select direction to attack...", (255, 255, 0))
            elif event.action_type == "wait":
                self.log("You wait...", (150, 150, 150))
            elif event.action_type.startswith("cast_"):
                skill_num = int(event.action_type.split("_")[1])
                self.handle_skill_cast(skill_num)

        elif self.game_state == "TARGETING":
            if event.action_type == "move":
                self.fire_weapon(event.dx, event.dy)
                self.game_state = "PLAYING"
            else:
                self.game_state = "PLAYING"
                self.log("Canceled.", (150, 150, 150))

        elif self.game_state == "HELP":
            if event.action_type:
                # Any key to close help
                self.game_state = "PLAYING"

        elif self.game_state == "INVENTORY":
            if event.action_type == "move":
                # Use move keys for menu navigation
                if event.dy > 0:
                    self.inventory_selection += 1
                elif event.dy < 0:
                    self.inventory_selection -= 1
            elif event.action_type == "quit":
                # Close inventory
                self.game_state = "PLAYING"
            elif event.action_type == "select":
                # Use/Equip item
                self.use_inventory_item()
            elif event.action_type in ("action_menu", "inventory"):
                # Close inventory
                self.game_state = "PLAYING"

        elif self.game_state == "STATS":
            if event.action_type == "move":
                if event.dy > 0:
                    self.inventory_selection = (self.inventory_selection + 1) % 4
                elif event.dy < 0:
                    self.inventory_selection = (self.inventory_selection - 1) % 4
            elif event.action_type in ("quit", "stats"):
                self.game_state = "PLAYING"
            elif event.action_type == "select":
                self.allocate_stat()

        elif self.game_state == "SHOPPING":
            if event.action_type in ("quit", "action_menu"):
                self.game_state = "PLAYING"
                self.log("You leave the shop.", (200, 200, 200))

    def handle_skill_cast(self, skill_num: int):
        """Handle casting of active skills."""
        from entities.components import Mana, Health, Position, Monster
        import random

        if self.player_id is None:
            return

        mana = self.entity_manager.get_component(self.player_id, Mana)
        health = self.entity_manager.get_component(self.player_id, Health)
        pos = self.entity_manager.get_component(self.player_id, Position)

        if not mana or not health or not pos:
            return

        if skill_num == 1:
            # Heal Skill (Cost 20 Mana, Heals 50 HP)
            cost = 20
            if mana.current < cost:
                self.log("Not enough mana for Heal!", (150, 150, 255))
                return

            mana.current -= cost
            heal_amount = 50
            health.current = min(health.maximum, health.current + heal_amount)
            self.log(f"Cast Heal! Restored {heal_amount} HP.", (100, 255, 100))
            self.vfx_system.add_floating_text(pos.x, pos.y, "+HP", (100, 255, 100))

        elif skill_num == 2:
            # Fireball (Cost 25 Mana, AoE damage around player)
            cost = 25
            if mana.current < cost:
                self.log("Not enough mana for Fireball!", (150, 150, 255))
                return

            mana.current -= cost
            self.log("Cast Fireball! Flames erupt!", (255, 100, 50))

            # Find monsters in radius 3
            radius = 3
            hit = False
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        tx, ty = pos.x + dx, pos.y + dy
                        monsters = self.entity_wrapper.get_monsters_at_position(tx, ty)
                        for mid in monsters:
                            # Direct damage
                            m_hp = self.entity_manager.get_component(mid, Health)
                            if m_hp:
                                dmg = 30
                                m_hp.current -= dmg
                                self.vfx_system.add_floating_text(
                                    tx, ty, str(dmg), (255, 100, 50)
                                )
                                self.vfx_system.add_hit_flash(
                                    mid, (255, 100, 0), duration=0.2
                                )
                                hit = True

                                # Check death
                                if m_hp.current <= 0:
                                    m_comp = self.entity_manager.get_component(
                                        mid, Monster
                                    )
                                    name = m_comp.name if m_comp else "Monster"
                                    self.log(f"{name} is incinerated!", (255, 50, 50))
                                    if m_comp:
                                        self.gain_xp(self.player_id, m_comp.xp_reward)
                                        # Random chance to drop item
                                        if random.random() < 0.2:
                                            drop_type = random.choice(
                                                [
                                                    "health_potion",
                                                    "sword",
                                                    "shield",
                                                    "bow",
                                                    "wand",
                                                ]
                                            )
                                            self.entity_wrapper.factory.create_item(
                                                tx, ty, drop_type
                                            )
                                            self.log(
                                                "Something dropped!", (255, 215, 0)
                                            )
                                    self.entity_manager.destroy_entity(mid)

            if not hit:
                self.log("The fireball hits nothing.", (150, 150, 150))

        elif skill_num == 3:
            # Teleport/Blink (Cost 30 Mana, random nearby free tile)
            cost = 30
            if mana.current < cost:
                self.log("Not enough mana for Blink!", (150, 150, 255))
                return

            radius = 5
            tries = 0
            while tries < 10:
                dx = random.randint(-radius, radius)
                dy = random.randint(-radius, radius)
                tx, ty = pos.x + dx, pos.y + dy

                # Check bounds and walkability
                if (
                    0 <= tx < self.game_map.width
                    and 0 <= ty < self.game_map.height
                    and self.game_map.is_walkable(tx, ty)
                ):

                    mana.current -= cost
                    self.vfx_system.add_floating_text(
                        pos.x, pos.y, "Poof!", (200, 200, 255)
                    )
                    pos.x = tx
                    pos.y = ty

                    # Notify ECS so spatial index updates
                    self.entity_manager.notify_component_change(
                        self.player_id, Position
                    )
                    self.update_fov()
                    self.log("You blink to a new location!", (200, 200, 255))
                    return
                tries += 1
            self.log("Blink failed, no safe spot found.", (150, 150, 150))

    def allocate_stat(self):
        """Allocate an attribute point."""
        from entities.components import Level, Combat, Health, Mana

        if self.player_id is None:
            return

        level_comp = self.entity_manager.get_component(self.player_id, Level)
        if not level_comp or level_comp.attribute_points <= 0:
            self.log("No attribute points to spend!", (150, 150, 150))
            return

        level_comp.attribute_points -= 1

        # 0: Str (Atk), 1: Dex (Def), 2: Vit (HP), 3: Int (MP)
        if self.inventory_selection == 0:
            combat = self.entity_manager.get_component(self.player_id, Combat)
            if combat:
                combat.attack_power += 2
                self.log("Strength Up! Attack +2", (255, 100, 100))
        elif self.inventory_selection == 1:
            combat = self.entity_manager.get_component(self.player_id, Combat)
            if combat:
                combat.defense += 1
                self.log("Dexterity Up! Defense +1", (100, 255, 100))
        elif self.inventory_selection == 2:
            health = self.entity_manager.get_component(self.player_id, Health)
            if health:
                health.maximum += 20
                health.current += 20
                self.log("Vitality Up! HP +20", (255, 50, 50))
        elif self.inventory_selection == 3:
            mana = self.entity_manager.get_component(self.player_id, Mana)
            if mana:
                mana.maximum += 15
                mana.current += 15
                self.log("Intelligence Up! MP +15", (50, 100, 255))

        # Keep menu open if points remain, otherwise close it?
        # Let's keep it open for convenience.
        if level_comp.attribute_points <= 0:
            self.game_state = "PLAYING"
            self.log("All points allocated.", (200, 200, 200))

    def check_for_attack(self) -> bool:
        """Check for adjacent monsters and attack if found."""
        from entities.components import Position, Monster

        if self.player_id is None:
            return False

        pos = self.entity_manager.get_component(self.player_id, Position)
        if not pos:
            return False

        # Check all neighbors (including diagonals)
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
            nx, ny = pos.x + dx, pos.y + dy

            # Check for monsters
            monsters = self.entity_wrapper.get_monsters_at_position(nx, ny)
            if monsters:
                # Attack the first valid target
                for mid in monsters:
                    monster = self.entity_manager.get_component(mid, Monster)
                    # Don't attack passive/static NPCs with Space (safety)
                    if monster and monster.ai_type not in ["passive", "static"]:
                        self.handle_combat(self.player_id, mid)
                        return True
        return False

    def check_for_shop(self) -> bool:
        """Check for adjacent shopkeeper and open shop if found."""
        from entities.components import Position, Shop

        if self.player_id is None:
            return False

        pos = self.entity_manager.get_component(self.player_id, Position)
        if not pos:
            return False

        # Check all neighbors (including diagonals)
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
            nx, ny = pos.x + dx, pos.y + dy

            # Check for entities at neighbor
            entities = self.entity_wrapper.get_monsters_at_position(nx, ny)
            for eid in entities:
                shop = self.entity_manager.get_component(eid, Shop)
                if shop:
                    self.game_state = "SHOPPING"
                    self.log(f"Welcome to {shop.shop_name}!", (255, 215, 0))
                    # Store current shop entity ID if we want to buy things later
                    self.current_shop_id = eid
                    return True
        return False

    def fire_weapon(self, dx: int, dy: int):
        """Fire weapon in a direction."""
        from entities.components import Equipment, Position

        if self.player_id is None:
            return

        # Get player info
        pos = self.entity_manager.get_component(self.player_id, Position)
        equip = self.entity_manager.get_component(self.player_id, Equipment)

        if not pos or not equip:
            return

        # Determine Range
        attack_range = 1

        if equip.weapon_type == "distance":
            attack_range = 4
        elif equip.weapon_type == "magic":
            attack_range = 5

        # Raycast
        target_found = False
        for r in range(1, attack_range + 1):
            tx = pos.x + (dx * r)
            ty = pos.y + (dy * r)

            # Check for walls
            if not self.game_map.is_walkable(tx, ty):
                self.log("Blocked by wall.", (150, 150, 150))
                break

            # Check for monsters
            monsters = self.entity_wrapper.get_monsters_at_position(tx, ty)
            if monsters:
                self.handle_combat(self.player_id, monsters[0])
                target_found = True

                # Visual effect (simple log for now, could be improved)
                # self.log(f"Projectile hit at distance {r}!", visual_color)
                break

        if not target_found:
            self.log(f"You attack the air with {equip.weapon_type}...", (100, 100, 100))

    def pickup_item(self):
        """Pick up an item at the player's location."""
        from entities.components import Position, Inventory, Item

        player_pos = self.entity_manager.get_component(self.player_id, Position)
        player_inv = self.entity_manager.get_component(self.player_id, Inventory)

        if not player_pos or not player_inv:
            return

        # Check for items at this position
        items_on_ground = self.entity_wrapper.get_items_at_position(
            player_pos.x, player_pos.y
        )

        if not items_on_ground:
            self.log("There is nothing here.", (150, 150, 150))
            return

        if len(player_inv.items) >= player_inv.capacity:
            self.log("Your inventory is full!", (255, 100, 100))
            return

        # Pick up the first item
        item_id = items_on_ground[0]
        item_comp = self.entity_manager.get_component(item_id, Item)

        if item_comp:
            # Remove Position component to "remove" it from the map
            self.entity_manager.remove_component(item_id, Position)
            # Add to inventory
            player_inv.items.append(item_id)
            self.log(f"You picked up {item_comp.name}.", (100, 255, 100))

    def use_inventory_item(self):
        """Use or equip the selected item."""
        from entities.components import (
            Inventory,
            Consumable,
            Health,
            Item,
            WeaponStats,
            ArmorStats,
            Equipment,
        )

        player_inv = self.entity_manager.get_component(self.player_id, Inventory)
        if not player_inv or not player_inv.items:
            return

        # Bounds check selection
        if self.inventory_selection < 0:
            self.inventory_selection = 0
        if self.inventory_selection >= len(player_inv.items):
            self.inventory_selection = len(player_inv.items) - 1

        item_id = player_inv.items[self.inventory_selection]
        item_comp = self.entity_manager.get_component(item_id, Item)

        # Check for Consumable
        consumable = self.entity_manager.get_component(item_id, Consumable)
        if consumable:
            if consumable.effect_type == "heal":
                health = self.entity_manager.get_component(self.player_id, Health)
                if health:
                    amount = min(consumable.amount, health.maximum - health.current)
                    health.current += amount
                    self.log(
                        f"Used {item_comp.name}. Healed {amount} HP.", (100, 255, 100)
                    )

                    # Remove from inventory and destroy
                    player_inv.items.pop(self.inventory_selection)
                    self.entity_manager.destroy_entity(item_id)

                    # Adjust selection
                    if self.inventory_selection >= len(player_inv.items):
                        self.inventory_selection = max(0, len(player_inv.items) - 1)
            return

        # Check for Weapon
        weapon_stats = self.entity_manager.get_component(item_id, WeaponStats)
        if weapon_stats:
            # Equip it
            equip = self.entity_manager.get_component(self.player_id, Equipment)
            if equip:
                # Unequip old weapon if any
                if equip.weapon is not None:
                    old_weapon_name = "Unknown"
                    old_item = self.entity_manager.get_component(equip.weapon, Item)
                    if old_item:
                        old_weapon_name = old_item.name

                    player_inv.items.append(equip.weapon)
                    self.log(f"Unequipped {old_weapon_name}.", (200, 200, 200))

                # Remove new weapon from inventory
                player_inv.items.pop(self.inventory_selection)

                # Equip new weapon
                equip.weapon = item_id
                equip.weapon_type = weapon_stats.weapon_type

                self.log(
                    f"Equipped {item_comp.name} ({weapon_stats.weapon_type}).",
                    (100, 200, 255),
                )

                # Adjust selection
                if self.inventory_selection >= len(player_inv.items):
                    self.inventory_selection = max(0, len(player_inv.items) - 1)
            return

        # Check for Armor
        armor_stats = self.entity_manager.get_component(item_id, ArmorStats)
        if armor_stats:
            # Equip it
            equip = self.entity_manager.get_component(self.player_id, Equipment)
            if equip:
                slot = armor_stats.slot
                
                # Get the current item in that slot
                old_item_id = getattr(equip, slot, None)
                
                # Unequip old armor if any
                if old_item_id is not None:
                    old_weapon_name = "Unknown"
                    old_item = self.entity_manager.get_component(old_item_id, Item)
                    if old_item:
                        old_weapon_name = old_item.name

                    player_inv.items.append(old_item_id)
                    self.log(f"Unequipped {old_weapon_name}.", (200, 200, 200))

                # Remove new armor from inventory
                player_inv.items.pop(self.inventory_selection)

                # Equip new armor in the specific slot
                setattr(equip, slot, item_id)

                self.log(
                    f"Equipped {item_comp.name} to {slot} (+{armor_stats.defense} Def).",
                    (100, 200, 255),
                )

                # Adjust selection
                if self.inventory_selection >= len(player_inv.items):
                    self.inventory_selection = max(0, len(player_inv.items) - 1)
            return

        self.log(f"You can't use {item_comp.name}.", (150, 150, 150))

    def swap_weapon(self):
        """Cycle through weapon types (Rucoy style: Melee -> Distance -> Magic)."""
        from entities.components import Equipment

        if self.player_id is None:
            return

        equip = self.entity_manager.get_component(self.player_id, Equipment)
        if equip:
            # Cycle types
            if equip.weapon_type == "melee":
                equip.weapon_type = "distance"
            elif equip.weapon_type == "distance":
                equip.weapon_type = "magic"
            else:
                equip.weapon_type = "melee"

            self.log(f"Switched to {equip.weapon_type.capitalize()}.", (255, 255, 0))

    def move_player(self, dx: int, dy: int):
        """Move the player by the given amount."""
        if self.player_id is None or self.game_map is None:
            return

        # Get the player's current position
        pos = self.entity_manager.get_component(self.player_id, Position)
        if not pos:
            return

        # Calculate new position
        new_x = pos.x + dx
        new_y = pos.y + dy

        # Clamp to world bounds
        new_x = max(0, min(new_x, self.game_map.width - 1))
        new_y = max(0, min(new_y, self.game_map.height - 1))

        # Check for monsters at new position
        monsters = self.entity_wrapper.get_monsters_at_position(new_x, new_y)
        if monsters:
            # Check AI type before attacking
            monster_id = monsters[0]
            from entities.components import Monster
            import random

            monster_comp = self.entity_manager.get_component(monster_id, Monster)

            if monster_comp and monster_comp.ai_type == "passive":
                # Give passive NPCs a purpose through interaction
                if monster_comp.name.lower() == "dog":
                    self.log("The Dog barks happily and wags its tail.", (200, 150, 100))
                    self.vfx_system.add_floating_text(new_x, new_y, "Woof!", (255, 255, 255))
                elif monster_comp.name.lower() == "citizen":
                    tips = [
                        "Stay on the paths to avoid danger.",
                        "I hear the oasis in the desert has strange ruins.",
                        "Watch out for the lava, it will melt you!",
                        "Ice is slippery, be careful!",
                        "Cacti hurt if you bump into them.",
                        "Shopkeepers pay good gold for loot."
                    ]
                    self.log(f"{monster_comp.name} says: '{random.choice(tips)}'", (150, 255, 150))
                    
                    # Small chance to drop a random minor item when talked to for the first time?
                    # Keep it simple: 5% chance to drop a potion
                    if random.random() < 0.05:
                        self.log(f"{monster_comp.name} drops something for you!", (255, 215, 0))
                        self.entity_wrapper.factory.create_item(new_x, new_y, "health_potion")
                else:
                    self.log(f"{monster_comp.name} looks at you curiously.", (100, 255, 100))
            else:
                # Attack the first monster found
                self.handle_combat(self.player_id, monster_id)
            return

        # Check if the new position is walkable
        if self.game_map.is_walkable(new_x, new_y):
            # Handle Ice sliding
            from world.map import TILE_ICE, TILE_LAVA, TILE_CACTUS, TILE_SNOW, TILE_SAND, TILE_ASH
            import random
            
            current_tile = self.game_map.tiles[pos.y, pos.x]
            target_tile = self.game_map.tiles[new_y, new_x]
            
            # Terrain Movement Penalties (Struggling to move)
            if current_tile in [TILE_SNOW, TILE_SAND, TILE_ASH]:
                if random.random() < 0.25: # 25% chance to lose footing/struggle
                    self.log(f"You struggle to move through the deep {self.game_map.tile_definitions[current_tile].name.lower()}...", (150, 150, 150))
                    return

            # Slippery Ice logic: keep sliding in the same direction until hitting a non-ice tile or wall
            if target_tile == TILE_ICE:
                self.log("You slip on the ice!", (150, 200, 255))
                slide_x, slide_y = new_x, new_y
                while True:
                    next_x, next_y = slide_x + dx, slide_y + dy
                    if self.game_map.is_walkable(next_x, next_y) and self.game_map.tiles[next_y, next_x] == TILE_ICE:
                        slide_x, slide_y = next_x, next_y
                    else:
                        break
                new_x, new_y = slide_x, slide_y
                target_tile = self.game_map.tiles[new_y, new_x]

            # Update the player's position
            pos.x = new_x
            pos.y = new_y
            self.entity_manager.notify_component_change(self.player_id, Position)

            # Environmental Hazards
            if target_tile == TILE_LAVA:
                from entities.components import Health
                health = self.entity_manager.get_component(self.player_id, Health)
                if health:
                    damage = max(5, int(health.maximum * 0.05))
                    health.current -= damage
                    self.log("You step in lava! It burns!", (255, 50, 50))
                    intensity = 2.0 + (damage / health.maximum) * 30.0
                    self.renderer.trigger_shake(min(15.0, intensity), 0.2)
                    if health.current <= 0:
                        self.log("You melted in the lava...", (255, 50, 50))
                        self.respawn_player()
                        return
            elif target_tile == TILE_CACTUS:
                from entities.components import Health
                health = self.entity_manager.get_component(self.player_id, Health)
                if health:
                    health.current -= 2
                    self.log("You prick yourself on a cactus.", (200, 255, 100))
                    self.renderer.trigger_shake(2.0, 0.1)
                    if health.current <= 0:
                        self.respawn_player()
                        return

            # Update FOV after movement
            self.update_fov()

            # Periodically update active region (e.g., every 10 steps)
            if (pos.x % 10 == 0) or (pos.y % 10 == 0):
                self.update_active_region()

    def handle_combat(self, attacker_id: int, defender_id: int, is_extra_attack: bool = False):
        """Handle combat with Rucoy-style skill logic."""
        from entities.components import (
            Combat,
            Health,
            Monster,
            Player,
            Skills,
            Equipment,
            WeaponStats,
            ArmorStats,
            Item,
            Name,
        )

        # Get components
        attacker_skills = self.entity_manager.get_component(attacker_id, Skills)
        attacker_equip = self.entity_manager.get_component(attacker_id, Equipment)

        defender_health = self.entity_manager.get_component(defender_id, Health)
        # defender_skills = self.entity_manager.get_component(defender_id, Skills)

        if not defender_health:
            return

        # Determine Attack Power based on Weapon Type
        attack_power = 1
        skill_used = "melee"
        weapon_affixes = []

        if attacker_skills:
            # Check equipped weapon stats
            if attacker_equip and attacker_equip.weapon:
                weapon_stats = self.entity_manager.get_component(
                    attacker_equip.weapon, WeaponStats
                )
                if weapon_stats:
                    attack_power += weapon_stats.attack_power
                    skill_used = weapon_stats.weapon_type

                # Check for item affixes if needed later (e.g., life steal)
                weapon_item = self.entity_manager.get_component(
                    attacker_equip.weapon, Item
                )
                if weapon_item and weapon_item.affixes:
                    weapon_affixes = weapon_item.affixes

            if skill_used == "melee":
                attack_power += attacker_skills.melee
            elif skill_used == "distance":
                attack_power += attacker_skills.distance
            elif skill_used == "magic":
                attack_power += attacker_skills.magic
        else:
            # Fallback for entities without Skills component (basic monsters)
            attacker_combat = self.entity_manager.get_component(attacker_id, Combat)
            if attacker_combat:
                attack_power = attacker_combat.attack_power

        # Apply Special Effects (Damage)
        if "Flaming" in weapon_affixes:
            attack_power += 5
            self.log("Flaming weapon burns!", (255, 100, 0))
        elif "Frozen" in weapon_affixes:
            attack_power += 3
            self.log("Frozen weapon chills!", (100, 200, 255))

        # Determine Defense (Stat based, not skill)
        defense_power = 0
        defender_combat = self.entity_manager.get_component(defender_id, Combat)
        if defender_combat:
            defense_power = defender_combat.defense

        # Add Armor Defense
        defender_equip = self.entity_manager.get_component(defender_id, Equipment)
        if defender_equip:
            # Check all armor slots
            for slot_name in ["head", "body", "legs", "shield"]:
                item_id = getattr(defender_equip, slot_name, None)
                if item_id is not None:
                    armor_stats = self.entity_manager.get_component(item_id, ArmorStats)
                    if armor_stats:
                        defense_power += armor_stats.defense

        # Calculate Damage
        import random

        # 1. Dodge Chance (Based on relative defense vs attack)
        # If defense is much higher than attack, higher chance to dodge
        dodge_chance = 0.05  # Base 5% dodge
        if defense_power > attack_power:
            dodge_chance += min(0.4, (defense_power - attack_power) * 0.02)
        
        if random.random() < dodge_chance:
            damage = 0
            self.log(f"{self.entity_manager.get_component(defender_id, Name).value if self.entity_manager.has_component(defender_id, Name) else 'Target'} dodged the attack!", (150, 150, 150))
            is_crit = False
        else:
            # 2. Critical Hit Chance
            crit_chance = 0.05 # Base 5% crit
            if attack_power > defense_power:
                crit_chance += min(0.3, (attack_power - defense_power) * 0.01)
            
            is_crit = random.random() < crit_chance

            # 3. Damage Calculation (Non-linear scaling)
            # Base damage is attack power
            base_dmg = attack_power
            
            # Mitigation is a percentage based on defense rather than flat subtraction
            # e.g., 10 defense = ~9% reduction, 50 defense = ~33% reduction
            mitigation = defense_power / (defense_power + 100)
            
            raw_dmg = base_dmg * (1.0 - mitigation)
            
            # Add variance (+/- 15%)
            variance = random.uniform(0.85, 1.15)
            final_dmg = raw_dmg * variance
            
            if is_crit:
                final_dmg *= 1.5 # 50% extra damage on crit
                
            damage = max(1, int(final_dmg)) # Always do at least 1 damage on a hit

        defender_health.current -= damage

        # Visual Effects
        def_pos = self.entity_manager.get_component(defender_id, Position)
        if def_pos:
            # Floating damage number
            vfx_color = (255, 50, 50) if damage > 0 else (150, 150, 150)
            if is_crit and damage > 0:
                vfx_color = (255, 215, 0) # Gold for crit
                
            text = str(damage) if damage > 0 else "Miss"
            if is_crit and damage > 0:
                text = f"{damage}!"
                
            self.vfx_system.add_floating_text(
                def_pos.x, def_pos.y, text, vfx_color
            )
            # Hit flash
            if damage > 0:
                self.vfx_system.add_hit_flash(
                    defender_id, (255, 255, 255), duration=0.1
                )

                # Screen shake if player was hit (Dynamic intensity)
                if self.entity_manager.has_component(defender_id, Player):
                    # Intensity based on % of max HP lost (Min 2.0, Max ~15.0)
                    # e.g. 10 dmg on 100 max HP = 10% = intensity 5
                    intensity = 2.0 + (damage / defender_health.maximum) * 30.0
                    # Cap intensity
                    intensity = min(15.0, intensity)
                    # Increase duration for big hits
                    duration = 0.1 + (damage / defender_health.maximum) * 0.5
                    self.renderer.trigger_shake(intensity, duration=min(0.6, duration))

        # Apply Vampiric Effect
        if "Vampiric" in weapon_affixes and damage > 0:
            attacker_health = self.entity_manager.get_component(attacker_id, Health)
            if attacker_health:
                heal = max(1, damage // 3)  # Heal 33% of damage
                attacker_health.current = min(
                    attacker_health.maximum, attacker_health.current + heal
                )
                self.log(f"Vampiric drain: +{heal} HP", (255, 50, 50))

        attacker_name = (
            "Player"
            if self.entity_manager.has_component(attacker_id, Player)
            else "Monster"
        )
        defender_name = (
            "Player"
            if self.entity_manager.has_component(defender_id, Player)
            else "Monster"
        )

        # Monster name override
        monster_comp = self.entity_manager.get_component(defender_id, Monster)
        if monster_comp:
            defender_name = monster_comp.name

        monster_attacker = self.entity_manager.get_component(attacker_id, Monster)
        if monster_attacker:
            attacker_name = monster_attacker.name

        self.log(
            f"{attacker_name} ({skill_used}) hits {defender_name} for {damage}!",
            (200, 200, 200),
        )

        # --- SKILL PROGRESSION ---
        # 1. Attacker gains XP in the weapon skill used
        if attacker_skills:
            xp_gain = 5  # Base XP per hit
            if skill_used == "melee":
                attacker_skills.melee_xp += xp_gain
                if attacker_skills.melee_xp >= attacker_skills.xp_for_next_level(
                    attacker_skills.melee
                ):
                    attacker_skills.melee += 1
                    attacker_skills.melee_xp = 0
                    self.log(
                        f"Melee Skill Up! {attacker_skills.melee}", (255, 100, 100)
                    )
            elif skill_used == "distance":
                attacker_skills.distance_xp += xp_gain
                if attacker_skills.distance_xp >= attacker_skills.xp_for_next_level(
                    attacker_skills.distance
                ):
                    attacker_skills.distance += 1
                    attacker_skills.distance_xp = 0
                    self.log(
                        f"Distance Skill Up! {attacker_skills.distance}",
                        (100, 255, 100),
                    )
            elif skill_used == "magic":
                attacker_skills.magic_xp += xp_gain
                if attacker_skills.magic_xp >= attacker_skills.xp_for_next_level(
                    attacker_skills.magic
                ):
                    attacker_skills.magic += 1
                    attacker_skills.magic_xp = 0
                    self.log(
                        f"Magic Skill Up! {attacker_skills.magic}", (100, 100, 255)
                    )

        # Check for death
        if defender_health.current <= 0:
            if self.entity_manager.has_component(defender_id, Player):
                # Player death
                self.respawn_player()
                return

            self.log(f"{defender_name} is defeated!", (255, 100, 100))

            # Handle Base Level XP gain (Mob Kill XP)
            if self.entity_manager.has_component(attacker_id, Player) and monster_comp:
                self.gain_xp(attacker_id, monster_comp.xp_reward)

                # Loot Drop Chance
                if random.random() < 0.2:  # 20% chance
                    pos = self.entity_manager.get_component(defender_id, Position)
                    if pos:
                        drop_type = random.choice(
                            ["health_potion", "sword", "shield", "bow", "wand"]
                        )
                        self.entity_wrapper.factory.create_item(pos.x, pos.y, drop_type)
                        self.log("Something dropped!", (255, 215, 0))

            # Destroy the entity
            self.entity_manager.destroy_entity(defender_id)

        # Extra attack from Swift affix
        elif "Swift" in weapon_affixes and not is_extra_attack and defender_health.current > 0:
            if random.random() < 0.3:  # 30% chance
                self.log("Swift weapon strikes again!", (255, 255, 0))
                self.handle_combat(attacker_id, defender_id, is_extra_attack=True)

    def gain_xp(self, entity_id: int, amount: int):
        """Give XP to an entity and handle leveling up."""
        from entities.components import Level, Combat, Health, Mana

        level_comp = self.entity_manager.get_component(entity_id, Level)
        if level_comp:
            level_comp.current_xp += amount
            self.log(f"Gained {amount} XP!", (100, 255, 100))

            # Check for level up
            if level_comp.current_xp >= level_comp.xp_to_next_level:
                level_comp.current_level += 1
                level_comp.current_xp -= level_comp.xp_to_next_level
                level_comp.xp_to_next_level = int(level_comp.xp_to_next_level * 1.5)
                level_comp.attribute_points += 5

                # Keep small automatic gains
                combat_comp = self.entity_manager.get_component(entity_id, Combat)
                health_comp = self.entity_manager.get_component(entity_id, Health)
                mana_comp = self.entity_manager.get_component(entity_id, Mana)

                if combat_comp:
                    combat_comp.defense += 1

                if health_comp:
                    health_comp.maximum += 10
                    health_comp.current = health_comp.maximum

                if mana_comp:
                    mana_comp.maximum += 5
                    mana_comp.current = mana_comp.maximum

                self.log(
                    f"LEVEL UP! Now Level {level_comp.current_level}!", (255, 215, 0)
                )
                self.log("HP+10, MP+5, Def+1, +5 Stat Points!", (255, 255, 0))
                self.log("Press 'k' to allocate points.", (200, 200, 255))

    def throttle_framerate(self):
        """Throttle the framerate to stabilize rendering."""
        current_time = time.time()
        elapsed = current_time - self.last_time
        sleep_time = self.frame_duration - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)

    def respawn_player(self):
        """Handle player death: lose XP and respawn at a safe location."""
        from entities.components import Position, Health, Mana, Level

        if self.player_id is None:
            return

        pos = self.entity_manager.get_component(self.player_id, Position)
        health = self.entity_manager.get_component(self.player_id, Health)
        mana = self.entity_manager.get_component(self.player_id, Mana)
        level = self.entity_manager.get_component(self.player_id, Level)

        if not pos or not health or not level:
            return

        # 1. Experience Loss (10% of XP required for next level)
        xp_loss = int(level.xp_to_next_level * 0.10)
        level.current_xp = max(0, level.current_xp - xp_loss)
        
        self.log(f"YOU DIED! Lost {xp_loss} XP.", (255, 50, 50))

        # 2. Teleport to Spawn Point (Town Center or persistent_world.player_start_pos)
        from world.persistent_world import get_persistent_world
        world = get_persistent_world()
        
        spawn_x, spawn_y = self.center_x, self.center_y # Default to world center
        if world and world.player_start_pos:
            spawn_x, spawn_y = world.player_start_pos
        elif hasattr(world, 'center_x'):
            spawn_x, spawn_y = world.center_x + 25, world.center_y + 25

        # Spiral search for a free spot near spawn
        found = False
        for r in range(0, 20):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    tx, ty = spawn_x + dx, spawn_y + dy
                    if self.game_map.is_walkable(tx, ty):
                        pos.x, pos.y = tx, ty
                        found = True
                        break
                if found:
                    break
            if found:
                break

        # 3. Restore Vitals
        health.current = health.maximum
        if mana:
            mana.current = mana.maximum

        # 4. Notify ECS and Update FOV
        self.entity_manager.notify_component_change(self.player_id, Position)
        self.update_fov()
        self.update_active_region()
        
        self.log("You have been resurrected in the town center.", (200, 200, 255))

    def quit(self):
        """Quit the game."""
        self.input_handler.restore_terminal()
        self.running = False
