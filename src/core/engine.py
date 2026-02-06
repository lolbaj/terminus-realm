"""
Main game engine for the roguelike game.
"""

import time
from typing import Optional
from collections import deque
from rich.console import Console
from core.ecs import EntityManager, SystemManager
from config import CONFIG
from world.map import GameMap
from entities.entities import EntityManagerWrapper
from entities.components import Position
from ui.renderer import Renderer
from input.handler import InputHandler, InputEvent
from entities.spawn_system import SpawnSystem
from entities.ai_system import AISystem
from entities.boss_system import BossSystem
from world.fov import calculate_fov


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

        # Initialize game components
        self.game_map: Optional[GameMap] = None
        self.entity_wrapper = EntityManagerWrapper(self.entity_manager)
        self.player_id: Optional[int] = None

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
            self.entity_manager, self.entity_wrapper.factory
        )

        # Initialize AI system
        self.ai_system = AISystem(self.entity_manager)

        # Initialize boss system
        self.boss_system = BossSystem(self.entity_manager, self.entity_wrapper.factory)

        # AI Timer
        self.ai_timer = 0.0

        # Message Log
        self.message_log = deque(maxlen=5)
        self.log("Welcome to the dungeon!", (255, 255, 0))

        # Game State
        self.game_state = "PLAYING"  # PLAYING, INVENTORY
        self.inventory_selection = 0
        self.current_shop_id = None

    def update_fov(self):
        """Update the field of view based on player position."""
        if self.player_id is None or self.game_map is None:
            return

        pos = self.entity_manager.get_component(self.player_id, Position)
        if pos:
            fov_radius = 8  # Default radius
            fov_array = calculate_fov(self.game_map, pos.x, pos.y, fov_radius)
            self.game_map.update_fov(fov_array)

    def log(self, text: str, color: tuple = (255, 255, 255)):
        """Add a message to the log."""
        self.message_log.append((text, color))

    def run(self):
        """Run the main game loop."""
        print("Game engine started...")
        print("Controls: WASD/Arrows to move, Space for Menu, E to Select, P to quit")
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

                with open("game_debug.log", "a") as f:
                    f.write(
                        f"Loop Crash at iteration {loop_count}: {e}\n{traceback.format_exc()}\n"
                    )
                raise e

    def initialize_game(self):
        """Initialize game state."""
        print("Initializing game...")

        # Get the persistent world
        from world.persistent_world import get_persistent_world

        persistent_world = get_persistent_world()

        # Load the FULL world map for seamless scrolling
        self.game_map = persistent_world.get_full_game_map()
        print("Loaded Full World Map")

        # Start player
        if persistent_world.player_start_pos:
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

        # Handle any game-specific updates
        self.handle_updates(dt)

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
        # FOV update removed (Game is fully visible)

        # Get player position once for all updates
        player_pos = self.entity_manager.get_component(self.player_id, Position)

        # Update AI for monsters (Throttled)
        self.ai_timer += dt
        if self.ai_timer >= CONFIG.ai_move_delay:
            if player_pos:

                def combat_callback(attacker_id):
                    self.handle_combat(attacker_id, self.player_id)

                self.ai_system.update(self.game_map, player_pos, combat_callback)
            self.ai_timer = 0.0

        # Check for boss encounters
        if player_pos:
            boss_encounter = self.boss_system.check_for_boss_encounter(
                player_pos.x, player_pos.y
            )
            if boss_encounter:
                print(f"Danger approaches: {boss_encounter.name} is nearby!")
                # Optionally trigger the boss encounter here
                # self.boss_system.trigger_boss_encounter(boss_encounter)

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
            elif event.action_type == "fire":
                self.game_state = "TARGETING"
                self.log("Select direction to attack...", (255, 255, 0))

        elif self.game_state == "TARGETING":
            if event.action_type == "move":
                self.fire_weapon(event.dx, event.dy)
                self.game_state = "PLAYING"
            else:
                self.game_state = "PLAYING"
                self.log("Canceled.", (150, 150, 150))

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
            elif event.action_type == "action_menu" or event.action_type == "inventory":
                # Close inventory
                self.game_state = "PLAYING"

        elif self.game_state == "SHOPPING":
            if event.action_type == "quit" or event.action_type == "action_menu":
                self.game_state = "PLAYING"
                self.log("You leave the shop.", (200, 200, 200))

    def check_for_attack(self) -> bool:
        """Check for adjacent monsters and attack if found."""
        from entities.components import Position, Monster

        if self.player_id is None:
            return False

        pos = self.entity_manager.get_component(self.player_id, Position)
        if not pos:
            return False

        # Check all 4 neighbors
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
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

        # Check all 4 neighbors
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
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
                equip.weapon = item_comp.name
                equip.weapon_type = weapon_stats.weapon_type
                # Update combat stats? Not needed since damage is skill based + stats
                # But we might want to store the actual weapon ID later
                self.log(
                    f"Equipped {item_comp.name} ({weapon_stats.weapon_type}).",
                    (100, 200, 255),
                )
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

            monster_comp = self.entity_manager.get_component(monster_id, Monster)

            if monster_comp and monster_comp.ai_type == "passive":
                self.log(f"{monster_comp.name} looks at you.", (100, 255, 100))
            else:
                # Attack the first monster found
                self.handle_combat(self.player_id, monster_id)
            return

        # Check if the new position is walkable
        if self.game_map.is_walkable(new_x, new_y):
            # Update the player's position
            pos.x = new_x
            pos.y = new_y

            # Update FOV after movement
            self.update_fov()

            # Periodically update active region (e.g., every 10 steps)
            # Use a simple counter or just check occasionally
            # For simplicity, we can do a distance check or just call it:
            if (pos.x % 10 == 0) or (pos.y % 10 == 0):
                self.update_active_region()

    def handle_combat(self, attacker_id: int, defender_id: int):
        """Handle combat with Rucoy-style skill logic."""
        from entities.components import (
            Combat,
            Health,
            Monster,
            Player,
            Skills,
            Equipment,
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

        if attacker_skills:
            if attacker_equip:
                skill_used = attacker_equip.weapon_type

            if skill_used == "melee":
                attack_power = attacker_skills.melee
            elif skill_used == "distance":
                attack_power = attacker_skills.distance
            elif skill_used == "magic":
                attack_power = attacker_skills.magic
        else:
            # Fallback for entities without Skills component (basic monsters)
            attacker_combat = self.entity_manager.get_component(attacker_id, Combat)
            if attacker_combat:
                attack_power = attacker_combat.attack_power

        # Determine Defense (Stat based, not skill)
        defense_power = 0
        defender_combat = self.entity_manager.get_component(defender_id, Combat)
        if defender_combat:
            defense_power = defender_combat.defense

        # Calculate Damage
        # Rucoy logic: damage isn't just subtraction, but let's keep it simple for now
        # Random variance + skill diff
        import random

        variance = random.randint(-1, 2)
        damage = max(0, attack_power - (defense_power // 2) + variance)

        defender_health.current -= damage

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

    def gain_xp(self, entity_id: int, amount: int):
        """Give XP to an entity and handle leveling up."""
        from entities.components import Level, Combat, Health

        level_comp = self.entity_manager.get_component(entity_id, Level)
        if level_comp:
            level_comp.current_xp += amount
            self.log(f"Gained {amount} XP!", (100, 255, 100))

            # Check for level up
            if level_comp.current_xp >= level_comp.xp_to_next_level:
                level_comp.current_level += 1
                level_comp.current_xp -= level_comp.xp_to_next_level
                level_comp.xp_to_next_level = int(level_comp.xp_to_next_level * 1.5)

                # Increase stats
                combat_comp = self.entity_manager.get_component(entity_id, Combat)
                health_comp = self.entity_manager.get_component(entity_id, Health)

                if combat_comp:
                    combat_comp.attack_power += 2
                    combat_comp.defense += 1

                if health_comp:
                    health_comp.maximum += 20
                    health_comp.current = health_comp.maximum  # Full heal on level up

                self.log(
                    f"LEVEL UP! Now Level {level_comp.current_level}!", (255, 215, 0)
                )
                self.log("HP+20, Atk+2, Def+1", (255, 255, 0))

    def throttle_framerate(self):
        """Throttle the framerate to stabilize rendering."""
        current_time = time.time()
        elapsed = current_time - self.last_time
        sleep_time = self.frame_duration - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)

    def quit(self):
        """Quit the game."""
        self.input_handler.restore_terminal()
        self.running = False
