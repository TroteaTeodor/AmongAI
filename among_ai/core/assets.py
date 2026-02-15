"""Centralized, dictionary-based asset loading. Replaces the massive if/elif chains in settings.py."""

import pygame
from os import path
from among_ai.constants import ALL_COLOURS, PLAYER_SPRITE_SIZE


class AssetManager:
    """Loads and provides access to all game sprites and images via dict lookups."""

    def __init__(self):
        self._player_sprites = {}   # colour -> {direction -> [frames]}
        self._dead_sprites = {}     # colour -> Surface
        self._ghost_sprites = {}    # colour -> {left: Surface, right: Surface}
        self._meeting_imgs = {}     # colour -> Surface
        self._meeting_report_imgs = {}  # colour -> Surface
        self._eject_imgs = {}       # colour -> Surface (right walk frame 9)
        self._loaded = False

    def load_all(self):
        """Load all player sprites for all colours."""
        if self._loaded:
            return
        for colour in ALL_COLOURS:
            self._load_colour(colour)
        self._loaded = True

    def _load_colour(self, colour: str):
        """Load all sprites for a single colour."""
        lower = colour.lower()
        base_path = f'Assets/Images/Player/{colour}'
        w, h = PLAYER_SPRITE_SIZE

        # Determine if this colour has full animation (17+ frames) or single frames
        full_anim_colours = {"Red", "Blue", "Orange", "Yellow", "Green"}
        has_full_anim = colour in full_anim_colours

        directions = {}
        for direction in ["left", "right", "up", "down"]:
            frames = []
            if has_full_anim:
                count = 18 if direction == "down" else 17
                for i in range(1, count + 1):
                    img = pygame.image.load(
                        f'{base_path}/{lower}_{direction}_walk/step{i}.png'
                    )
                    img = pygame.transform.smoothscale(img, (w, h))
                    frames.append(img)
            else:
                img = pygame.image.load(
                    f'{base_path}/{lower}_{direction}_walk/step1.png'
                )
                img = pygame.transform.smoothscale(img, (w, h))
                frames.append(img)
            directions[direction] = frames
        self._player_sprites[colour] = directions

        # Dead sprite
        dead_img = pygame.image.load(f'Assets/Images/Player/Dead/Dead{lower}.png')
        self._dead_sprites[colour] = dead_img

        # Ghost sprites (only for full-anim colours)
        if has_full_anim:
            ghost_left = pygame.image.load(
                f'{base_path}/{lower}_ghost/step1_left.png'
            )
            ghost_left = pygame.transform.smoothscale(ghost_left, (w, h))
            ghost_right = pygame.image.load(
                f'{base_path}/{lower}_ghost/step1_right.png'
            )
            ghost_right = pygame.transform.smoothscale(ghost_right, (w, h))
        else:
            # Use the single frame as ghost placeholder
            ghost_left = directions["left"][0].copy()
            ghost_left.set_alpha(100)
            ghost_right = directions["right"][0].copy()
            ghost_right.set_alpha(100)
        self._ghost_sprites[colour] = {"left": ghost_left, "right": ghost_right}

        # Emergency meeting images
        try:
            meeting_img = pygame.image.load(
                f'Assets/Images/Alerts/emergency_meeting_{lower}.png'
            )
            self._meeting_imgs[colour] = meeting_img
        except FileNotFoundError:
            self._meeting_imgs[colour] = None

        try:
            report_img = pygame.image.load(
                f'Assets/Images/Alerts/report_dead_body_{lower}.png'
            )
            self._meeting_report_imgs[colour] = report_img
        except FileNotFoundError:
            self._meeting_report_imgs[colour] = None

        # Eject image: right walk frame index 9 (or last available)
        right_frames = directions["right"]
        eject_idx = min(9, len(right_frames) - 1)
        self._eject_imgs[colour] = right_frames[eject_idx]

    def get_walk_frames(self, colour: str, direction: str) -> list:
        """Get animation frames for a colour+direction. direction: left/right/up/down."""
        return self._player_sprites[colour][direction]

    def get_default_image(self, colour: str) -> pygame.Surface:
        """Get the default (standing) image for a colour."""
        return self._player_sprites[colour]["down"][0]

    def get_dead_image(self, colour: str) -> pygame.Surface:
        """Get the dead body sprite."""
        return self._dead_sprites[colour]

    def get_ghost_images(self, colour: str) -> dict:
        """Get ghost sprites: {left: Surface, right: Surface}."""
        return self._ghost_sprites[colour]

    def get_meeting_image(self, colour: str) -> pygame.Surface:
        """Get emergency meeting alert image for a colour."""
        return self._meeting_imgs.get(colour)

    def get_meeting_report_image(self, colour: str) -> pygame.Surface:
        """Get dead body report alert image for a colour."""
        return self._meeting_report_imgs.get(colour)

    def get_eject_image(self, colour: str) -> pygame.Surface:
        """Get the ejection image for a colour."""
        return self._eject_imgs.get(colour)

    def get_all_walk_data(self, colour: str) -> dict:
        """Get full walk data dict for a colour: {direction: [frames]}."""
        return self._player_sprites[colour]


# Singleton instance
_asset_manager = None


def get_asset_manager() -> AssetManager:
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager()
    return _asset_manager
