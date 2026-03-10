"""Builds role-specific prompts for LLM calls."""

from among_ai.ai.interfaces import GameStateSnapshot
from among_ai.ai.personality import Personality


class PromptBuilder:
    """Constructs system and user prompts for different AI decision types."""

    @staticmethod
    def build_system_prompt(role: str, personality: Personality) -> str:
        """Build the system prompt for an AI player."""
        base = (
            "You are a player in Among AI, a social-deduction game similar to Among Us. "
            "You are on a spaceship with other AI players.\n\n"
            "CRITICAL OUTPUT RULES — follow these exactly:\n"
            "• For ACTION decisions: reply with the action line ONLY (e.g. 'MOVE_TO_ROOM Cafeteria'), "
            "then on the next line a brief reason. No JSON, no lists, no extra commentary.\n"
            "• For CHAT messages: reply with your spoken line ONLY — plain text, 1-2 sentences. "
            "Do NOT include your name, brackets, labels, JSON, or any prefix.\n"
            "• Stay fully in character at all times. Do not reference being an AI or being prompted.\n\n"
        )

        if role == "crewmate":
            base += (
                "You are a CREWMATE. Your goals:\n"
                "1. Complete your assigned tasks by going to their locations\n"
                "2. Watch for suspicious behavior from other players\n"
                "3. Report dead bodies you find\n"
                "4. Vote out the impostor during meetings\n"
                "5. Fix sabotages (lights, reactor) when they happen\n\n"
                "You do NOT know who the impostor is. Be observant and trust your observations.\n"
            )
        else:
            base += (
                "You are the IMPOSTOR. Your goals:\n"
                "1. Kill crewmates without being seen (check visible players before killing)\n"
                "2. Pretend to do tasks to blend in\n"
                "3. Sabotage lights/reactor to create chaos and separate groups\n"
                "4. Use vents to move quickly and escape\n"
                "5. Lie convincingly during meetings — deflect suspicion onto others\n"
                "6. Never kill when you can see other players (they can see you too)\n\n"
                "Be strategic. Kill only when isolated with a target.\n"
            )

        base += "\n" + personality.to_system_prompt_section()
        return base

    @staticmethod
    def build_action_prompt(game_state: GameStateSnapshot) -> str:
        """Build the user prompt for an action decision."""
        lines = ["=== CURRENT GAME STATE ==="]
        lines.append(f"You are: {game_state.my_colour} ({game_state.my_role})")
        lines.append(f"Location: {game_state.my_room}")

        # Alive/dead players
        alive = [p.colour for p in game_state.all_players if p.alive]
        dead = [p.colour for p in game_state.all_players if not p.alive]
        lines.append(f"Alive: {', '.join(alive)} ({len(alive)} players)")
        if dead:
            lines.append(f"Dead: {', '.join(dead)}")

        # Sabotage
        if game_state.sabotage_active:
            lines.append(f"\nSABOTAGE ACTIVE: {game_state.sabotage_active.upper()}")
            if game_state.reactor_countdown:
                lines.append(f"Reactor meltdown in: {game_state.reactor_countdown}s!")

        # Visible players
        visible_text = "None"
        if game_state.visible_players:
            # Add distance info
            visible_entries = []
            for vp in game_state.visible_players:
                visible_entries.append(f"- {vp.colour} in {vp.room} ({int(getattr(vp, 'distance', 0))} units away)")
            visible_text = "\n".join(visible_entries)
            
        lines.append("\n--- WHAT YOU SEE ---")
        lines.append(f"VISIBLE PLAYERS (Who you can see RIGHT NOW):\n{visible_text}")
        lines.append("(If this list is not 'None', you are NOT alone. You can see these players.)")

        # Visible bodies
        if game_state.visible_bodies:
            lines.append("\nDEAD BODIES VISIBLE:")
            for body in game_state.visible_bodies:
                lines.append(f"  {body.colour}'s body in {body.room}!")

        # Task status
        lines.append(f"\n--- YOUR STATUS ---")
        lines.append(f"Tasks: {game_state.my_tasks_completed}/{game_state.my_tasks_total}")
        if game_state.my_assigned_tasks:
            remaining = [t for t in game_state.my_assigned_tasks
                        if t not in game_state.my_completed_tasks]
            if remaining:
                lines.append(f"Remaining tasks: {', '.join(remaining)}")

        # Cooldowns (impostor)
        if game_state.my_role == "impostor":
            if game_state.kill_cooldown_remaining > 0:
                lines.append(f"Kill cooldown: {int(game_state.kill_cooldown_remaining)}s")
            else:
                lines.append("Kill: READY")
            if game_state.sabotage_cooldown_remaining > 0:
                lines.append(f"Sabotage cooldown: {int(game_state.sabotage_cooldown_remaining)}s")
            else:
                lines.append("Sabotage: READY")
            if game_state.is_near_vent:
                lines.append("You are near a vent (can use it)")

        # Emergency button
        if game_state.can_call_meeting and game_state.is_near_emergency_button:
            lines.append("Emergency button: AVAILABLE (you're near it)")
        elif game_state.meeting_cooldown_remaining > 0:
            lines.append(f"Meeting cooldown: {int(game_state.meeting_cooldown_remaining)}s")

        # Current intent/goal
        if game_state.current_intent_summary:
            lines.append(f"\n--- CURRENT GOAL ---")
            lines.append(f"Current goal: {game_state.current_intent_summary}")
            lines.append("(You can continue this goal or choose a new one.)")

        # Memory
        if game_state.memory_summary:
            lines.append(f"\n--- MEMORY ---\n{game_state.memory_summary}")

        # Available actions
        lines.append("\n--- CHOOSE AN ACTION ---")
        lines.append("Reply with EXACTLY this format (nothing else):")
        lines.append("  ACTION_NAME target")
        lines.append("  Reason: one short sentence why")
        lines.append("")
        lines.append("DO NOT output JSON, lists, explanations, or multiple actions.")
        lines.append("Valid actions:")
        lines.append("")

        actions = [
            "MOVE_TO_ROOM <room_name>  (rooms: Cafeteria, Medbay, Security, Reactor, Upper Engine, Lower Engine, Electrical, Storage, Admin, Communications, Oxygen, Navigation, Weapons)",
            "IDLE  (wait here briefly)",
        ]
        if game_state.my_role == "crewmate" or game_state.my_role == "impostor":
            actions.append("DO_TASK <task_name>  (must be at or near the task location)")

        if game_state.visible_bodies:
            actions.append("REPORT_BODY  (report the dead body you see)")

        if game_state.is_near_emergency_button and game_state.can_call_meeting:
            actions.append("CALL_MEETING  (press emergency button)")

        if game_state.my_role == "impostor":
            if game_state.visible_players:
                actions.append("KILL <colour>  (kill a nearby player)")
            if game_state.is_near_vent:
                actions.append("VENT  (enter/exit vent)")
            if game_state.sabotage_cooldown_remaining <= 0:
                actions.append("SABOTAGE_LIGHTS  (turn off lights)")
                actions.append("SABOTAGE_REACTOR  (start reactor meltdown)")

        if game_state.sabotage_active == "lights":
            actions.append("FIX_LIGHTS  (must be at Electrical)")
        if game_state.sabotage_active == "reactor":
            actions.append("FIX_REACTOR  (must be at Reactor)")

        for action in actions:
            lines.append(f"  {action}")

        return "\n".join(lines)

    @staticmethod
    def build_chat_prompt(game_state: GameStateSnapshot,
                          chat_history: list, phase: str) -> str:
        """Build prompt for generating a chat message during meetings."""
        lines = ["=== EMERGENCY MEETING ==="]
        lines.append(f"You are: {game_state.my_colour} ({game_state.my_role})")
        lines.append(f"You were in: {game_state.my_room} when the meeting was called")

        # Meeting trigger context
        if game_state.meeting_trigger == "report":
            lines.append(f"Meeting reason: {game_state.meeting_caller} REPORTED a dead body")
            if game_state.meeting_body_colour:
                lines.append(f"Victim: {game_state.meeting_body_colour}")
            if game_state.meeting_body_location:
                lines.append(f"Body found in: {game_state.meeting_body_location}")
        elif game_state.meeting_trigger == "button":
            lines.append(f"Meeting reason: {game_state.meeting_caller} pressed the EMERGENCY BUTTON")
        else:
            lines.append("Meeting reason: Unknown")

        alive = [p.colour for p in game_state.all_players if p.alive]
        dead = [p.colour for p in game_state.all_players if not p.alive]
        lines.append(f"Alive: {', '.join(alive)}")
        if dead:
            lines.append(f"Dead: {', '.join(dead)}")

        if game_state.memory_summary:
            lines.append(f"\nYour memory:\n{game_state.memory_summary}")

        if chat_history:
            lines.append("\n--- DISCUSSION SO FAR ---")
            for msg in chat_history[-15:]:  # Last 15 messages
                lines.append(f"[{msg['speaker']}]: {msg['text']}")

        lines.append(f"\nPhase: {phase}")
        if game_state.my_role == "impostor":
            lines.append(
                "\nRemember: You are the IMPOSTOR. Deflect suspicion. "
                "Accuse someone else if needed. Don't reveal yourself. "
                "Be careful about self-reporting bodies you killed — it can look suspicious."
            )
        else:
            lines.append(
                "\nShare your observations. Who is suspicious? What did you see?"
            )

        lines.append(
            "\nWrite your chat message now. "
            "OUTPUT ONLY the spoken words — no name prefix, no brackets, no labels. "
            "1-2 sentences maximum. Stay fully in character."
        )
        return "\n".join(lines)

    @staticmethod
    def build_vote_prompt(game_state: GameStateSnapshot,
                          chat_history: list, alive_players: list) -> str:
        """Build prompt for voting decision."""
        lines = ["=== VOTING TIME ==="]
        lines.append(f"You are: {game_state.my_colour} ({game_state.my_role})")
        lines.append(f"Alive players: {', '.join(alive_players)}")

        # Meeting trigger context
        if game_state.meeting_trigger == "report":
            lines.append(f"This meeting was called because {game_state.meeting_caller} reported a body.")
            if game_state.meeting_body_colour:
                lines.append(f"Victim: {game_state.meeting_body_colour}")
            if game_state.meeting_body_location:
                lines.append(f"Body was found in: {game_state.meeting_body_location}")
        elif game_state.meeting_trigger == "button":
            lines.append(f"This meeting was called by {game_state.meeting_caller} using the emergency button.")

        if chat_history:
            lines.append("\n--- DISCUSSION SUMMARY ---")
            for msg in chat_history[-20:]:
                lines.append(f"[{msg['speaker']}]: {msg['text']}")

        if game_state.memory_summary:
            lines.append(f"\nYour memory:\n{game_state.memory_summary}")

        if game_state.my_role == "impostor":
            lines.append(
                "\nYou are the IMPOSTOR. Vote for someone to deflect suspicion. "
                "Don't vote for yourself."
            )

        lines.append(
            f"\nVote decision: reply with ONE word only — a colour name or SKIP. "
            f"Valid options: {', '.join(alive_players)}, SKIP. "
            f"No explanation, no punctuation, just the single word."
        )
        return "\n".join(lines)
