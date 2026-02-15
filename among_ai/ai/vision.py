"""Simulated field-of-view: determines what an AI player can see."""

import math
import time
from among_ai.ai.interfaces import MemoryEvent


class Vision:
    """Simulates what an AI player can see based on distance."""

    def __init__(self, owner_colour: str, normal_radius: float = 500,
                 dark_radius: float = 150):
        self.owner_colour = owner_colour
        self.normal_radius = normal_radius
        self.dark_radius = dark_radius

    def get_vision_radius(self, lights_sabotaged: bool) -> float:
        return self.dark_radius if lights_sabotaged else self.normal_radius

    def get_visible_players(self, my_pos, all_players, lights_sabotaged: bool) -> list:
        """Return list of player data dicts that are within vision range."""
        radius = self.get_vision_radius(lights_sabotaged)
        visible = []
        mx, my = my_pos
        for player in all_players:
            if player.get("colour") == self.owner_colour:
                continue
            if not player.get("alive", True):
                continue
            px, py = player["position"]
            dist = math.sqrt((mx - px) ** 2 + (my - py) ** 2)
            if dist <= radius:
                visible.append({**player, "distance": dist})
        return visible

    def get_visible_bodies(self, my_pos, dead_players, lights_sabotaged: bool) -> list:
        """Return dead bodies within vision range."""
        radius = self.get_vision_radius(lights_sabotaged)
        visible = []
        mx, my = my_pos
        for body in dead_players:
            if body.get("reported", False):
                continue
            px, py = body["position"]
            dist = math.sqrt((mx - px) ** 2 + (my - py) ** 2)
            if dist <= radius:
                visible.append({**body, "distance": dist})
        return visible

    def scan_and_record(self, my_pos, all_players, dead_players,
                        lights_sabotaged: bool, memory, pathfinder) -> tuple:
        """Scan surroundings and record events to memory.

        Returns (visible_players, visible_bodies) for game state snapshot.
        """
        visible_players = self.get_visible_players(my_pos, all_players, lights_sabotaged)
        visible_bodies = self.get_visible_bodies(my_pos, dead_players, lights_sabotaged)

        now = time.time()
        my_room = pathfinder.get_room_at(my_pos) if pathfinder else "Unknown"

        # Record player sightings
        for vp in visible_players:
            room = pathfinder.get_room_at(vp["position"]) if pathfinder else "Unknown"
            memory.record_event(MemoryEvent(
                timestamp=now,
                event_type="saw_player",
                location=room,
                actors=[vp["colour"]],
                description=f"Saw {vp['colour']} in {room} ({int(vp['distance'])} units away)",
                importance=0.3,
            ))

        # Record body sightings
        for body in visible_bodies:
            room = pathfinder.get_room_at(body["position"]) if pathfinder else "Unknown"
            memory.record_event(MemoryEvent(
                timestamp=now,
                event_type="saw_body",
                location=room,
                actors=[body["colour"]],
                description=f"Found {body['colour']}'s dead body in {room}!",
                importance=1.0,
            ))

        return visible_players, visible_bodies
