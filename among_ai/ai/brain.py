"""AIBrain: the decision-making coordinator. Uses LLM + fallback heuristics."""

import random
from typing import Optional

from among_ai.ai.interfaces import IAIBrain, ILLMProvider, GameStateSnapshot, AIAction, AIDecision
from among_ai.ai.personality import Personality
from among_ai.ai.prompt_builder import PromptBuilder
from among_ai.ai.action_parser import ActionParser
from among_ai.constants import ROOMS, TASK_DEFINITIONS


class AIBrain(IAIBrain):
    """Concrete AI brain using LLM for decisions with rule-based fallback."""

    MAX_HISTORY = 40  # Max messages in history (mix of events + decisions)

    def __init__(self, colour: str, provider: ILLMProvider, personality: Personality):
        self.colour = colour
        self.provider = provider
        self.personality = personality
        self._role = "crewmate"
        # Persistent conversation history shared across all LLM calls
        self._history: list[dict] = []

    def set_role(self, role: str):
        self._role = role

    def _trim_history(self):
        """Keep history bounded."""
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]

    def _add_event(self, event_text: str):
        """Inject a game event into history so the LLM remembers it."""
        self._history.append({
            "role": "user",
            "content": f"[GAME EVENT] {event_text}"
        })
        self._trim_history()

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict]:
        """Build full message list: system + history + current prompt."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _record_exchange(self, user_summary: str, assistant_response: str):
        """Record a concise summary of the exchange (not the raw prompt)."""
        self._history.append({"role": "user", "content": user_summary})
        self._history.append({"role": "assistant", "content": assistant_response})
        self._trim_history()

    async def decide_action(self, game_state: GameStateSnapshot) -> AIDecision:
        """Ask the LLM what to do, with full conversation history."""
        if not self.provider or not self.provider.is_available():
            return self.get_fallback_action(game_state)

        try:
            system_prompt = PromptBuilder.build_system_prompt(
                self._role, self.personality
            )
            user_prompt = PromptBuilder.build_action_prompt(game_state)

            messages = self._build_messages(system_prompt, user_prompt)

            response = await self.provider.generate_with_messages(
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )

            # Store a CONCISE summary, not the full game state dump
            summary = (
                f"[Turn] Room: {game_state.my_room} | "
                f"Visible: {', '.join(p.colour for p in game_state.visible_players) or 'nobody'} | "
                f"Tasks: {game_state.my_tasks_completed}/{game_state.my_tasks_total}"
            )
            if game_state.sabotage_active:
                summary += f" | SABOTAGE: {game_state.sabotage_active}"
            if game_state.visible_bodies:
                summary += f" | BODIES: {', '.join(b.colour for b in game_state.visible_bodies)}"

            self._record_exchange(summary, response.text.strip())

            decision = ActionParser.parse(response.text)
            return decision

        except Exception as e:
            print(f"[{self.colour}] LLM error: {e}")
            return self.get_fallback_action(game_state)

    async def decide_opportunity(self, target_colour: str, target_room: str,
                                  witnesses: list[str], kill_ready: bool) -> AIDecision:
        """Quick LLM prompt: impostor spotted a crewmate — pursue or ignore?"""
        if not self.provider or not self.provider.is_available():
            # Fallback: chase if kill ready and no witnesses
            if kill_ready and len(witnesses) == 0:
                return AIDecision(
                    action=AIAction.KILL, target_player=target_colour,
                    reasoning="Fallback: alone with target, kill ready"
                )
            return AIDecision(action=AIAction.IDLE, reasoning="Fallback: ignore opportunity")

        try:
            system_prompt = (
                f"You are {self.colour}, an IMPOSTOR in Among Us. "
                f"You just spotted a crewmate. Make a quick tactical decision. "
                f"Reply with EXACTLY one action on its own line, then a brief reason.\n"
                f"Options:\n"
                f"  KILL {target_colour} — if you think it's safe to kill right now\n"
                f"  FOLLOW_PLAYER {target_colour} — stalk them and wait for a safe moment\n"
                f"  IDLE — ignore this opportunity and continue what you were doing\n"
            )

            witness_str = ", ".join(witnesses) if witnesses else "nobody"
            user_prompt = (
                f"You see {target_colour} in {target_room}.\n"
                f"Other players also nearby: {witness_str}\n"
                f"Kill cooldown ready: {'YES' if kill_ready else 'NO'}\n"
                f"What do you do?"
            )

            messages = self._build_messages(system_prompt, user_prompt)

            response = await self.provider.generate_with_messages(
                messages=messages, temperature=0.8, max_tokens=100,
            )

            self._record_exchange(
                f"[Opportunity] Spotted {target_colour} in {target_room}, witnesses: {witness_str}",
                response.text.strip()
            )

            decision = ActionParser.parse(response.text)
            return decision

        except Exception as e:
            print(f"[{self.colour}] Opportunity prompt error: {e}")
            return AIDecision(action=AIAction.IDLE, reasoning="Error, ignoring")

    async def generate_chat_message(self, game_state: GameStateSnapshot,
                                     chat_history: list, phase: str) -> str:
        """Generate a chat message for meetings, using shared history."""
        if not self.provider or not self.provider.is_available():
            return self._fallback_chat(game_state)

        try:
            system_prompt = PromptBuilder.build_system_prompt(
                self._role, self.personality
            )
            user_prompt = PromptBuilder.build_chat_prompt(
                game_state, chat_history, phase
            )

            messages = self._build_messages(system_prompt, user_prompt)

            response = await self.provider.generate_with_messages(
                messages=messages,
                temperature=0.8,
                max_tokens=150,
            )

            text = response.text.strip()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            if len(text) > 200:
                text = text[:197] + "..."

            # Record concisely
            self._record_exchange(
                f"[Meeting - {phase}] You spoke in the discussion.",
                text
            )
            return text

        except Exception as e:
            print(f"[{self.colour}] Chat LLM error: {e}")
            return self._fallback_chat(game_state)

    async def decide_vote(self, game_state: GameStateSnapshot,
                           chat_history: list, alive_players: list) -> Optional[str]:
        """Decide who to vote for, using shared history."""
        if not self.provider or not self.provider.is_available():
            return self._fallback_vote(game_state, alive_players)

        try:
            system_prompt = PromptBuilder.build_system_prompt(
                self._role, self.personality
            )
            user_prompt = PromptBuilder.build_vote_prompt(
                game_state, chat_history, alive_players
            )

            messages = self._build_messages(system_prompt, user_prompt)

            response = await self.provider.generate_with_messages(
                messages=messages,
                temperature=0.5,
                max_tokens=50,
            )

            vote_result = ActionParser.parse_vote(response.text)

            # Record the vote in history so they remember it
            vote_text = vote_result if vote_result else "SKIP"
            self._record_exchange(
                f"[Voting] Time to vote. Alive: {', '.join(alive_players)}",
                f"I vote for {vote_text}."
            )
            return vote_result

        except Exception as e:
            print(f"[{self.colour}] Vote LLM error: {e}")
            return self._fallback_vote(game_state, alive_players)

    def get_fallback_action(self, game_state: GameStateSnapshot) -> AIDecision:
        """Rule-based fallback when LLM is unavailable."""
        # Priority 1: Report visible body
        if game_state.visible_bodies:
            return AIDecision(action=AIAction.REPORT_BODY, reasoning="Fallback: found body")

        # Priority 2: Fix active sabotage
        if game_state.sabotage_active == "reactor":
            return AIDecision(
                action=AIAction.MOVE_TO_ROOM,
                target_room="Reactor",
                reasoning="Fallback: fix reactor",
            )
        if game_state.sabotage_active == "lights" and self._role == "crewmate":
            return AIDecision(
                action=AIAction.MOVE_TO_ROOM,
                target_room="Electrical",
                reasoning="Fallback: fix lights",
            )

        if self._role == "impostor":
            return self._impostor_fallback(game_state)
        else:
            return self._crewmate_fallback(game_state)

    def _crewmate_fallback(self, game_state: GameStateSnapshot) -> AIDecision:
        """Crewmate fallback: go do tasks."""
        remaining = [t for t in game_state.my_assigned_tasks
                    if t not in game_state.my_completed_tasks]
        if remaining:
            task = random.choice(remaining)
            if task in TASK_DEFINITIONS:
                task_room = TASK_DEFINITIONS[task]["room"]
                return AIDecision(
                    action=AIAction.MOVE_TO_ROOM,
                    target_room=task_room,
                    target_task=task,
                    reasoning=f"Fallback: go to {task}",
                )
        # No tasks left, wander
        room = random.choice(list(ROOMS.keys()))
        return AIDecision(
            action=AIAction.MOVE_TO_ROOM,
            target_room=room,
            reasoning="Fallback: wander",
        )

    def _impostor_fallback(self, game_state: GameStateSnapshot) -> AIDecision:
        """Impostor fallback: hunt or fake tasks."""
        # If kill is ready and someone is nearby alone, kill
        if (game_state.kill_cooldown_remaining <= 0
                and len(game_state.visible_players) == 1):
            target = game_state.visible_players[0]
            return AIDecision(
                action=AIAction.KILL,
                target_player=target.colour,
                reasoning="Fallback: kill isolated target",
            )

        # Sabotage if cooldown ready
        if game_state.sabotage_cooldown_remaining <= 0:
            if random.random() < self.personality.aggression:
                action = random.choice([AIAction.SABOTAGE_LIGHTS, AIAction.SABOTAGE_REACTOR])
                return AIDecision(action=action, reasoning="Fallback: sabotage")

        # Pretend to do tasks
        room = random.choice(list(ROOMS.keys()))
        return AIDecision(
            action=AIAction.MOVE_TO_ROOM,
            target_room=room,
            reasoning="Fallback: fake task / patrol",
        )

    def _fallback_chat(self, game_state: GameStateSnapshot) -> str:
        """Generate a simple chat message without LLM."""
        if self._role == "impostor":
            options = [
                "I was doing tasks in Electrical.",
                "I didn't see anything suspicious.",
                "Has anyone checked Security?",
                "I think we should skip this round.",
                "Where was everyone?",
            ]
        else:
            options = [
                "I was doing my tasks.",
                "Did anyone see anything?",
                "Let's think about this carefully.",
                "Where was everyone when it happened?",
                "I'm not sure who to vote for.",
            ]
        return random.choice(options)

    def _fallback_vote(self, game_state: GameStateSnapshot, alive_players: list) -> Optional[str]:
        """Fallback voting logic."""
        # Vote for most suspicious or skip
        candidates = [c for c in alive_players if c != self.colour]
        if self._role == "impostor":
            # Vote randomly to blend in
            if random.random() < 0.7 and candidates:
                return random.choice(candidates)
            return None  # Skip
        else:
            # Skip unless we have strong suspicion
            if random.random() < 0.4 and candidates:
                return random.choice(candidates)
            return None

    def get_personality(self) -> Personality:
        return self.personality
