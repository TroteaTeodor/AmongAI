"""Reusable Pygame UI widgets for the Among AI menu system."""

import os
import pygame as pg
from among_ai.constants import FONT, PLAYER_DISPLAY_COLORS, WHITE, BLACK

# Theme colors
ACCENT_RED = (200, 30, 30)
PANEL_BG = (20, 20, 35, 200)
SLIDER_TRACK = (40, 40, 55)
SLIDER_FILL = (180, 30, 30)
KNOB_COLOR = (240, 240, 240)

MENU_IMG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Assets", "Images", "menu",
)
SOUND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Assets", "Sounds",
)


def _load_font(size: int):
    try:
        return pg.font.Font(FONT, size)
    except Exception:
        return pg.font.SysFont("arial", size)


def _load_image(name: str):
    path = os.path.join(MENU_IMG_DIR, name)
    if os.path.exists(path):
        return pg.image.load(path).convert_alpha()
    return None


def _load_sound(relpath: str):
    full = os.path.join(SOUND_DIR, relpath)
    if os.path.exists(full):
        try:
            return pg.mixer.Sound(full)
        except Exception:
            return None
    return None


# Shared sounds (loaded lazily)
_sounds = {}


def _get_sound(key: str):
    if key not in _sounds:
        if key == "hover":
            _sounds[key] = _load_sound("UI/select.wav")
        elif key == "click":
            _sounds[key] = _load_sound("UI/selected2.wav")
        elif key == "back":
            _sounds[key] = _load_sound("UI/back2.wav")
    return _sounds.get(key)


# Shared overlay image (loaded lazily)
_select_overlay = None


def _get_select_overlay():
    global _select_overlay
    if _select_overlay is None:
        _select_overlay = _load_image("select.png")
    return _select_overlay


class ImageButton:
    """Button that uses a PNG image as its base, with optional text overlay."""

    def __init__(self, x, y, image_name, text="", width=None, height=None,
                 font_size=22, selected=False):
        self.x = x
        self.y = y
        self.text = text
        self.font_size = font_size
        self.selected = selected
        self._hovered = False
        self._was_hovered = False

        # Load base image
        self.base_image = _load_image(image_name)
        if self.base_image is None:
            # Fallback: dark rectangle
            w = width or 260
            h = height or 55
            self.base_image = pg.Surface((w, h), pg.SRCALPHA)
            self.base_image.fill((30, 30, 50, 220))

        # Scale if dimensions specified
        if width and height:
            self.base_image = pg.transform.smoothscale(self.base_image, (width, height))
        elif width:
            ratio = width / self.base_image.get_width()
            h = int(self.base_image.get_height() * ratio)
            self.base_image = pg.transform.smoothscale(self.base_image, (width, h))
        elif height:
            ratio = height / self.base_image.get_height()
            w = int(self.base_image.get_width() * ratio)
            self.base_image = pg.transform.smoothscale(self.base_image, (w, height))

        self.width = self.base_image.get_width()
        self.height = self.base_image.get_height()
        self.rect = pg.Rect(x, y, self.width, self.height)

        # Prepare select overlay scaled to match
        overlay_src = _get_select_overlay()
        if overlay_src:
            self._select_overlay = pg.transform.smoothscale(
                overlay_src, (self.width + 16, self.height + 16)
            )
        else:
            self._select_overlay = None

    def handle_event(self, event) -> bool:
        """Returns True if button was clicked."""
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                snd = _get_sound("click")
                if snd:
                    snd.play()
                return True
        return False

    def update(self, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos)
        if self._hovered and not self._was_hovered:
            snd = _get_sound("hover")
            if snd:
                snd.play()
        self._was_hovered = self._hovered

    def draw(self, surface):
        # Draw select overlay if selected or hovered
        if (self.selected or self._hovered) and self._select_overlay:
            ox = self.x - 8
            oy = self.y - 8
            surface.blit(self._select_overlay, (ox, oy))

        # Draw base image
        surface.blit(self.base_image, (self.x, self.y))

        # Draw text overlay
        if self.text:
            font = _load_font(self.font_size)
            text_surf = font.render(self.text, True, WHITE)
            tx = self.x + (self.width - text_surf.get_width()) // 2
            ty = self.y + (self.height - text_surf.get_height()) // 2
            surface.blit(text_surf, (tx, ty))


