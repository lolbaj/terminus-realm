import numpy as np
from typing import Tuple, Optional
from data.loader import DATA_LOADER

# Tile types represented as integers for memory efficiency
TILE_FLOOR = 0
TILE_WALL = 1
TILE_DOOR = 2
TILE_WATER = 3
TILE_GRASS = 4
TILE_TREE = 5
TILE_STAIRS_UP = 6
TILE_STAIRS_DOWN = 7
TILE_SAND = 8
TILE_PAVEMENT = 9
TILE_SNOW = 10
TILE_LAVA = 11
TILE_ASH = 12
TILE_CACTUS = 13
TILE_ICE = 14


class Tile:
    """Represents a single tile in the game world."""

    __slots__ = ["tile_type", "walkable", "transparent", "char", "fg_color", "bg_color"]

    def __init__(
        self,
        tile_type: int,
        walkable: bool,
        transparent: bool,
        char: str,
        fg_color: Tuple[int, int, int],
        bg_color: Optional[Tuple[int, int, int]] = None,
    ):
        self.tile_type = tile_type
        self.walkable = walkable
        self.transparent = transparent
        self.char = char
        self.fg_color = fg_color
        self.bg_color = bg_color


class GameMap:
    """Represents the game map."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        # Use numpy array for efficient storage and operations
        self.tiles = np.full((height, width), TILE_WALL, dtype=np.uint8)
        # Visibility arrays - Default to fully visible (No Fog of War)
        self.explored = np.full((height, width), True, dtype=bool)
        self.visible = np.full((height, width), True, dtype=bool)

        # Start position (x, y) if defined in map data
        self.start_position: Optional[Tuple[int, int]] = None

        # Load tile definitions from data
        self.tile_definitions = {}
        tiles_data = DATA_LOADER.load_json("tiles")

        for key, data in tiles_data.items():
            tile_id = int(key)
            self.tile_definitions[tile_id] = Tile(
                tile_type=tile_id,
                walkable=data.get("walkable", False),
                transparent=data.get("transparent", False),
                char=data.get("char", "??"),
                fg_color=tuple(data.get("fg", [255, 255, 255])),
                bg_color=tuple(data.get("bg", [0, 0, 0])) if data.get("bg") else None,
            )

    def create_room(self, x1: int, y1: int, x2: int, y2: int):
        """Create a rectangular room in the map."""
        for x in range(x1 + 1, x2):
            for y in range(y1 + 1, y2):
                self.tiles[y, x] = TILE_FLOOR

    def create_h_tunnel(self, x1: int, x2: int, y: int):
        """Create a horizontal tunnel."""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y, x] = TILE_FLOOR

    def create_v_tunnel(self, y1: int, y2: int, x: int):
        """Create a vertical tunnel."""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y, x] = TILE_FLOOR

    def place_entities(self, entity_manager):
        """Place entities on the map."""
        # This will be implemented in later phases
        pass

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable."""
        if 0 <= x < self.width and 0 <= y < self.height:
            tile_def = self.tile_definitions[self.tiles[y, x]]
            return tile_def.walkable
        return False

    def is_transparent(self, x: int, y: int) -> bool:
        """Check if a tile is transparent."""
        if 0 <= x < self.width and 0 <= y < self.height:
            tile_def = self.tile_definitions[self.tiles[y, x]]
            return tile_def.transparent
        return False

    def get_tile_char(self, x: int, y: int, visible: bool = True) -> str:
        """Get the character representation of a tile."""
        if 0 <= x < self.width and 0 <= y < self.height:
            tile_type = self.tiles[y, x]
            tile_def = self.tile_definitions[tile_type]

            # Procedural texture for grass
            if tile_type == TILE_GRASS:
                # Cleaner look for Rucoy style - mostly solid, occasional detail
                if (x * 7 + y * 13) % 11 == 0:
                    char = ".."  # faint detail
                else:
                    char = tile_def.char
            else:
                char = tile_def.char

            # If the tile is not visible but has been explored, show it differently
            if not visible and self.explored[y, x]:
                # ... rest of the logic
                if char == ". " or char == "· ":
                    return ": "
                elif char == "🪨":
                    return "▒▒"
                else:
                    return char
            else:
                return char
        return "  "

    def get_tile_fg_color(
        self, x: int, y: int, visible: bool = True
    ) -> Tuple[int, int, int]:
        """Get the foreground color of a tile."""
        if 0 <= x < self.width and 0 <= y < self.height:
            tile_def = self.tile_definitions[self.tiles[y, x]]

            # If the tile is not visible but has been explored, show it with dimmer colors
            if not visible and self.explored[y, x]:
                # Dim the color by reducing brightness
                r, g, b = tile_def.fg_color
                return (max(0, r - 100), max(0, g - 100), max(0, b - 100))
            else:
                return tile_def.fg_color
        return (0, 0, 0)

    def update_fov(self, fov_array: np.ndarray):
        """Update the visibility and exploration status based on FOV."""
        # FOV disabled: Keep everything visible
        pass

    def generate_dungeon_rooms(
        self, max_rooms: int = 10, min_size: int = 4, max_size: int = 8
    ):
        """Generate a simple dungeon with rooms connected by tunnels."""
        rooms = []

        for r in range(max_rooms):
            # Random width and height
            w = np.random.randint(min_size, max_size)
            h = np.random.randint(min_size, max_size)
            # Random position without going out of bounds
            x = np.random.randint(0, self.width - w - 1)
            y = np.random.randint(0, self.height - h - 1)

            # Create a new room
            new_room = (x, y, x + w, y + h)

            # Check if this room intersects with any existing room
            intersects = False
            for other_room in rooms:
                if (
                    new_room[0] < other_room[2]
                    and new_room[2] > other_room[0]
                    and new_room[1] < other_room[3]
                    and new_room[3] > other_room[1]
                ):
                    intersects = True
                    break

            if not intersects:
                # This means there are no intersections, so this room is valid
                self.create_room(*new_room)

                # Center coordinates of new room
                center_x = (new_room[0] + new_room[2]) // 2
                center_y = (new_room[1] + new_room[3]) // 2

                if len(rooms) == 0:
                    # This is the first room, where the player starts
                    first_room_center_x = center_x
                    first_room_center_y = center_y
                else:
                    # Connect to the previous room with an L-shaped tunnel
                    prev_center_x = (rooms[-1][0] + rooms[-1][2]) // 2
                    prev_center_y = (rooms[-1][1] + rooms[-1][3]) // 2

                    # Create L-shaped tunnel
                    self.create_h_tunnel(prev_center_x, center_x, prev_center_y)
                    self.create_v_tunnel(prev_center_y, center_y, center_x)

                # Append the new room to the list
                rooms.append(new_room)

        return rooms, (first_room_center_x, first_room_center_y)

    def load_from_string(self, map_data: list[str]):
        """Load map data from a list of strings."""
        # Legend mapping
        char_map = {
            ".": TILE_FLOOR,
            "#": TILE_WALL,
            "+": TILE_DOOR,
            "~": TILE_WATER,
            ",": TILE_GRASS,
            "T": TILE_TREE,
            ">": TILE_STAIRS_DOWN,
            "<": TILE_STAIRS_UP,
            "S": TILE_SAND,
            "P": TILE_PAVEMENT,
            "*": TILE_SNOW,
            "=": TILE_LAVA,
            "A": TILE_ASH,
            "C": TILE_CACTUS,
            "I": TILE_ICE,
            # Box drawing walls
            "║": TILE_WALL,
            "═": TILE_WALL,
            "╚": TILE_WALL,
            "╔": TILE_WALL,
            "╗": TILE_WALL,
            "╝": TILE_WALL,
            "╠": TILE_WALL,
            "╦": TILE_WALL,
            "╣": TILE_WALL,
            "╩": TILE_WALL,
            "╬": TILE_WALL,
            "█": TILE_WALL,
        }

        for y, row in enumerate(map_data):
            if y >= self.height:
                break
            for x, char in enumerate(row):
                if x >= self.width:
                    break

                if char == "@":
                    self.start_position = (x, y)
                    self.tiles[y, x] = TILE_FLOOR
                    continue

                # Default to floor for spaces or unknown chars
                tile_type = char_map.get(char, TILE_FLOOR)
                self.tiles[y, x] = tile_type


def create_map_from_string(map_data: list[str]) -> GameMap:
    """Create a GameMap from a string definition."""
    if not map_data:
        return GameMap(40, 25)

    height = len(map_data)
    width = len(map_data[0])

    game_map = GameMap(width, height)
    game_map.load_from_string(map_data)
    return game_map


def create_basic_map(width: int = 40, height: int = 25) -> GameMap:
    """Create a basic map with some rooms and corridors."""
    game_map = GameMap(width, height)
    game_map.generate_dungeon_rooms(max_rooms=8, min_size=3, max_size=6)
    return game_map
