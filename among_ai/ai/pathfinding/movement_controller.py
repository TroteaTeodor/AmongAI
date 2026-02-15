"""Converts pathfinding waypoints to per-frame velocity vectors with animation direction."""

import math
from among_ai.constants import PLAYER_SPEED


class MovementController:
    """Follows a path of waypoints, outputting velocity and direction each frame."""

    STUCK_FRAMES = 90       # If no progress in ~1.5s, skip waypoint
    STUCK_THRESHOLD = 3.0   # Minimum distance to consider "progress"

    def __init__(self):
        self.path = []           # List of (x, y) waypoints
        self.current_index = 0
        self.speed = PLAYER_SPEED
        self.arrival_threshold = 20.0  # Pixels to consider "arrived" at waypoint
        self.is_moving = False
        # Stuck detection
        self._last_pos = None
        self._stuck_counter = 0

    def set_path(self, path):
        """Set a new path to follow."""
        if path and len(path) > 0:
            self.path = path
            self.current_index = 0
            self.is_moving = True
            self._last_pos = None
            self._stuck_counter = 0
        else:
            self.path = []
            self.current_index = 0
            self.is_moving = False

    def stop(self):
        """Stop all movement."""
        self.path = []
        self.current_index = 0
        self.is_moving = False
        self._last_pos = None
        self._stuck_counter = 0

    def has_arrived(self) -> bool:
        """True if we've reached the end of the path."""
        return not self.is_moving or self.current_index >= len(self.path)

    def get_current_target(self):
        """Get current waypoint target, or None."""
        if self.current_index < len(self.path):
            return self.path[self.current_index]
        return None

    def _move_toward(self, target, current_pos):
        """Internal: compute velocity toward a target point from current position."""
        dx = target[0] - current_pos[0]
        dy = target[1] - current_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < 1.0:
            return (0, 0), None
            
        # Normalize and scale
        scale = self.speed / dist
        vx = dx * scale
        vy = dy * scale
        
        # Determine direction for animation
        direction = "down"
        if abs(vx) > abs(vy):
            if vx > 0: direction = "right"
            else: direction = "left"
        else:
            if vy > 0: direction = "down"
            else: direction = "up"
            
        return (vx, vy), direction

    def get_velocity_and_direction(self, current_pos) -> tuple:
        """Calculate velocity toward current waypoint."""
        if not self.is_moving or self.current_index >= len(self.path):
            return (0, 0), None

        target = self.path[self.current_index]
        return self._move_toward(target, current_pos)

    def update_position(self, current_pos):
        """Update position tracking, advance waypoints, and detect stuck bots.
        Call this each frame with the sprite's current (x, y) position."""
        if not self.is_moving or self.current_index >= len(self.path):
            return

        target = self.path[self.current_index]
        dx = target[0] - current_pos[0]
        dy = target[1] - current_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= self.arrival_threshold:
            self.current_index += 1
            self._stuck_counter = 0
            self._last_pos = None
            if self.current_index >= len(self.path):
                self.is_moving = False
            return

        # Stuck detection: if position hasn't changed much in STUCK_FRAMES, skip waypoint
        if self._last_pos is not None:
            move_dx = current_pos[0] - self._last_pos[0]
            move_dy = current_pos[1] - self._last_pos[1]
            moved_dist = math.sqrt(move_dx * move_dx + move_dy * move_dy)
            if moved_dist < self.STUCK_THRESHOLD:
                self._stuck_counter += 1
            else:
                self._stuck_counter = 0
        self._last_pos = current_pos

        if self._stuck_counter >= self.STUCK_FRAMES:
            # Skip to next waypoint (or stop if last one)
            print(f"[MovementController] Stuck at waypoint {self.current_index}, skipping")
            self.current_index += 1
            self._stuck_counter = 0
            self._last_pos = None
            if self.current_index >= len(self.path):
                self.is_moving = False
