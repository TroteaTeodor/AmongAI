"""Converts pathfinding waypoints to per-frame velocity vectors with animation direction."""

import math
from among_ai.constants import PLAYER_SPEED


class MovementController:
    """Follows a path of waypoints, outputting velocity and direction each frame."""

    def __init__(self):
        self.path = []           # List of (x, y) waypoints
        self.current_index = 0
        self.speed = PLAYER_SPEED
        self.arrival_threshold = 20.0  # Pixels to consider "arrived" at waypoint
        self.is_moving = False

    def set_path(self, path):
        """Set a new path to follow."""
        if path and len(path) > 0:
            self.path = path
            self.current_index = 0
            self.is_moving = True
        else:
            self.path = []
            self.current_index = 0
            self.is_moving = False

    def stop(self):
        """Stop all movement."""
        self.path = []
        self.current_index = 0
        self.is_moving = False

    def has_arrived(self) -> bool:
        """True if we've reached the end of the path."""
        return not self.is_moving or self.current_index >= len(self.path)

    def get_current_target(self):
        """Get current waypoint target, or None."""
        if self.current_index < len(self.path):
            return self.path[self.current_index]
        return None

    def get_velocity_and_direction(self) -> tuple:
        """Calculate velocity toward current waypoint.

        Returns:
            ((vx, vy), direction_str) where direction_str is 'left'/'right'/'up'/'down' or None.
        """
        if not self.is_moving or self.current_index >= len(self.path):
            return (0, 0), None

        target = self.path[self.current_index]
        return self._move_toward(target)

    def update_position(self, current_pos):
        """Update position tracking and advance waypoints.
        Call this each frame with the sprite's current (x, y) position."""
        if not self.is_moving or self.current_index >= len(self.path):
            return

        target = self.path[self.current_index]
        dx = target[0] - current_pos[0]
        dy = target[1] - current_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= self.arrival_threshold:
            self.current_index += 1
            if self.current_index >= len(self.path):
                self.is_moving = False

    def _move_toward(self, target):
        """Internal: compute velocity toward a target point.

        We don't know current position here - velocity is directional based on
        the path segment. The actual position update happens in the sprite."""
        # This is called to get direction; the sprite applies its own pos.
        # We store the target and let the sprite do: vel = direction * speed
        # Direction is based on the waypoint segment.
        return self._compute_direction(target)

    def _compute_direction(self, target):
        """Compute velocity components and animation direction from path context."""
        if self.current_index <= 0 and len(self.path) > 1:
            prev = self.path[0]
            nxt = self.path[min(1, len(self.path) - 1)]
        elif self.current_index > 0:
            prev = self.path[self.current_index - 1]
            nxt = target
        else:
            return (0, 0), None

        dx = nxt[0] - prev[0]
        dy = nxt[1] - prev[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 1.0:
            return (0, 0), None

        # Normalize and scale to PLAYER_SPEED
        nx = dx / dist
        ny = dy / dist
        vx = nx * self.speed
        vy = ny * self.speed

        # Determine animation direction (dominant axis)
        if abs(dx) >= abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"

        # Diagonal normalization
        if abs(vx) > 0 and abs(vy) > 0:
            factor = self.speed / math.sqrt(vx * vx + vy * vy)
            vx *= factor
            vy *= factor

        return (vx, vy), direction
