"""AI memory system: event storage, spatial memory, suspicion tracking."""

import time
from among_ai.ai.interfaces import IMemory, MemoryEvent


class Memory(IMemory):
    """Concrete memory implementation with event history and suspicion tracking."""

    MAX_EVENTS = 60

    def __init__(self, owner_colour: str):
        self.owner_colour = owner_colour
        self.events: list[MemoryEvent] = []
        self.suspicion: dict[str, float] = {}   # colour -> 0.0-1.0
        self.last_known_locations: dict[str, tuple] = {}  # colour -> (room, timestamp)

    def record_event(self, event: MemoryEvent):
        self.events.append(event)
        # Update location tracking for actors
        for actor in event.actors:
            if actor != self.owner_colour:
                self.last_known_locations[actor] = (event.location, event.timestamp)
        # Prune old low-importance events
        if len(self.events) > self.MAX_EVENTS:
            self.events.sort(key=lambda e: (e.importance, e.timestamp))
            self.events = self.events[len(self.events) - self.MAX_EVENTS:]
            self.events.sort(key=lambda e: e.timestamp)

    def get_recent_events(self, count: int = 10) -> list:
        return self.events[-count:]

    def get_events_about_player(self, player_colour: str) -> list:
        return [e for e in self.events if player_colour in e.actors]

    def get_suspicion_level(self, player_colour: str) -> float:
        return self.suspicion.get(player_colour, 0.0)

    def update_suspicion(self, player_colour: str, delta: float, reason: str):
        current = self.suspicion.get(player_colour, 0.0)
        new_val = max(0.0, min(1.0, current + delta))
        self.suspicion[player_colour] = new_val

    def get_known_player_locations(self) -> dict:
        return dict(self.last_known_locations)

    def summarize_for_prompt(self, max_tokens: int = 500) -> str:
        """Generate a text summary of recent events and suspicions."""
        lines = []
        now = time.time()
        recent = self.get_recent_events(12)
        for event in reversed(recent):
            ago = int(now - event.timestamp)
            lines.append(f"- {ago}s ago: {event.description}")

        # Add suspicion summary
        suspicious = [(c, s) for c, s in self.suspicion.items() if s > 0.3]
        suspicious.sort(key=lambda x: x[1], reverse=True)
        if suspicious:
            lines.append("")
            lines.append("SUSPICIONS:")
            for colour, level in suspicious[:5]:
                label = "low" if level < 0.5 else "medium" if level < 0.7 else "HIGH"
                lines.append(f"- {colour}: {label} suspicion ({level:.1f})")

        return "\n".join(lines)

    def clear(self):
        self.events.clear()
        self.suspicion.clear()
        self.last_known_locations.clear()
