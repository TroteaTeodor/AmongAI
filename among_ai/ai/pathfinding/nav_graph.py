"""Navigation graph built from TMX collision data for AI pathfinding."""

import math
from among_ai.constants import (
    ROOMS, VENT_LOCATIONS, TASK_DEFINITIONS, TILESIZE, COLLISION_OBJECT_NAMES,
)
from among_ai.ai.interfaces import IPathfinder


class NavGraph(IPathfinder):
    """Walkability grid + room labeling built from the TMX tilemap."""

    def __init__(self):
        self.grid = None         # 2D list: True=walkable, False=blocked
        self.grid_width = 0
        self.grid_height = 0
        self.cell_size = TILESIZE  # 32px cells
        self.map_width = 0
        self.map_height = 0

    def build_from_tilemap(self, tiled_map):
        """Build the walkability grid from a TiledMap's collision objects."""
        self.map_width = tiled_map.width
        self.map_height = tiled_map.height
        self.grid_width = self.map_width // self.cell_size + 1
        self.grid_height = self.map_height // self.cell_size + 1

        # Start with all cells walkable
        self.grid = [[True] * self.grid_width for _ in range(self.grid_height)]

        # Mark blocked cells from collision objects
        for obj in tiled_map.get_collision_objects():
            if obj['name'] in COLLISION_OBJECT_NAMES or obj['name'] is None:
                self._mark_blocked(obj['x'], obj['y'], obj['width'], obj['height'])

    def _mark_blocked(self, x, y, w, h):
        """Mark grid cells covered by a collision rectangle as blocked.
        Inflates obstacles by half player width to avoid clipping."""
        # Player is 64x86 (PLAYER_SPRITE_SIZE). Half width is 32.
        # We need to inflate obstacles but 60 was too aggressive (blocked corridors).
        # reducing to 40 to be safe but allow movement.
        padding = 40
        
        # Calculate grid bounds with padding
        gx1 = max(0, int((x - padding) / self.cell_size))
        gy1 = max(0, int((y - padding) / self.cell_size))
        gx2 = min(self.grid_width - 1, int((x + w + padding) / self.cell_size))
        gy2 = min(self.grid_height - 1, int((y + h + padding) / self.cell_size))
        
        for gy in range(gy1, gy2 + 1):
            for gx in range(gx1, gx2 + 1):
                self.grid[gy][gx] = False

    def _world_to_grid(self, x, y):
        gx = int(x / self.cell_size)
        gy = int(y / self.cell_size)
        gx = max(0, min(self.grid_width - 1, gx))
        gy = max(0, min(self.grid_height - 1, gy))
        return gx, gy

    def _grid_to_world(self, gx, gy):
        return (gx * self.cell_size + self.cell_size // 2,
                gy * self.cell_size + self.cell_size // 2)

    def _is_walkable(self, gx, gy):
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            return self.grid[gy][gx]
        return False

    def find_path(self, start, goal):
        """A* pathfinding from start to goal world coordinates."""
        from among_ai.ai.pathfinding.astar import astar_search

        sx, sy = self._world_to_grid(start[0], start[1])
        gx, gy = self._world_to_grid(goal[0], goal[1])

        # If goal is blocked, find nearest walkable cell
        if not self._is_walkable(gx, gy):
            gx, gy = self._find_nearest_walkable(gx, gy)
            if gx is None:
                return None

        if not self._is_walkable(sx, sy):
            sx, sy = self._find_nearest_walkable(sx, sy)
            if sx is None:
                return None

        grid_path = astar_search(
            self.grid, self.grid_width, self.grid_height,
            (sx, sy), (gx, gy)
        )

        if grid_path is None:
            return None

        # Convert grid path to world coordinates and smooth
        world_path = [self._grid_to_world(p[0], p[1]) for p in grid_path]
        return self._smooth_path(world_path)

    def _find_nearest_walkable(self, gx, gy, max_radius=10):
        """Find the nearest walkable cell to a blocked position."""
        for r in range(1, max_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) == r or abs(dy) == r:
                        nx, ny = gx + dx, gy + dy
                        if self._is_walkable(nx, ny):
                            return nx, ny
        return None, None

    def _smooth_path(self, path):
        """Remove redundant waypoints on straight lines."""
        if len(path) <= 2:
            return path
        smoothed = [path[0]]
        for i in range(1, len(path) - 1):
            prev = smoothed[-1]
            curr = path[i]
            nxt = path[i + 1]
            # Keep point if direction changes
            dx1 = curr[0] - prev[0]
            dy1 = curr[1] - prev[1]
            dx2 = nxt[0] - curr[0]
            dy2 = nxt[1] - curr[1]
            if (dx1, dy1) != (dx2, dy2):
                smoothed.append(curr)
        smoothed.append(path[-1])
        return smoothed

    def get_room_at(self, position):
        """Determine which room a position is in based on nearest room center."""
        min_dist = float('inf')
        nearest_room = "Unknown"
        px, py = position
        for room_name, (rx, ry) in ROOMS.items():
            dist = math.sqrt((px - rx) ** 2 + (py - ry) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest_room = room_name
        return nearest_room

    def get_room_center(self, room_name):
        return ROOMS.get(room_name, (3277, 658))  # Default to Cafeteria

    def get_nearest_vent(self, position):
        min_dist = float('inf')
        nearest = None
        px, py = position
        for vx, vy in VENT_LOCATIONS:
            dist = math.sqrt((px - vx) ** 2 + (py - vy) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest = (vx, vy)
        return nearest

    def get_nearest_task_location(self, position, available_tasks):
        min_dist = float('inf')
        nearest = None
        px, py = position
        for task_name in available_tasks:
            if task_name not in TASK_DEFINITIONS:
                continue
            loc = TASK_DEFINITIONS[task_name]["location"]
            dist = math.sqrt((px - loc[0]) ** 2 + (py - loc[1]) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest = (task_name, loc)
        return nearest

    def distance_between(self, a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