class Slider:
    """Among Us themed horizontal slider with label and value display."""

    def __init__(self, x, y, width, label, min_val, max_val, value,
                 step=1, suffix="", font_size=18):
        self.x = x
        self.y = y
        self.width = width
        self.height = 32
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.step = step
        self.suffix = suffix
        self.font_size = font_size
        self._dragging = False

        # Track area (centered vertically in the widget)
        self.label_width = 140
        self.value_width = 60
        self.track_x = self.x + self.label_width
        self.track_w = self.width - self.label_width - self.value_width
        self.track_y = self.y + 10
        self.track_h = 12
        self.knob_radius = 10

        # +/- button areas
        self.minus_rect = pg.Rect(self.track_x - 24, self.y + 4, 22, 24)
        self.plus_rect = pg.Rect(
            self.track_x + self.track_w + 2, self.y + 4, 22, 24
        )

    def _knob_x(self):
        if self.max_val == self.min_val:
            return self.track_x
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return self.track_x + int(ratio * self.track_w)

    def _value_from_x(self, mx):
        ratio = max(0, min(1, (mx - self.track_x) / self.track_w))
        raw = self.min_val + ratio * (self.max_val - self.min_val)
        # Snap to step
        if self.step >= 1:
            return int(round(raw / self.step) * self.step)
        return round(raw / self.step) * self.step

    def handle_event(self, event) -> bool:
        """Returns True if value changed."""
        changed = False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Check knob/track area
            track_rect = pg.Rect(
                self.track_x, self.y, self.track_w, self.height
            )
            if track_rect.collidepoint(mx, my):
                self._dragging = True
                new_val = self._value_from_x(mx)
                if new_val != self.value:
                    self.value = new_val
                    changed = True
            elif self.minus_rect.collidepoint(mx, my):
                new_val = max(self.min_val, self.value - self.step)
                if new_val != self.value:
                    self.value = new_val
                    changed = True
                    snd = _get_sound("click")
                    if snd:
                        snd.play()
            elif self.plus_rect.collidepoint(mx, my):
                new_val = min(self.max_val, self.value + self.step)
                if new_val != self.value:
                    self.value = new_val
                    changed = True
                    snd = _get_sound("click")
                    if snd:
                        snd.play()
        elif event.type == pg.MOUSEBUTTONUP:
            self._dragging = False
        elif event.type == pg.MOUSEMOTION and self._dragging:
            mx = event.pos[0]
            new_val = self._value_from_x(mx)
            if new_val != self.value:
                self.value = new_val
                changed = True
        return changed

    def draw(self, surface):
        font = _load_font(self.font_size)

        # Label
        label_surf = font.render(self.label, True, WHITE)
        surface.blit(label_surf, (self.x, self.y + 4))

        # -/+ buttons
        btn_font = _load_font(16)
        minus_surf = btn_font.render("-", True, WHITE)
        plus_surf = btn_font.render("+", True, WHITE)
        pg.draw.rect(surface, (60, 60, 80), self.minus_rect, border_radius=4)
        pg.draw.rect(surface, (60, 60, 80), self.plus_rect, border_radius=4)
        surface.blit(
            minus_surf,
            (self.minus_rect.x + 6, self.minus_rect.y + 2),
        )
        surface.blit(
            plus_surf,
            (self.plus_rect.x + 5, self.plus_rect.y + 2),
        )

        # Track background
        pg.draw.rect(
            surface, SLIDER_TRACK,
            (self.track_x, self.track_y, self.track_w, self.track_h),
            border_radius=6,
        )

        # Fill
        knob_x = self._knob_x()
        fill_w = knob_x - self.track_x
        if fill_w > 0:
            pg.draw.rect(
                surface, SLIDER_FILL,
                (self.track_x, self.track_y, fill_w, self.track_h),
                border_radius=6,
            )

        # Knob
        knob_center = (knob_x, self.track_y + self.track_h // 2)
        pg.draw.circle(surface, KNOB_COLOR, knob_center, self.knob_radius)
        pg.draw.circle(surface, ACCENT_RED, knob_center, self.knob_radius, 2)

        # Value text
        if self.step >= 1:
            val_str = f"{int(self.value)}{self.suffix}"
        else:
            val_str = f"{self.value:.1f}{self.suffix}"
        val_surf = font.render(val_str, True, WHITE)
        vx = self.track_x + self.track_w + 30
        surface.blit(val_surf, (vx, self.y + 4))


class ColorSwatch:
    """Clickable color swatch using PNG images with fallback to drawn circles."""

    # Map of colour names to PNG filenames that exist in menu/
    COLOR_PNGS = {
        "Red": "red.png",
        "Blue": "blue.png",
        "Orange": "orange.png",
        "Yellow": "yellow.png",
        "Green": "green.png",
        "Pink": "pink.png",
    }

    def __init__(self, x, y, colour_name, size=50, selected=False):
        self.x = x
        self.y = y
        self.colour_name = colour_name
        self.size = size
        self.selected = selected
        self._hovered = False
        self._was_hovered = False

        # Try loading PNG
        png_name = self.COLOR_PNGS.get(colour_name)
        self.image = None
        if png_name:
            self.image = _load_image(png_name)
            if self.image:
                self.image = pg.transform.smoothscale(
                    self.image, (size, size)
                )

        self.rect = pg.Rect(x, y, size, size)

        # Select overlay
        overlay_src = _get_select_overlay()
        if overlay_src:
            self._select_overlay = pg.transform.smoothscale(
                overlay_src, (size + 12, size + 12)
            )
        else:
            self._select_overlay = None

    def handle_event(self, event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                snd = _get_sound("click")
                if snd:
                    snd.play()
                return True
        return False

    def update(self, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos)
        if self._hovered and not self._was_hovered:
            snd = _get_sound("hover")
            if snd:
                snd.play()
        self._was_hovered = self._hovered

    def draw(self, surface):
        # Selection/hover overlay
        if (self.selected or self._hovered) and self._select_overlay:
            surface.blit(self._select_overlay, (self.x - 6, self.y - 6))

        if self.image:
            surface.blit(self.image, (self.x, self.y))
        else:
            # Fallback: draw circle with PLAYER_DISPLAY_COLORS
            rgb = PLAYER_DISPLAY_COLORS.get(self.colour_name, (150, 150, 150))
            center = (self.x + self.size // 2, self.y + self.size // 2)
            pg.draw.circle(surface, rgb, center, self.size // 2 - 2)
            pg.draw.circle(surface, WHITE, center, self.size // 2 - 2, 2)
