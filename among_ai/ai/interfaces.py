"""Abstract interfaces (ABCs) and shared data types for the AI system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
# Data Types
# ============================================================

@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    raw_response: Optional[dict] = None


class AIAction(Enum):
    """All possible actions an AI player can take."""
    MOVE_TO_ROOM = "move_to_room"
    DO_TASK = "do_task"
    KILL = "kill"
    REPORT_BODY = "report_body"
    CALL_MEETING = "call_meeting"
    VENT = "vent"
    SABOTAGE_LIGHTS = "sabotage_lights"
    SABOTAGE_REACTOR = "sabotage_reactor"
    FIX_LIGHTS = "fix_lights"
    FIX_REACTOR = "fix_reactor"
    IDLE = "idle"
    FOLLOW_PLAYER = "follow_player"
    FLEE = "flee"


@dataclass
class AIDecision:
    """A decision made by the AI brain."""
    action: AIAction
    target_room: Optional[str] = None
    target_task: Optional[str] = None
    target_player: Optional[str] = None
    target_position: Optional[tuple] = None
    reasoning: str = ""
    confidence: float = 1.0


@dataclass
class PlayerSnapshot:
    """Frozen snapshot of a player's visible state."""
    colour: str
    position: tuple
    room: str
    alive: bool
    is_impostor: bool = False  # Only set for the requesting AI's own snapshot
    tasks_completed: int = 0
    is_visible: bool = True


@dataclass
class GameStateSnapshot:
    """Immutable snapshot of game state for AI consumption."""
    # Game info
    game_time: float = 0.0
    phase: str = "gameplay"  # gameplay, meeting_alert, discussion, voting, ejection
    sabotage_active: Optional[str] = None  # None, "lights", "reactor"
    reactor_countdown: Optional[int] = None

    # This AI's info
    my_colour: str = ""
    my_position: tuple = (0, 0)
    my_room: str = ""
    my_role: str = "crewmate"  # crewmate or impostor
    my_tasks_completed: int = 0
    my_tasks_total: int = 8
    my_assigned_tasks: list = field(default_factory=list)
    my_completed_tasks: list = field(default_factory=list)
    kill_cooldown_remaining: float = 0.0
    sabotage_cooldown_remaining: float = 0.0
    meeting_cooldown_remaining: float = 0.0
    can_call_meeting: bool = False
    is_near_emergency_button: bool = False
    is_near_vent: bool = False
    is_in_vent: bool = False

    # Other players
    visible_players: list = field(default_factory=list)
    visible_bodies: list = field(default_factory=list)
    all_players: list = field(default_factory=list)

    # Memory (pre-serialized)
    memory_summary: str = ""

    # Meeting info
    chat_history: Optional[list] = None
    accusation_summary: Optional[str] = None


@dataclass
class MemoryEvent:
    """A single event stored in AI memory."""
    timestamp: float
    event_type: str  # saw_player, saw_body, heard_kill, task_done, sabotage, meeting, vote, ejection
    location: str
    actors: list = field(default_factory=list)
    description: str = ""
    importance: float = 0.5  # 0.0-1.0


# ============================================================
# Abstract Interfaces
# ============================================================

class ILLMProvider(ABC):
    """Interface for all LLM API providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 300,
        stop_sequences: Optional[list] = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider has a valid API key configured."""
        ...


class IAIBrain(ABC):
    """Interface for AI decision-making."""

    @abstractmethod
    async def decide_action(self, game_state: GameStateSnapshot) -> AIDecision:
        """Decide what action to take given the current game state."""
        ...

    @abstractmethod
    async def generate_chat_message(
        self,
        game_state: GameStateSnapshot,
        chat_history: list,
        phase: str,
    ) -> str:
        """Generate a chat message during a meeting discussion."""
        ...

    @abstractmethod
    async def decide_vote(
        self,
        game_state: GameStateSnapshot,
        chat_history: list,
        alive_players: list,
    ) -> Optional[str]:
        """Decide who to vote for. Returns player colour or None to skip."""
        ...

    @abstractmethod
    def get_fallback_action(self, game_state: GameStateSnapshot) -> AIDecision:
        """Rule-based fallback when LLM is unavailable/slow."""
        ...


class IMemory(ABC):
    """Interface for AI memory system."""

    @abstractmethod
    def record_event(self, event: MemoryEvent) -> None:
        ...

    @abstractmethod
    def get_recent_events(self, count: int = 10) -> list:
        ...

    @abstractmethod
    def get_events_about_player(self, player_colour: str) -> list:
        ...

    @abstractmethod
    def get_suspicion_level(self, player_colour: str) -> float:
        ...

    @abstractmethod
    def update_suspicion(self, player_colour: str, delta: float, reason: str) -> None:
        ...

    @abstractmethod
    def get_known_player_locations(self) -> dict:
        """Return {colour: (room_name, timestamp)}."""
        ...

    @abstractmethod
    def summarize_for_prompt(self, max_tokens: int = 500) -> str:
        """Generate text summary for LLM prompt inclusion."""
        ...

    @abstractmethod
    def clear(self) -> None:
        ...


class IPathfinder(ABC):
    """Interface for pathfinding on the game map."""

    @abstractmethod
    def find_path(
        self, start: tuple, goal: tuple
    ) -> Optional[list]:
        """Find path from start to goal. Returns list of (x,y) waypoints or None."""
        ...

    @abstractmethod
    def get_room_at(self, position: tuple) -> str:
        """Determine which room a position is in."""
        ...

    @abstractmethod
    def get_room_center(self, room_name: str) -> tuple:
        """Get center coordinates of a named room."""
        ...

    @abstractmethod
    def get_nearest_vent(self, position: tuple) -> Optional[tuple]:
        ...

    @abstractmethod
    def get_nearest_task_location(
        self, position: tuple, available_tasks: list
    ) -> Optional[tuple]:
        """Returns (task_name, (x, y)) or None."""
        ...

    @abstractmethod
    def distance_between(self, a: tuple, b: tuple) -> float:
        ...
