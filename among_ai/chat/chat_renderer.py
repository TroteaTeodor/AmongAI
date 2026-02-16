"""Pygame UI for rendering scrollable chat messages during meetings."""

import pygame as pg
from among_ai.constants import WIDTH, HEIGHT, FONT, WHITE, BLACK, PLAYER_DISPLAY_COLORS


class ChatRenderer:
    """Renders scrollable chat messages on the game screen during meetings."""

    def __init__(self):
        self.font = None
        self.small_font = None
        self.header_font = None
        self._scroll_offset = 0  # In pixels, scrolls upward
        self._line_height = 26
        self._padding = 12
        self._chat_area = pg.Rect(50, 70, WIDTH - 100, HEIGHT - 170)
        self._rendered_height = 0  # Total height of all rendered messages
        self._auto_scroll = True  # Auto-scroll to bottom on new messages
        self._last_msg_count = 0

    def _ensure_fonts(self):
        if self.font is None:
            try:
                self.font = pg.font.Font(FONT, 15)
                self.small_font = pg.font.Font(FONT, 11)
                self.header_font = pg.font.Font(FONT, 20)
            except Exception:
                self.font = pg.font.SysFont("arial", 15)
                self.small_font = pg.font.SysFont("arial", 11)
                self.header_font = pg.font.SysFont("arial", 20)

    def handle_event(self, event):
        """Handle mouse wheel scrolling."""
        if event.type == pg.MOUSEWHEEL:
            self._scroll_offset -= event.y * 40  # 40px per scroll tick
            self._scroll_offset = max(0, self._scroll_offset)
            max_scroll = max(0, self._rendered_height - self._chat_area.height + 20)
            self._scroll_offset = min(self._scroll_offset, max_scroll)
            self._auto_scroll = (self._scroll_offset >= max_scroll - 10)

    def render(self, screen: pg.Surface, messages: list[dict],
               phase: str, time_remaining: float,
               vote_summary: dict = None):
        """Render the meeting UI with scrollable chat messages."""
        self._ensure_fonts()

        # Auto-scroll when new messages arrive
        if len(messages) != self._last_msg_count:
            self._last_msg_count = len(messages)
            if self._auto_scroll:
                max_scroll = max(0, self._rendered_height - self._chat_area.height + 20)
                self._scroll_offset = max_scroll

        # Semi-transparent dark overlay
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        # Header bar
        header_bg = pg.Rect(0, 0, WIDTH, 55)
        pg.draw.rect(screen, (20, 20, 40), header_bg)
        pg.draw.line(screen, (100, 100, 160), (0, 55), (WIDTH, 55), 2)

        header_text = "🔴 EMERGENCY MEETING" if phase != "voting" else "🗳️ VOTING TIME"
        header = self.header_font.render(header_text, True, (255, 80, 80) if phase != "voting" else (80, 200, 255))
        screen.blit(header, (WIDTH // 2 - header.get_width() // 2, 14))

        # Timer (right side)
        timer_colour = (255, 100, 100) if time_remaining < 10 else (180, 220, 180)
        timer_text = self.small_font.render(f"⏱ {int(time_remaining)}s", True, timer_colour)
        screen.blit(timer_text, (WIDTH - 100, 22))

        # Phase (left side)
        phase_label = phase.upper().replace("_", " ")
        phase_text = self.small_font.render(phase_label, True, (140, 140, 170))
        screen.blit(phase_text, (20, 22))

        # Chat area background
        pg.draw.rect(screen, (18, 18, 35), self._chat_area)
        pg.draw.rect(screen, (60, 60, 100), self._chat_area, 1)

        # Create a clipping surface for the chat area
        chat_surface = pg.Surface((self._chat_area.width, self._chat_area.height), pg.SRCALPHA)
        chat_surface.fill((0, 0, 0, 0))

        # Render all messages onto chat surface
        y = self._padding - self._scroll_offset
        for i, msg in enumerate(messages):
            speaker = msg.get("speaker", "???")
            text = msg.get("text", "")
            colour = PLAYER_DISPLAY_COLORS.get(speaker, WHITE)

            # Speaker name with coloured dot
            dot_y = y + 7
            if 0 <= dot_y < self._chat_area.height:
                pg.draw.circle(chat_surface, colour, (12, dot_y), 5)

            name_surf = self.font.render(f"{speaker}:", True, colour)
            msg_start_y = y

            if -self._line_height < y < self._chat_area.height:
                chat_surface.blit(name_surf, (22, y))

            # Message text (word wrap)
            # First line starts after speaker name; continuation lines
            # wrap to a small indent so they use the full width.
            first_line_x = 22 + name_surf.get_width() + 8
            wrap_x = 32  # continuation indent
            current_x = first_line_x
            max_first = self._chat_area.width - first_line_x - self._padding
            max_wrap = self._chat_area.width - wrap_x - self._padding

            words = text.split()
            line = ""
            max_width = max_first
            for word in words:
                test = line + " " + word if line else word
                test_w = self.font.size(test)[0]
                if test_w > max_width and line:
                    if -self._line_height < y < self._chat_area.height:
                        line_surf = self.font.render(line, True, (220, 220, 230))
                        chat_surface.blit(line_surf, (current_x, y))
                    y += self._line_height
                    # After the first rendered line, use the smaller indent
                    current_x = wrap_x
                    max_width = max_wrap
                    line = word
                else:
                    line = test
            if line:
                if -self._line_height < y < self._chat_area.height:
                    line_surf = self.font.render(line, True, (220, 220, 230))
                    chat_surface.blit(line_surf, (current_x, y))

            y += self._line_height + 6

            # Separator line between messages
            if i < len(messages) - 1 and -2 < y < self._chat_area.height:
                pg.draw.line(chat_surface, (40, 40, 60),
                           (10, y - 2), (self._chat_area.width - 10, y - 2), 1)

        # Store total rendered height for scroll calculations
        self._rendered_height = y + self._scroll_offset

        screen.blit(chat_surface, (self._chat_area.x, self._chat_area.y))

        # Scroll indicator
        if self._rendered_height > self._chat_area.height:
            scrollbar_height = max(20, int(self._chat_area.height *
                                          (self._chat_area.height / self._rendered_height)))
            max_scroll = self._rendered_height - self._chat_area.height
            scrollbar_y = int(self._chat_area.y +
                            (self._scroll_offset / max(1, max_scroll)) *
                            (self._chat_area.height - scrollbar_height))
            scrollbar_rect = pg.Rect(
                self._chat_area.right - 6, scrollbar_y, 4, scrollbar_height
            )
            pg.draw.rect(screen, (80, 80, 120), scrollbar_rect, border_radius=2)

        # Vote summary during voting/results
        if vote_summary and phase in ("voting", "results"):
            self._render_votes(screen, vote_summary)

    def _render_votes(self, screen, vote_summary: dict):
        """Render vote tally at the bottom."""
        vote_bg = pg.Rect(40, HEIGHT - 85, WIDTH - 80, 75)
        pg.draw.rect(screen, (25, 25, 45), vote_bg, border_radius=6)
        pg.draw.rect(screen, (80, 80, 120), vote_bg, 1, border_radius=6)

        y = HEIGHT - 78
        x = 60
        title = self.font.render("VOTES:", True, (200, 200, 255))
        screen.blit(title, (x, y))
        x += title.get_width() + 15

        for target, voters in vote_summary.items():
            if not voters:
                continue
            colour = PLAYER_DISPLAY_COLORS.get(target, WHITE)
            text = f"{target}: {len(voters)} ({', '.join(voters)})"
            surf = self.small_font.render(text, True, colour)
            screen.blit(surf, (x, y + 3))
            x += surf.get_width() + 20
            if x > WIDTH - 200:
                x = 60
                y += 22
