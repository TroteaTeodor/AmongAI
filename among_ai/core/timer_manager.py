"""Centralized timer system replacing the scattered USEREVENT timers."""

import pygame
import time


class Timer:
    """A single countdown timer."""

    def __init__(self, name: str, duration: float, auto_start: bool = False):
        self.name = name
        self.duration = duration
        self.remaining = duration
        self.running = auto_start
        self.finished = False
        self._last_tick = time.time() if auto_start else 0

    def start(self):
        self.remaining = self.duration
        self.running = True
        self.finished = False
        self._last_tick = time.time()

    def restart(self):
        self.start()

    def stop(self):
        self.running = False

    def update(self):
        if not self.running or self.finished:
            return
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
            self.finished = True
            self.running = False

    def is_ready(self) -> bool:
        """Returns True if timer has finished (cooldown is over)."""
        return self.finished or (not self.running and self.remaining <= 0)

    def get_remaining_int(self) -> int:
        return max(0, int(self.remaining))


class TimerManager:
    """Manages all game timers centrally."""

    def __init__(self):
        self.timers: dict[str, Timer] = {}
        self._setup_default_timers()

    def _setup_default_timers(self):
        from among_ai.constants import (
            KILL_COOLDOWN, SABOTAGE_COOLDOWN, REACTOR_MELTDOWN_TIME,
            MEETING_DURATION, MEETING_COOLDOWN, LIGHTS_DURATION,
        )
        self.timers['kill_cooldown'] = Timer('kill_cooldown', KILL_COOLDOWN, auto_start=True)
        self.timers['sabotage_cooldown'] = Timer('sabotage_cooldown', SABOTAGE_COOLDOWN, auto_start=True)
        self.timers['reactor_meltdown'] = Timer('reactor_meltdown', REACTOR_MELTDOWN_TIME)
        self.timers['meeting_duration'] = Timer('meeting_duration', MEETING_DURATION)
        self.timers['meeting_cooldown'] = Timer('meeting_cooldown', MEETING_COOLDOWN, auto_start=True)
        self.timers['lights_duration'] = Timer('lights_duration', LIGHTS_DURATION)

    def update(self):
        """Update all timers. Call once per frame."""
        for timer in self.timers.values():
            timer.update()

    def get(self, name: str) -> Timer:
        return self.timers[name]

    def add(self, name: str, duration: float, auto_start: bool = False) -> Timer:
        timer = Timer(name, duration, auto_start)
        self.timers[name] = timer
        return timer

    def is_ready(self, name: str) -> bool:
        return self.timers[name].is_ready()

    def start(self, name: str):
        self.timers[name].start()

    def restart(self, name: str):
        self.timers[name].restart()

    def remaining(self, name: str) -> float:
        return self.timers[name].remaining
