"""Background thread AI decision coordinator.
Bridges the 60fps game loop with slow LLM calls using a producer-consumer pattern."""

import asyncio
import threading
import time
from typing import Optional, Callable

from among_ai.ai.interfaces import GameStateSnapshot, AIAction


class DecisionLoop:
    """Runs AI decision-making in a background thread."""

    def __init__(self, ai_players: list, game_state_provider: Callable,
                 decision_interval: float = 3.0, max_concurrent: int = 3):
        self.ai_players = ai_players
        self.get_game_state = game_state_provider
        self.decision_interval = decision_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.meeting_active = False
        self._meeting_chat_callback = None
        self._meeting_vote_callback = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_loop())
        except Exception as e:
            print(f"[DecisionLoop] Error: {e}")
        finally:
            loop.close()

    async def _async_loop(self):
        while self.running:
            try:
                if self.meeting_active:
                    await asyncio.sleep(0.5)
                else:
                    await self._process_decisions()
            except Exception as e:
                print(f"[DecisionLoop] Tick error: {e}")
            await asyncio.sleep(0.1)

    async def _process_decisions(self):
        """Process movement/action decisions for AI players."""
        game_state = self.get_game_state()
        if game_state is None:
            return

        now = time.time()
        pending = []
        for player in self.ai_players:
            if not player.alive_status:
                continue
            if player.brain is None:
                continue

            # Goal Persistence: If player is busy moving or doing a task, skip decision
            # UNLESS they have been idle too long or caught in a loop
            # Or if checking for urgent events happened in update() and reset last_decision_time
            if player.movement_ctrl and player.movement_ctrl.is_moving:
                # If moving, only interrupt if it's been a LONG time (stuck?)
                if now - player.last_decision_time < 10.0:
                    continue
            
            if player.is_doing_task:
                 if now - player.last_decision_time < 5.0:
                    continue

            if now - player.last_decision_time >= self.decision_interval:
                pending.append(player)

        # Process in batches
        for i in range(0, len(pending), self.max_concurrent):
            batch = pending[i:i + self.max_concurrent]
            tasks = [self._get_decision(p, game_state) for p in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _get_decision(self, player, game_state: GameStateSnapshot):
        """Get a single decision for one AI player."""
        try:
            # Build player-specific state snapshot
            player_state = self._personalize_state(game_state, player)

            decision = await asyncio.wait_for(
                player.brain.decide_action(player_state),
                timeout=15.0,  # Free models can be slow
            )
            player.action_queue.append(decision)
            player.last_decision_time = time.time()

        except asyncio.TimeoutError:
            print(f"[{player.bot_colour}] Decision timeout, using fallback")
            fallback = player.brain.get_fallback_action(
                self._personalize_state(game_state, player)
            )
            player.action_queue.append(fallback)
            player.last_decision_time = time.time()

        except Exception as e:
            print(f"[{player.bot_colour}] Decision error: {e}")
            player.last_decision_time = time.time()

    def _personalize_state(self, base_state: GameStateSnapshot,
                           player) -> GameStateSnapshot:
        """Create a player-specific view of the game state."""
        from among_ai.ai.interfaces import PlayerSnapshot

        my_room = "Unknown"
        if hasattr(player, 'game') and hasattr(player.game, 'pathfinder'):
            pf = player.game.pathfinder
            if pf:
                my_room = pf.get_room_at((player.pos.x, player.pos.y))

        # Get memory summary
        memory_summary = ""
        if player.memory:
            memory_summary = player.memory.summarize_for_prompt()

        # Determine visible players/bodies via vision
        visible_players = []
        visible_bodies = []
        if hasattr(player, 'vision') and player.vision:
            visible_players, visible_bodies = player.vision.scan_and_record(
                (player.pos.x, player.pos.y),
                base_state.all_players if hasattr(base_state, '_raw_players') else [],
                base_state.visible_bodies if hasattr(base_state, '_raw_bodies') else [],
                base_state.sabotage_active == "lights",
                player.memory,
                player.game.pathfinder if hasattr(player.game, 'pathfinder') else None,
            )

        completed_tasks = player.completed_task_names
        assigned_tasks = [t.name for t in player.assigned_tasks]

        # Get AI's individual kill cooldown if available
        kill_cd = base_state.kill_cooldown_remaining
        if hasattr(player, 'kill_timer'):
            kill_cd = player.kill_timer

        return GameStateSnapshot(
            game_time=base_state.game_time,
            phase=base_state.phase,
            sabotage_active=base_state.sabotage_active,
            reactor_countdown=base_state.reactor_countdown,
            my_colour=player.bot_colour,
            my_position=(player.pos.x, player.pos.y),
            my_room=my_room,
            my_role="impostor" if player.imposter else "crewmate",
            my_tasks_completed=len(completed_tasks),
            my_tasks_total=len(assigned_tasks),
            my_assigned_tasks=assigned_tasks,
            my_completed_tasks=completed_tasks,
            kill_cooldown_remaining=kill_cd,
            sabotage_cooldown_remaining=base_state.sabotage_cooldown_remaining,
            meeting_cooldown_remaining=base_state.meeting_cooldown_remaining,
            can_call_meeting=base_state.can_call_meeting,
            is_near_emergency_button=self._is_near(
                player.pos, (3284, 669), 250),
            is_near_vent=self._is_near_any_vent(player.pos),
            is_in_vent=player.is_in_vent,
            visible_players=[
                PlayerSnapshot(
                    colour=vp.get("colour", ""),
                    position=vp.get("position", (0, 0)),
                    room=vp.get("room", "Unknown"),
                    alive=vp.get("alive", True),
                    is_visible=True,
                ) for vp in (visible_players if isinstance(visible_players, list) else [])
            ],
            visible_bodies=[
                PlayerSnapshot(
                    colour=b.get("colour", ""),
                    position=b.get("position", (0, 0)),
                    room=b.get("room", "Unknown"),
                    alive=False,
                ) for b in (visible_bodies if isinstance(visible_bodies, list) else [])
            ],
            all_players=base_state.all_players,
            memory_summary=memory_summary,
            chat_history=base_state.chat_history,
        )

    def _is_near(self, pos, target, radius):
        import math
        return math.sqrt((pos.x - target[0])**2 + (pos.y - target[1])**2) <= radius

    def _is_near_any_vent(self, pos):
        from among_ai.constants import VENT_LOCATIONS
        import math
        for vx, vy in VENT_LOCATIONS:
            if math.sqrt((pos.x - vx)**2 + (pos.y - vy)**2) <= 100:
                return True
        return False

    async def run_meeting_discussion(self, game_state, meeting_manager):
        """Run AI discussion during a meeting. Called from main thread via queue."""
        alive_players = [p for p in self.ai_players if p.alive_status]
        if not alive_players:
            return

        # Each player takes a turn speaking (up to 3 rounds)
        for round_num in range(3):
            import random
            speaking_order = list(alive_players)
            random.shuffle(speaking_order)

            for player in speaking_order:
                if not self.meeting_active:
                    return
                if player.brain is None:
                    continue

                try:
                    player_state = self._personalize_state(game_state, player)
                    message = await asyncio.wait_for(
                        player.brain.generate_chat_message(
                            player_state,
                            meeting_manager.chat_messages,
                            "discussion",
                        ),
                        timeout=8.0,
                    )
                    meeting_manager.add_chat_message(player.bot_colour, message)
                except Exception as e:
                    print(f"[{player.bot_colour}] Chat error: {e}")
                    meeting_manager.add_chat_message(
                        player.bot_colour, "..."
                    )
                await asyncio.sleep(0.3)

    async def run_meeting_votes(self, game_state, meeting_manager, alive_colours):
        """Collect votes from all AI players."""
        for player in self.ai_players:
            if not player.alive_status or player.brain is None:
                continue
            try:
                player_state = self._personalize_state(game_state, player)
                vote = await asyncio.wait_for(
                    player.brain.decide_vote(
                        player_state,
                        meeting_manager.chat_messages,
                        alive_colours,
                    ),
                    timeout=6.0,
                )
                meeting_manager.cast_vote(player.bot_colour, vote)
            except Exception as e:
                print(f"[{player.bot_colour}] Vote error: {e}")
                meeting_manager.cast_vote(player.bot_colour, None)
