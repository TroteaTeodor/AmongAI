"""Pygame UI for rendering chat messages during meetings."""

import pygame as pg
from among_ai.constants import WIDTH, HEIGHT, FONT, WHITE, BLACK, PLAYER_DISPLAY_COLORS


class ChatRenderer:
    """Renders scrollable chat messages on the game screen during meetings."""

    def __init__(self):
        self.font = None
        self.small_font = None
        self._scroll_offset = 0
        self._max_visible = 12
        self._line_height = 28
        self._padding = 15
        self._chat_area = pg.Rect(50, 100, WIDTH - 100, HEIGHT - 200)

    def _ensure_fonts(self):
        if self.font is None:
            try:
                self.font = pg.font.Font(FONT, 16)
                self.small_font = pg.font.Font(FONT, 12)
            except Exception:
                self.font = pg.font.SysFont("arial", 16)
                self.small_font = pg.font.SysFont("arial", 12)

    def render(self, screen: pg.Surface, messages: list[dict],
               phase: str, time_remaining: float,
               vote_summary: dict = None):
        """Render the meeting UI with chat messages."""
        self._ensure_fonts()

        # Semi-transparent dark overlay
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # Header
        header_text = "EMERGENCY MEETING" if phase != "voting" else "VOTING TIME"
        header = self.font.render(header_text, True, WHITE)
        screen.blit(header, (WIDTH // 2 - header.get_width() // 2, 20))

        # Timer
        timer_text = self.small_font.render(f"Time: {int(time_remaining)}s", True, WHITE)
        screen.blit(timer_text, (WIDTH - 150, 20))

        # Phase indicator
        phase_text = self.small_font.render(f"Phase: {phase.upper()}", True, (180, 180, 180))
        screen.blit(phase_text, (50, 20))

        # Chat area background
        pg.draw.rect(screen, (30, 30, 50), self._chat_area)
        pg.draw.rect(screen, (80, 80, 120), self._chat_area, 2)

        # Render messages
        y = self._chat_area.y + self._padding
        visible_messages = messages[-self._max_visible:]
        for msg in visible_messages:
            if y > self._chat_area.bottom - self._line_height:
                break
            speaker = msg.get("speaker", "???")
            text = msg.get("text", "")
            colour = PLAYER_DISPLAY_COLORS.get(speaker, WHITE)

            # Speaker name
            name_surf = self.font.render(f"[{speaker}]", True, colour)
            screen.blit(name_surf, (self._chat_area.x + self._padding, y))

            # Message text (wrap if needed)
            msg_x = self._chat_area.x + self._padding + name_surf.get_width() + 8
            max_width = self._chat_area.right - msg_x - self._padding

            words = text.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                test_surf = self.font.render(test, True, WHITE)
                if test_surf.get_width() > max_width and line:
                    line_surf = self.font.render(line, True, WHITE)
                    screen.blit(line_surf, (msg_x, y))
                    y += self._line_height
                    line = word
                else:
                    line = test
            if line:
                line_surf = self.font.render(line, True, WHITE)
                screen.blit(line_surf, (msg_x, y))

            y += self._line_height + 4

        # Vote summary during voting/results
        if vote_summary and phase in ("voting", "results"):
            self._render_votes(screen, vote_summary)

    def _render_votes(self, screen, vote_summary: dict):
        """Render vote tally at the bottom."""
        y = HEIGHT - 90
        x = 60
        title = self.font.render("VOTES:", True, WHITE)
        screen.blit(title, (x, y))
        y += 24
        for target, voters in vote_summary.items():
            if not voters:
                continue
            colour = PLAYER_DISPLAY_COLORS.get(target, WHITE)
            text = f"{target}: {len(voters)} vote(s) ({', '.join(voters)})"
            surf = self.small_font.render(text, True, colour)
            screen.blit(surf, (x, y))
            x += surf.get_width() + 30
            if x > WIDTH - 200:
                x = 60
                y += 20
