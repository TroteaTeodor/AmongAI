"""Parses LLM text responses into structured AIDecision objects."""

import re
from among_ai.ai.interfaces import AIAction, AIDecision
from among_ai.constants import ROOMS, TASK_DEFINITIONS, ALL_COLOURS


class ActionParser:
    """Parses free-text LLM responses into AIDecision objects."""

    # Patterns for action extraction
    _ACTION_PATTERNS = [
        (r'(?:^|\n)\s*MOVE_TO_ROOM\s+(.+)', AIAction.MOVE_TO_ROOM),
        (r'(?:^|\n)\s*DO_TASK\s+(.+)', AIAction.DO_TASK),
        (r'(?:^|\n)\s*KILL\s+(\w+)', AIAction.KILL),
        (r'(?:^|\n)\s*REPORT_BODY', AIAction.REPORT_BODY),
        (r'(?:^|\n)\s*CALL_MEETING', AIAction.CALL_MEETING),
        (r'(?:^|\n)\s*VENT', AIAction.VENT),
        (r'(?:^|\n)\s*SABOTAGE_LIGHTS', AIAction.SABOTAGE_LIGHTS),
        (r'(?:^|\n)\s*SABOTAGE_REACTOR', AIAction.SABOTAGE_REACTOR),
        (r'(?:^|\n)\s*FIX_LIGHTS', AIAction.FIX_LIGHTS),
        (r'(?:^|\n)\s*FIX_REACTOR', AIAction.FIX_REACTOR),
        (r'(?:^|\n)\s*FOLLOW_PLAYER\s+(\w+)', AIAction.FOLLOW_PLAYER),
        (r'(?:^|\n)\s*FLEE', AIAction.FLEE),
        (r'(?:^|\n)\s*IDLE', AIAction.IDLE),
    ]

    @staticmethod
    def parse(text: str) -> AIDecision:
        """Parse LLM response text into an AIDecision."""
        text_upper = text.strip()

        for pattern, action in ActionParser._ACTION_PATTERNS:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                return ActionParser._build_decision(action, match, text)

        # Fallback: try to extract any room name or action keyword
        decision = ActionParser._fuzzy_parse(text)
        if decision:
            return decision

        # Last resort: IDLE
        return AIDecision(
            action=AIAction.IDLE,
            reasoning=f"Could not parse: {text[:100]}",
        )

    @staticmethod
    def _build_decision(action: AIAction, match, full_text: str) -> AIDecision:
        """Build an AIDecision from a matched pattern."""
        reasoning = full_text.strip()[:200]
        target = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else None

        if action == AIAction.MOVE_TO_ROOM:
            room = ActionParser._match_room(target) if target else None
            return AIDecision(action=action, target_room=room, reasoning=reasoning)

        elif action == AIAction.DO_TASK:
            task = ActionParser._match_task(target) if target else None
            return AIDecision(action=action, target_task=task, reasoning=reasoning)

        elif action in (AIAction.KILL, AIAction.FOLLOW_PLAYER):
            colour = ActionParser._match_colour(target) if target else None
            return AIDecision(action=action, target_player=colour, reasoning=reasoning)

        else:
            return AIDecision(action=action, reasoning=reasoning)

    @staticmethod
    def _fuzzy_parse(text: str) -> AIDecision:
        """Try to extract intent from messy LLM output."""
        text_lower = text.lower()

        # Check for room names
        for room in ROOMS:
            if room.lower() in text_lower:
                if any(w in text_lower for w in ["go to", "move to", "head to", "walk to", "navigate"]):
                    return AIDecision(
                        action=AIAction.MOVE_TO_ROOM,
                        target_room=room,
                        reasoning=text[:200],
                    )

        # Check for task names
        for task in TASK_DEFINITIONS:
            if task.lower() in text_lower:
                if any(w in text_lower for w in ["do", "complete", "task", "work on"]):
                    return AIDecision(
                        action=AIAction.DO_TASK,
                        target_task=task,
                        reasoning=text[:200],
                    )

        # Check for kill
        if "kill" in text_lower:
            for colour in ALL_COLOURS:
                if colour.lower() in text_lower:
                    return AIDecision(
                        action=AIAction.KILL,
                        target_player=colour,
                        reasoning=text[:200],
                    )

        # Check for report
        if "report" in text_lower and "body" in text_lower:
            return AIDecision(action=AIAction.REPORT_BODY, reasoning=text[:200])

        if "sabotage" in text_lower:
            if "light" in text_lower:
                return AIDecision(action=AIAction.SABOTAGE_LIGHTS, reasoning=text[:200])
            if "reactor" in text_lower:
                return AIDecision(action=AIAction.SABOTAGE_REACTOR, reasoning=text[:200])

        return None

    @staticmethod
    def _match_room(text: str) -> str:
        """Fuzzy-match a room name from text."""
        if not text:
            return "Cafeteria"
        text_lower = text.lower().strip()
        for room in ROOMS:
            if room.lower() == text_lower or room.lower() in text_lower:
                return room
        # Partial match
        for room in ROOMS:
            if text_lower in room.lower():
                return room
        return text.strip().title()

    @staticmethod
    def _match_task(text: str) -> str:
        if not text:
            return None
        text_lower = text.lower().strip()
        for task in TASK_DEFINITIONS:
            if task.lower() == text_lower or task.lower() in text_lower:
                return task
        for task in TASK_DEFINITIONS:
            if text_lower in task.lower():
                return task
        return text.strip()

    @staticmethod
    def _match_colour(text: str) -> str:
        if not text:
            return None
        text_lower = text.lower().strip()
        for colour in ALL_COLOURS:
            if colour.lower() == text_lower:
                return colour
        for colour in ALL_COLOURS:
            if colour.lower() in text_lower:
                return colour
        return text.strip().title()

    @staticmethod
    def parse_vote(text: str) -> str:
        """Parse a vote response. Returns colour name or None for skip."""
        text = text.strip().upper()
        if "SKIP" in text:
            return None
        for colour in ALL_COLOURS:
            if colour.upper() in text:
                return colour
        return None
