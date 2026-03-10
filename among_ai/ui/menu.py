"""Main menu screen for Among AI with mode selection, settings, and color picker."""

import os
import pygame as pg
from dataclasses import dataclass

from among_ai.constants import WIDTH, HEIGHT, FONT, ALL_COLOURS, WHITE, BLACK
from among_ai.ui.widgets import (
    ImageButton, Slider, ColorSwatch,
    _load_image, _load_font, _get_sound,
    ACCENT_RED, PANEL_BG,
)
from among_ai.config import Config

MENU_IMG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Assets", "Images", "menu",
)
SOUND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Assets", "Sounds",
)


@dataclass
class MenuResult:
    action: str  # "start_game" or "quit"
    mode: str = "watch_ai"  # "watch_ai" or "play_with_ai"
    player_colour: str = "Red"


class MainMenu:
    """Full-screen main menu with mode selection, settings, and color picker."""

    def __init__(self, screen: pg.Surface, config: Config):
        self.screen = screen
        self.config = config
        self.running = True

        # State
        self.mode = "watch_ai"  # or "play_with_ai"
        self.selected_colour = config.game.human_colour

        # Load background images
        self.bg_image = _load_image("back.png")
        if self.bg_image:
            self.bg_image = pg.transform.smoothscale(self.bg_image, (WIDTH, HEIGHT))

        self.title_image = _load_image("title.png")
        if self.title_image:
            # Scale title to ~600px wide
            tw = 600
            ratio = tw / self.title_image.get_width()
            th = int(self.title_image.get_height() * ratio)
            self.title_image = pg.transform.smoothscale(self.title_image, (tw, th))

        self.shhh_image = None  # removed from menu

        self.sel_character = _load_image("sel.png")
        if self.sel_character:
            cw = 60
            ratio = cw / self.sel_character.get_width()
            ch = int(self.sel_character.get_height() * ratio)
            self.sel_character = pg.transform.smoothscale(self.sel_character, (cw, ch))

        self.choose_colour_banner = _load_image("choosecolour.png")
        if self.choose_colour_banner:
            bw = 380
            ratio = bw / self.choose_colour_banner.get_width()
            bh = int(self.choose_colour_banner.get_height() * ratio)
            self.choose_colour_banner = pg.transform.smoothscale(
                self.choose_colour_banner, (bw, bh)
            )

        # Mode buttons  (no texture PNG — clean flat look)
        btn_w, btn_h = 300, 65
        self.spectate_btn = ImageButton(
            100, 340, "", "SPECTATE AI",
            width=btn_w, height=btn_h, font_size=24, selected=True, no_texture=True,
        )
        self.play_btn = ImageButton(
            100, 430, "", "PLAY WITH AI",
            width=btn_w, height=btn_h, font_size=24, disabled=True, no_texture=True,
        )

        # Quit button (flat, no texture)
        self.quit_btn = ImageButton(
            60, HEIGHT - 100, "", "QUIT",
            width=200, height=55, font_size=20, no_texture=True,
        )

        # Start button (flat, no texture)
        self.start_btn = ImageButton(
            WIDTH // 2 - 180, HEIGHT - 110, "", "START GAME",
            width=360, height=70, font_size=30, no_texture=True,
        )

        # Settings sliders
        sx = 1020
        sy = 310
        sw = 500
        gap = 52
        g = config.game
        self.sliders = {
            "num_players": Slider(
                sx, sy, sw, "Players:", 4, 10, g.num_players, step=1
            ),
            "num_impostors": Slider(
                sx, sy + gap, sw, "Impostors:", 1, 3, g.num_impostors, step=1
            ),
            "discussion_time": Slider(
                sx, sy + gap * 2, sw, "Discussion:", 10, 120,
                g.discussion_time, step=5, suffix="s",
            ),
            "voting_time": Slider(
                sx, sy + gap * 3, sw, "Voting:", 10, 120,
                g.voting_time, step=5, suffix="s",
            ),
            "kill_cooldown": Slider(
                sx, sy + gap * 4, sw, "Kill CD:", 10, 60,
                g.kill_cooldown, step=5, suffix="s",
            ),
            "game_speed": Slider(
                sx, sy + gap * 5, sw, "Speed:", 0.5, 3.0,
                g.game_speed, step=0.5, suffix="x",
            ),
            "task_count": Slider(
                sx, sy + gap * 6, sw, "Tasks:", 3, 10,
                g.task_count, step=1,
            ),
        }

        # Color picker swatches
        self._build_color_swatches()

        # Music
        self._music_playing = False
        self._start_music()

    def _build_color_swatches(self):
        """Build color swatch grid."""
        self.color_swatches = []
        sx = 110
        sy = 610
        swatch_size = 50
        gap = 10
        cols = 5
        for i, colour in enumerate(ALL_COLOURS):
            col = i % cols
            row = i // cols
            x = sx + col * (swatch_size + gap)
            y = sy + row * (swatch_size + gap)
            selected = colour == self.selected_colour
            swatch = ColorSwatch(x, y, colour, size=swatch_size, selected=selected)
            self.color_swatches.append(swatch)

    def _start_music(self):
        music_path = os.path.join(SOUND_DIR, "Background", "main_menu_music.mp3")
        if os.path.exists(music_path):
            try:
                pg.mixer.music.load(music_path)
                pg.mixer.music.set_volume(0.4)
                pg.mixer.music.play(-1)
                self._music_playing = True
            except Exception:
                pass

    def _stop_music(self):
        if self._music_playing:
            try:
                pg.mixer.music.fadeout(800)
            except Exception:
                pass
            self._music_playing = False

    def _apply_settings_to_config(self):
        """Write slider values back to config."""
        g = self.config.game
        g.num_players = int(self.sliders["num_players"].value)
        g.num_impostors = int(self.sliders["num_impostors"].value)
        g.discussion_time = int(self.sliders["discussion_time"].value)
        g.voting_time = int(self.sliders["voting_time"].value)
        g.kill_cooldown = int(self.sliders["kill_cooldown"].value)
        g.game_speed = self.sliders["game_speed"].value
        g.task_count = int(self.sliders["task_count"].value)
        g.mode = self.mode
        g.human_colour = self.selected_colour

    def _clamp_impostors(self):
        """Ensure impostors <= num_players // 3."""
        num_p = int(self.sliders["num_players"].value)
        max_imp = max(1, num_p // 3)
        imp_slider = self.sliders["num_impostors"]
        imp_slider.max_val = max_imp
        if imp_slider.value > max_imp:
            imp_slider.value = max_imp

    def run(self) -> MenuResult:
        """Run the menu event loop. Returns MenuResult when user makes a choice."""
        clock = pg.time.Clock()

        while self.running:
            mouse_pos = pg.mouse.get_pos()

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self._stop_music()
                    return MenuResult(action="quit")

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self._stop_music()
                        return MenuResult(action="quit")
                    if event.key == pg.K_RETURN:
                        self._stop_music()
                        self._apply_settings_to_config()
                        return MenuResult(
                            action="start_game",
                            mode=self.mode,
                            player_colour=self.selected_colour,
                        )

                # Mode buttons
                if self.spectate_btn.handle_event(event):
                    self.mode = "watch_ai"
                    self.spectate_btn.selected = True
                    self.play_btn.selected = False

                # play_btn is disabled — no-op

                # Quit
                if self.quit_btn.handle_event(event):
                    self._stop_music()
                    return MenuResult(action="quit")

                # Start
                if self.start_btn.handle_event(event):
                    self._stop_music()
                    self._apply_settings_to_config()
                    return MenuResult(
                        action="start_game",
                        mode=self.mode,
                        player_colour=self.selected_colour,
                    )

                # Sliders
                for slider in self.sliders.values():
                    slider.handle_event(event)
                self._clamp_impostors()

                # Color swatches (only in play_with_ai mode)
                if self.mode == "play_with_ai":
                    for swatch in self.color_swatches:
                        if swatch.handle_event(event):
                            self.selected_colour = swatch.colour_name
                            for s in self.color_swatches:
                                s.selected = (s.colour_name == self.selected_colour)

            # Update hover states
            self.spectate_btn.update(mouse_pos)
            self.play_btn.update(mouse_pos)
            self.quit_btn.update(mouse_pos)
            self.start_btn.update(mouse_pos)
            if self.mode == "play_with_ai":
                for swatch in self.color_swatches:
                    swatch.update(mouse_pos)

            self._draw()
            clock.tick(60)

        self._stop_music()
        return MenuResult(action="quit")

    def _draw(self):
        # Background
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill((10, 10, 30))

        # Dim overlay for readability
        dim = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        dim.fill((0, 0, 0, 100))
        self.screen.blit(dim, (0, 0))

        # Title
        if self.title_image:
            tx = (WIDTH - self.title_image.get_width()) // 2
            self.screen.blit(self.title_image, (tx, 30))

        # Subtitle
        subtitle_font = _load_font(28)
        subtitle = subtitle_font.render("AI Edition", True, ACCENT_RED)
        sx = (WIDTH - subtitle.get_width()) // 2
        title_bottom = 30 + (self.title_image.get_height() if self.title_image else 80)
        self.screen.blit(subtitle, (sx, title_bottom + 5))

        # ---- LEFT COLUMN: Game Mode ----
        header_font = _load_font(26)
        mode_header = header_font.render("GAME MODE", True, WHITE)
        self.screen.blit(mode_header, (100, 290))

        self.spectate_btn.draw(self.screen)
        self.play_btn.draw(self.screen)

        # Color picker (only for play_with_ai)
        if self.mode == "play_with_ai":
            if self.choose_colour_banner:
                self.screen.blit(self.choose_colour_banner, (80, 545))

            for swatch in self.color_swatches:
                swatch.draw(self.screen)

            # Show sel.png character next to selected colour
            if self.sel_character:
                for swatch in self.color_swatches:
                    if swatch.selected:
                        cx = swatch.x + swatch.size + 8
                        cy = swatch.y - 10
                        self.screen.blit(self.sel_character, (cx, cy))
                        break

        # ---- RIGHT COLUMN: Settings ----
        # Semi-transparent panel behind settings
        panel = pg.Surface((560, 430), pg.SRCALPHA)
        panel.fill((10, 10, 30, 180))
        self.screen.blit(panel, (990, 270))

        settings_header = header_font.render("SETTINGS", True, WHITE)
        self.screen.blit(settings_header, (1020, 278))

        for slider in self.sliders.values():
            slider.draw(self.screen)

        # ---- Bottom bar ----
        self.quit_btn.draw(self.screen)
        self.start_btn.draw(self.screen)

        # (shhh image removed)

        pg.display.flip()
