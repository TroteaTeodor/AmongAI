"""Two-tier AI decision architecture: Intents (persistent goals) and Reflexes (instant reactions)."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from among_ai.ai.interfaces import AIAction, AIDecision, MemoryEvent


# ============================================================
# Intent Layer — persistent goals from LLM decisions
# ============================================================

class IntentType(Enum):
    DO_TASK = "do_task"
    PATROL = "patrol"
    HUNT = "hunt"
    FAKE_TASK = "fake_task"
    GUARD = "guard"
    FOLLOW = "follow"
    SABOTAGE = "sabotage"
    IDLE = "idle"


@dataclass
class Intent:
    """A persistent goal that the AI is working toward."""
    intent_type: IntentType
    target_room: Optional[str] = None
    target_task: Optional[str] = None
    target_player: Optional[str] = None
    reasoning: str = ""
    created_at: float = 0.0
    expires_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def __str__(self) -> str:
        parts = [self.intent_type.value]
        if self.target_room:
            parts.append(f"at {self.target_room}")
        if self.target_task:
            parts.append(f"(task: {self.target_task})")
        if self.target_player:
            parts.append(f"-> {self.target_player}")
        return " ".join(parts)


# ============================================================
# Reflex Layer — instant reactions that bypass LLM
# ============================================================

class ReflexType(Enum):
    REPORT_BODY = "report_body"
    SAW_BODY = "saw_body"          # Non-forced: interrupt + let LLM decide
    FIX_SABOTAGE = "fix_sabotage"
    OPPORTUNISTIC_KILL = "opportunistic_kill"


@dataclass
class Reflex:
    """An instant reaction that should be executed immediately."""
    reflex_type: ReflexType
    decision: AIDecision
    reason: str = ""


# Constants
EARLY_GAME_GRACE = 30.0  # Seconds before impostor can opportunistic-kill
OPPORTUNITY_COOLDOWN = 15.0  # Seconds between opportunity evaluations


class ReflexEvaluator:
    """Evaluates reflex conditions for an AI player. All methods are static
    and produce a Reflex or None — no LLM calls involved."""

    @staticmethod
    def evaluate(player, game) -> Optional[Reflex]:
        """Run all reflex checks in priority order. Returns the first triggered reflex."""
        # Don't evaluate during meetings
        if game.meeting_manager.is_active:
            return None

        reflex = ReflexEvaluator._check_body_report(player, game)
        if reflex:
            return reflex

        reflex = ReflexEvaluator._check_fix_sabotage(player, game)
        if reflex:
            return reflex

        if player.imposter:
            reflex = ReflexEvaluator._check_opportunistic_kill(player, game)
            if reflex:
                return reflex

        return None

    @staticmethod
    def _check_body_report(player, game) -> Optional[Reflex]:
        """Any player sees an unreported body with LOS -> interrupt for LLM decision.
        Does NOT auto-queue REPORT_BODY; instead triggers SAW_BODY so the
        AI can choose what to do (report, flee, self-report strategically, etc.)."""
        pathfinder = game.pathfinder
        vision_radius = game.config.ai.vision_radius
        my_pos = (player.pos.x, player.pos.y)

        # Track which bodies this player already reacted to
        seen_bodies = getattr(player, '_seen_bodies', set())

        for other in game.ai_players:
            if other.alive_status or other.got_reported:
                continue

            # Skip bodies we already triggered a reflex for
            if other.bot_colour in seen_bodies:
                continue

            body_pos = (other.pos.x, other.pos.y)
            dx = body_pos[0] - my_pos[0]
            dy = body_pos[1] - my_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > vision_radius:
                continue

            # LOS check
            if pathfinder and hasattr(pathfinder, 'has_line_of_sight'):
                if not pathfinder.has_line_of_sight(my_pos, body_pos):
                    continue

            body_room = pathfinder.get_room_at(body_pos) if pathfinder else "Unknown"

            # Mark this body as seen so reflex doesn't spam
            seen_bodies.add(other.bot_colour)

            # Record to memory immediately
            if hasattr(player, 'memory') and player.memory:
                player.memory.record_event(MemoryEvent(
                    timestamp=time.time(),
                    event_type="saw_body",
                    location=body_room,
                    actors=[other.bot_colour],
                    description=f"Found {other.bot_colour}'s dead body in {body_room}!",
                    importance=1.0,
                ))

            return Reflex(
                reflex_type=ReflexType.SAW_BODY,
                decision=None,  # No forced action — LLM will decide
                reason=f"Saw {other.bot_colour}'s body in {body_room}",
            )

        return None

    @staticmethod
    def _check_fix_sabotage(player, game) -> Optional[Reflex]:
        """Reactor meltdown imminent -> crewmate rushes to fix."""
        if player.imposter:
            return None

        if game.night_reactor:
            remaining = game.timers.get('reactor_meltdown').get_remaining_int()
            if remaining <= 20:
                return Reflex(
                    reflex_type=ReflexType.FIX_SABOTAGE,
                    decision=AIDecision(
                        action=AIAction.FIX_REACTOR,
                        reasoning=f"Reflex: reactor meltdown in {remaining}s!",
                    ),
                    reason=f"Reactor meltdown in {remaining}s",
                )

        return None

    @staticmethod
    def _check_opportunistic_kill(player, game) -> Optional[Reflex]:
        """Impostor alone with 1 crewmate, kill ready, no witnesses, past grace period."""
        # Grace period check
        game_time = time.time() - game.start_time
        grace = getattr(game.config.ai, 'early_game_grace_period', EARLY_GAME_GRACE)
        if game_time < grace:
            return None

        # Kill cooldown check
        if player.kill_timer > 0:
            return None

        # Opportunity cooldown check
        if player._opportunity_cooldown > 0:
            return None

        pathfinder = game.pathfinder
        vision_radius = game.config.ai.vision_radius
        my_pos = (player.pos.x, player.pos.y)

        nearby_crew = []
        witnesses = 0

        for other in game.ai_players:
            if other is player or not other.alive_status:
                continue

            other_pos = (other.pos.x, other.pos.y)
            dx = other_pos[0] - my_pos[0]
            dy = other_pos[1] - my_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > vision_radius:
                continue

            # Check LOS
            has_los = True
            if pathfinder and hasattr(pathfinder, 'has_line_of_sight'):
                has_los = pathfinder.has_line_of_sight(my_pos, other_pos)

            if not has_los:
                continue

            if other.imposter:
                continue  # Fellow impostor, not a threat

            if dist <= vision_radius * 0.6:
                nearby_crew.append(other)
            else:
                witnesses += 1

        # Only kill if exactly 1 crewmate nearby and 0 witnesses
        if len(nearby_crew) == 1 and witnesses == 0:
            target = nearby_crew[0]

            # Personality check: risk_tolerance gates opportunistic kills
            if hasattr(player, 'brain') and player.brain:
                personality = player.brain.get_personality()
                if hasattr(personality, 'risk_tolerance'):
                    import random
                    if random.random() > personality.risk_tolerance:
                        return None  # Personality says no

            player._opportunity_cooldown = OPPORTUNITY_COOLDOWN
            return Reflex(
                reflex_type=ReflexType.OPPORTUNISTIC_KILL,
                decision=AIDecision(
                    action=AIAction.KILL,
                    target_player=target.bot_colour,
                    reasoning=f"Reflex: alone with {target.bot_colour}, no witnesses",
                ),
                reason=f"Alone with {target.bot_colour}",
            )

        return None
