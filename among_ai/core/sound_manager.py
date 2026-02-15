"""Sound management: loads and plays effect/ambient/footstep sounds."""

import os
import random
import pygame as pg
from among_ai.constants import (
    EFFECT_SOUNDS, AMBIENT_SOUNDS, FOOTSTEP_SOUNDS, ROOMS, ROOM_AMBIENT_RADII,
)


class SoundManager:
    """Centralized sound loading and ambient sound management."""

    def __init__(self, sound_folder: str):
        self.sound_folder = sound_folder
        self.effect_sounds: dict[str, pg.mixer.Sound] = {}
        self.ambient_sounds: dict[str, pg.mixer.Sound] = {}
        self.foot_sounds: list[pg.mixer.Sound] = []
        self._ambient_playing: dict[str, bool] = {}

    def load_all(self):
        """Load all sounds from disk."""
        pg.mixer.init()

        # Effect sounds
        for name, rel_path in EFFECT_SOUNDS.items():
            full = os.path.join(self.sound_folder, rel_path)
            if os.path.exists(full):
                self.effect_sounds[name] = pg.mixer.Sound(full)

        # Ambient sounds
        for name, rel_path in AMBIENT_SOUNDS.items():
            full = os.path.join(self.sound_folder, rel_path)
            if os.path.exists(full):
                self.ambient_sounds[name] = pg.mixer.Sound(full)
                self._ambient_playing[name] = False

        # Footstep sounds
        for rel_path in FOOTSTEP_SOUNDS:
            full = os.path.join(self.sound_folder, rel_path)
            if os.path.exists(full):
                self.foot_sounds.append(pg.mixer.Sound(full))

    def play_effect(self, name: str):
        if name in self.effect_sounds:
            self.effect_sounds[name].play()

    def play_footstep(self):
        if self.foot_sounds:
            random.choice(self.foot_sounds).play()

    def stop_all(self):
        """Stop all sounds."""
        pg.mixer.stop()
        for name in self._ambient_playing:
            self._ambient_playing[name] = False

    def update_ambient(self, player_x: float, player_y: float):
        """Update ambient sounds based on player position."""
        player_pos = pg.Vector2(player_x, player_y)

        # Room name -> ambient sound key mapping
        room_sound_map = {
            "Cafeteria": "cafeteria",
            "Medbay": "medbay_room",
            "Security": "security_room",
            "Reactor": "reactor_room",
            "Upper Engine": "u_engine_room",
            "Lower Engine": "l_engine_room",
            "Electrical": "electrical_room",
            "Storage": "storage_room",
            "Admin": "admin_room",
            "Communications": "comms3",
            "Oxygen": "oxygen_room",
            "Navigation": "cockpit",
            "Weapons": "weapons",
        }

        for room_name, center in ROOMS.items():
            sound_key = room_sound_map.get(room_name)
            if not sound_key or sound_key not in self.ambient_sounds:
                continue

            radius = ROOM_AMBIENT_RADII.get(room_name, 400)
            dist = player_pos.distance_to(pg.Vector2(center))

            if dist <= radius:
                if not self._ambient_playing.get(sound_key, False):
                    self.ambient_sounds[sound_key].play(-1, -1, 500)
                    self._ambient_playing[sound_key] = True
            else:
                if self._ambient_playing.get(sound_key, False):
                    self.ambient_sounds[sound_key].fadeout(1000)
                    self._ambient_playing[sound_key] = False
