"""Core game engine: the main game loop that ties everything together.
Refactored from the original 3277-line game.py monolith."""

import os
import sys
import math
import time
import random
import pygame as pg
from os import path

from among_ai.constants import (
    WIDTH, HEIGHT, FPS, TITLE, FONT, TILESIZE, BGCOLOR,
    ALL_COLOURS, ROOMS, VENT_LOCATIONS, TASK_DEFINITIONS,
    PLAYER_SPAWN_POSITIONS, BOT_SPAWN_POSITIONS,
    EMERGENCY_BUTTON_POS, EMERGENCY_BUTTON_RADIUS,
    COLLISION_OBJECT_NAMES, ITEM_IMAGES,
    KILL_COOLDOWN, SABOTAGE_COOLDOWN, REACTOR_MELTDOWN_TIME,
    LIGHT_MASK, NIGHT_COLOR, LIGHT_RADIUS,
    PLAYER_DISPLAY_COLORS, WHITE, BLACK,
    NUM_TASKS_TO_WIN, PLAYER_SPEED,
)
from among_ai.core.sprites import Player, AIPlayer, Wall, Obstacle, Item
from among_ai.core.tilemap import TiledMap, Camera
from among_ai.core.assets import AssetManager
from among_ai.core.timer_manager import TimerManager
from among_ai.core.tasks import TaskManager
from among_ai.core.meeting import MeetingManager, MeetingPhase
from among_ai.core.sound_manager import SoundManager
from among_ai.ai.interfaces import AIAction, GameStateSnapshot, PlayerSnapshot
from among_ai.ai.brain import AIBrain
from among_ai.ai.memory import Memory
from among_ai.ai.vision import Vision
from among_ai.ai.personality import Personality
from among_ai.ai.decision_loop import DecisionLoop
from among_ai.ai.pathfinding.nav_graph import NavGraph
from among_ai.ai.pathfinding.movement_controller import MovementController
from among_ai.chat.chat_renderer import ChatRenderer
from among_ai.chat.chat_log import ChatLog
from among_ai.config import Config


class GameEngine:
    """Main game engine. Manages game loop, AI players, rendering, and state."""

    def __init__(self, config: Config):
        pg.init()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()
        self.config = config
        self.dt = 0
        self.playing = False
        self.game_over_flag = False
        self.game_result = None  # "crew_wins", "impostor_wins"

        # Folders
        self.game_folder = path.dirname(path.dirname(path.dirname(__file__)))
        self.map_folder = path.join(self.game_folder, 'Assets', 'Maps')
        self.img_folder = path.join(self.game_folder, 'Assets', 'Images')
        self.sound_folder = path.join(self.game_folder, 'Assets', 'Sounds')
        self.items_img_folder = path.join(self.img_folder, 'Items')

        # Game state
        self.emergency = False
        self.night = False         # Lights sabotaged
        self.night_reactor = False  # Reactor sabotaged
        self.isdoingTask = False
        self.invisible_play_count = 0
        self.paused = False

        # Managers
        self.timers = TimerManager()
        self.task_manager = TaskManager(
            task_duration_min=config.ai.task_duration_min,
            task_duration_max=config.ai.task_duration_max,
        )
        self.meeting_manager = MeetingManager(
            discussion_time=config.game.discussion_time,
            voting_time=config.game.voting_time,
        )
        self.chat_renderer = ChatRenderer()
        self.chat_log = ChatLog()

        # Assets
        self.asset_manager = AssetManager()
        self.sound_manager = SoundManager(self.sound_folder)

        # Pathfinding
        self.pathfinder = NavGraph()

        # AI
        self.ai_players: list[AIPlayer] = []
        self.decision_loop = None
        self._game_state_snapshot = None
        self._snapshot_time = 0

        # Sprite groups
        self.all_sprites = pg.sprite.LayeredUpdates()
        self.walls = pg.sprite.Group()
        self.bots = pg.sprite.Group()
        self.items = pg.sprite.Group()

        # Invisible player image
        self.invisible_player_image = None

        # Item images dict
        self.item_images = {}

        # Player (for camera follow in spectator mode)
        self.player = None
        self.camera = None

        # Sound stubs (for sprite compatibility)
        self.foot_sounds = {'footsteps': []}

        # Game start time
        self.start_time = 0

        # Spectator camera control
        self.spectator_target_idx = 0

        # Event log for display
        self.event_log: list[str] = []

    def load_data(self):
        """Load all game assets and build navigation graph."""
        # Load player sprites
        self.asset_manager.load_all()

        # Load sounds
        self.sound_manager.load_all()
        self.foot_sounds = {'footsteps': self.sound_manager.foot_sounds}

        # Load tilemap
        tilemap = TiledMap(path.join(self.map_folder, 'map.tmx'))
        self.map_img = tilemap.make_map()
        self.map_rect = self.map_img.get_rect()

        # Build navigation graph from collision data
        self.pathfinder.build_from_tilemap(tilemap)

        # Load item images
        for name, filename in ITEM_IMAGES.items():
            img_path = path.join(self.items_img_folder, filename)
            if os.path.exists(img_path):
                self.item_images[name] = pg.image.load(img_path).convert_alpha()

        # Load invisible player image
        invis_path = path.join(self.img_folder, 'Player', 'invisble3.png')
        if os.path.exists(invis_path):
            self.invisible_player_image = pg.image.load(invis_path).convert_alpha()
            self.invisible_player_image = pg.transform.scale(
                self.invisible_player_image, (64, 86)
            ).convert_alpha()

        # Load light mask for fog of war
        env_path = path.join(self.img_folder, 'Environment')
        mask_path = path.join(env_path, LIGHT_MASK)
        if os.path.exists(mask_path):
            self.light_mask = pg.image.load(mask_path).convert_alpha()
            self.light_mask = pg.transform.scale(self.light_mask, LIGHT_RADIUS)
        else:
            self.light_mask = None

        # Dim screen for overlays
        self.dim_screen = pg.Surface(self.screen.get_size()).convert_alpha()
        self.dim_screen.fill((0, 0, 0, 180))

        # Spawn map obstacles from tilemap objects
        for obj in tilemap.get_collision_objects():
            if obj['name'] in COLLISION_OBJECT_NAMES or obj['name'] is None:
                Obstacle(self, obj['x'], obj['y'], obj['width'], obj['height'])
            if obj['name'] in ['vent']:
                center = (obj['x'] + obj['width'] // 2, obj['y'] + obj['height'] // 2)
                if 'vent' in self.item_images:
                    Item(self, center, 'vent')
            if obj['name'] in ['emerg_btn']:
                center = (obj['x'] + obj['width'] // 2, obj['y'] + obj['height'] // 2)
                if 'emerg_btn' in self.item_images:
                    Item(self, center, 'emerg_btn')

    def setup_ai_game(self):
        """Set up an AI-only game (Watch AI mode) or AI opponents."""
        mode = self.config.game.mode
        num_players = min(self.config.game.num_players, len(ALL_COLOURS))
        num_impostors = self.config.game.num_impostors

        # Determine available colours (remove player's colour in play_with_ai)
        available_colours = list(ALL_COLOURS[:num_players])

        # Create AI players at spawn positions
        spawns = list(PLAYER_SPAWN_POSITIONS) + list(BOT_SPAWN_POSITIONS)
        random.shuffle(spawns)

        for i, colour in enumerate(available_colours):
            spawn = spawns[i % len(spawns)]
            ai_player = AIPlayer(
                self, spawn[0], spawn[1],
                bot_id=i, colour=colour,
                asset_manager=self.asset_manager,
            )

            # Create AI components
            provider = self._create_provider(colour)
            player_config = self.config.get_player_config(colour)
            if player_config:
                personality = Personality.from_config(player_config.personality)
            else:
                personality = Personality.default()

            brain = AIBrain(colour, provider, personality)
            memory = Memory(colour)
            vision = Vision(
                colour,
                normal_radius=self.config.ai.vision_radius,
                dark_radius=self.config.ai.vision_radius_dark,
            )
            movement_ctrl = MovementController()

            ai_player.set_ai_components(brain, memory, movement_ctrl)
            ai_player.vision = vision

            # Assign tasks
            ai_player.assigned_tasks = self.task_manager.assign_tasks(colour)

            self.ai_players.append(ai_player)

        # Assign impostors randomly
        impostor_indices = random.sample(range(len(self.ai_players)), num_impostors)
        for idx in impostor_indices:
            self.ai_players[idx].imposter = True
            self.ai_players[idx].brain.set_role("impostor")

        # For camera: follow first player
        if self.ai_players:
            self.player = self.ai_players[0]

        # Camera
        self.camera = Camera(self.pathfinder.map_width, self.pathfinder.map_height)

        # Start decision loop
        self.decision_loop = DecisionLoop(
            self.ai_players,
            game_state_provider=self._get_game_state_snapshot,
            decision_interval=self.config.ai.decision_interval,
            max_concurrent=self.config.ai.max_concurrent_calls,
        )
        self.decision_loop.start()

        self.start_time = time.time()
        self.playing = True

        self._log_event("Game started!")
        impostors = [p.bot_colour for p in self.ai_players if p.imposter]
        self._log_event(f"Impostors: {', '.join(impostors)}")

    def _create_provider(self, colour: str):
        """Create an LLM provider for a player based on config."""
        player_cfg = self.config.get_player_config(colour)
        provider_name = player_cfg.provider if player_cfg else self.config.ai.default_provider
        prov_cfg = self.config.get_provider_config(provider_name)

        if not prov_cfg or not prov_cfg.api_key:
            return None

        from among_ai.ai.providers.anthropic_provider import AnthropicProvider
        from among_ai.ai.providers.openai_provider import OpenAIProvider
        from among_ai.ai.providers.google_provider import GoogleProvider
        from among_ai.ai.providers.groq_provider import GroqProvider
        from among_ai.ai.providers.together_provider import TogetherProvider
        from among_ai.ai.providers.mistral_provider import MistralProvider
        from among_ai.ai.providers.deepseek_provider import DeepSeekProvider
        from among_ai.ai.providers.cohere_provider import CohereProvider

        providers = {
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "google": GoogleProvider,
            "groq": GroqProvider,
            "together": TogetherProvider,
            "mistral": MistralProvider,
            "deepseek": DeepSeekProvider,
            "cohere": CohereProvider,
        }

        cls = providers.get(provider_name)
        if cls:
            return cls(api_key=prov_cfg.api_key, model=prov_cfg.model)
        return None

    def run(self):
        """Main game loop."""
        self.load_data()
        self.setup_ai_game()
        self.sound_manager.play_effect('start_game')

        while self.playing:
            self.dt = self.clock.tick(FPS) / 1000.0
            self.events()
            if not self.paused:
                self.update()
            self.draw()

        # Cleanup
        if self.decision_loop:
            self.decision_loop.stop()

    def events(self):
        """Handle pygame events."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.playing = False
                pg.quit()
                sys.exit()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.playing = False
                elif event.key == pg.K_TAB:
                    # Cycle spectator camera target
                    alive = [p for p in self.ai_players if p.alive_status]
                    if alive:
                        self.spectator_target_idx = (
                            (self.spectator_target_idx + 1) % len(alive)
                        )
                        self.player = alive[self.spectator_target_idx]
                elif event.key == pg.K_SPACE:
                    self.paused = not self.paused

    def update(self):
        """Update game state each frame."""
        # Update timers
        self.timers.update()

        # Update all sprites (movement, collision)
        self.all_sprites.update()

        # Update camera
        if self.player and self.camera:
            self.camera.update(self.player)

        # Update ambient sounds based on spectated player
        if self.player:
            self.sound_manager.update_ambient(self.player.pos.x, self.player.pos.y)

        # Process AI actions from queues
        self._process_ai_actions()

        # Update AI movement controllers
        for ai in self.ai_players:
            if ai.alive_status and ai.movement_ctrl:
                ai.movement_ctrl.update_position((ai.pos.x, ai.pos.y))

        # Update tasks (check for completion of in-progress tasks)
        self._update_tasks()

        # Update meeting if active
        if self.meeting_manager.is_active:
            phase_change = self.meeting_manager.update()
            if phase_change:
                self._handle_meeting_phase_change(phase_change)
            self.emergency = self.meeting_manager.is_active
        else:
            self.emergency = False

        # Update game state snapshot for AI (every 500ms)
        now = time.time()
        if now - self._snapshot_time >= 0.5:
            self._update_game_state_snapshot()
            self._snapshot_time = now

        # Check win conditions
        self._check_win_conditions()

    def _process_ai_actions(self):
        """Process pending AI decisions from action queues."""
        for ai in self.ai_players:
            if not ai.alive_status or not ai.action_queue:
                continue

            # Get latest action (skip stale ones)
            action = None
            while ai.action_queue:
                action = ai.action_queue.popleft()

            if action is None:
                continue

            ai.current_action = action
            self._execute_ai_action(ai, action)

    def _execute_ai_action(self, ai: AIPlayer, decision):
        """Translate an AIDecision into game actions."""
        action = decision.action

        if action == AIAction.MOVE_TO_ROOM:
            room = decision.target_room
            if room and room in ROOMS:
                target = ROOMS[room]
                path = self.pathfinder.find_path(
                    (ai.pos.x, ai.pos.y), target
                )
                if path and ai.movement_ctrl:
                    ai.movement_ctrl.set_path(path)
                    ai.is_doing_task = False

        elif action == AIAction.DO_TASK:
            task_name = decision.target_task
            if task_name:
                self._start_ai_task(ai, task_name)

        elif action == AIAction.KILL:
            self._ai_kill(ai, decision.target_player)

        elif action == AIAction.REPORT_BODY:
            self._ai_report_body(ai)

        elif action == AIAction.CALL_MEETING:
            self._ai_call_meeting(ai)

        elif action == AIAction.VENT:
            self._ai_vent(ai)

        elif action == AIAction.SABOTAGE_LIGHTS:
            self._ai_sabotage_lights(ai)

        elif action == AIAction.SABOTAGE_REACTOR:
            self._ai_sabotage_reactor(ai)

        elif action == AIAction.FIX_LIGHTS:
            target = ROOMS["Electrical"]
            path = self.pathfinder.find_path((ai.pos.x, ai.pos.y), target)
            if path and ai.movement_ctrl:
                ai.movement_ctrl.set_path(path)

        elif action == AIAction.FIX_REACTOR:
            target = ROOMS["Reactor"]
            path = self.pathfinder.find_path((ai.pos.x, ai.pos.y), target)
            if path and ai.movement_ctrl:
                ai.movement_ctrl.set_path(path)

        elif action == AIAction.IDLE:
            if ai.movement_ctrl:
                ai.movement_ctrl.stop()
            ai.start_idle(
                self.config.ai.idle_after_task_min,
                self.config.ai.idle_after_task_max,
            )

        elif action == AIAction.FLEE:
            # Move to a random distant room
            rooms = list(ROOMS.keys())
            room = random.choice(rooms)
            path = self.pathfinder.find_path(
                (ai.pos.x, ai.pos.y), ROOMS[room]
            )
            if path and ai.movement_ctrl:
                ai.movement_ctrl.set_path(path)

    def _start_ai_task(self, ai: AIPlayer, task_name: str):
        """Start an AI player working on a task (takes real time)."""
        for task in ai.assigned_tasks:
            if task.name == task_name and not task.is_completed():
                # Check if near the task location
                dist = self.pathfinder.distance_between(
                    (ai.pos.x, ai.pos.y), task.location
                )
                if dist <= task.definition.get("radius", 50) + 100:
                    # Close enough - start the task
                    task.start_progress()
                    ai.is_doing_task = True
                    if ai.movement_ctrl:
                        ai.movement_ctrl.stop()
                    self._log_event(f"{ai.bot_colour} started task: {task_name}")
                else:
                    # Need to walk there first
                    path = self.pathfinder.find_path(
                        (ai.pos.x, ai.pos.y), task.location
                    )
                    if path and ai.movement_ctrl:
                        ai.movement_ctrl.set_path(path)
                break

    def _update_tasks(self):
        """Update in-progress tasks for all AI players."""
        for ai in self.ai_players:
            if not ai.alive_status:
                continue
            completed = self.task_manager.update_player_tasks(ai.bot_colour)
            for task_name in completed:
                ai.completed_task_names.append(task_name)
                ai.tasks_completed += 1
                ai.is_doing_task = False
                self.sound_manager.play_effect('task_completed')
                self._log_event(f"{ai.bot_colour} completed: {task_name}")
                # Natural pause after completing a task
                ai.start_idle(
                    self.config.ai.idle_after_task_min,
                    self.config.ai.idle_after_task_max,
                )

    def _ai_kill(self, ai: AIPlayer, target_colour: str):
        """Impostor AI kills a target."""
        if not ai.imposter or not self.timers.is_ready('kill_cooldown'):
            return

        target = None
        for other in self.ai_players:
            if other.bot_colour == target_colour and other.alive_status:
                dist = self.pathfinder.distance_between(
                    (ai.pos.x, ai.pos.y), (other.pos.x, other.pos.y)
                )
                if dist <= 150:
                    target = other
                    break

        if target:
            target.kill_target()
            self.timers.restart('kill_cooldown')
            self.sound_manager.play_effect('imposter_kill_sound')
            self._log_event(f"{ai.bot_colour} KILLED {target.bot_colour}!")

    def _ai_report_body(self, ai: AIPlayer):
        """AI reports a dead body."""
        for other in self.ai_players:
            if not other.alive_status and not other.got_reported:
                dist = self.pathfinder.distance_between(
                    (ai.pos.x, ai.pos.y), (other.pos.x, other.pos.y)
                )
                if dist <= 300:
                    other.got_reported = True
                    self.sound_manager.play_effect('dead_body_found')
                    self._log_event(f"{ai.bot_colour} reported {other.bot_colour}'s body!")
                    self.meeting_manager.start_meeting(
                        ai.bot_colour, body_colour=other.bot_colour
                    )
                    self.decision_loop.meeting_active = True
                    break

    def _ai_call_meeting(self, ai: AIPlayer):
        """AI calls an emergency meeting."""
        if not self.timers.is_ready('meeting_cooldown'):
            return
        dist = self.pathfinder.distance_between(
            (ai.pos.x, ai.pos.y), EMERGENCY_BUTTON_POS
        )
        if dist <= EMERGENCY_BUTTON_RADIUS:
            self.sound_manager.play_effect('emergency_alarm')
            self._log_event(f"{ai.bot_colour} called an EMERGENCY MEETING!")
            self.meeting_manager.start_meeting(ai.bot_colour)
            self.timers.restart('meeting_cooldown')
            self.decision_loop.meeting_active = True

    def _ai_vent(self, ai: AIPlayer):
        """AI uses a vent."""
        if not ai.imposter:
            return
        if ai.is_in_vent:
            ai.exit_vent()
            self.sound_manager.play_effect('vent')
        else:
            nearest = self.pathfinder.get_nearest_vent((ai.pos.x, ai.pos.y))
            if nearest:
                dist = self.pathfinder.distance_between(
                    (ai.pos.x, ai.pos.y), nearest
                )
                if dist <= 100:
                    ai.enter_vent()
                    self.sound_manager.play_effect('vent')
                    # Teleport to a random different vent
                    other_vents = [v for v in VENT_LOCATIONS if v != nearest]
                    if other_vents:
                        dest = random.choice(other_vents)
                        ai.teleport_to(dest[0], dest[1])
                        self._log_event(f"{ai.bot_colour} used a vent!")

    def _ai_sabotage_lights(self, ai: AIPlayer):
        """Impostor sabotages the lights."""
        if not ai.imposter or not self.timers.is_ready('sabotage_cooldown'):
            return
        self.night = True
        self.timers.restart('sabotage_cooldown')
        self.timers.start('lights_duration')
        self.sound_manager.play_effect('crises_alarm')
        self._log_event(f"LIGHTS SABOTAGED by {ai.bot_colour}!")

    def _ai_sabotage_reactor(self, ai: AIPlayer):
        """Impostor sabotages the reactor."""
        if not ai.imposter or not self.timers.is_ready('sabotage_cooldown'):
            return
        self.night_reactor = True
        self.timers.restart('sabotage_cooldown')
        self.timers.start('reactor_meltdown')
        self.sound_manager.play_effect('crises_alarm')
        self._log_event(f"REACTOR SABOTAGED by {ai.bot_colour}!")

    def _handle_meeting_phase_change(self, new_phase: MeetingPhase):
        """Handle transitions between meeting phases."""
        if new_phase == MeetingPhase.DISCUSSION:
            self.chat_log.start_new_meeting()
            # Trigger async discussion in decision loop
            import asyncio
            import threading
            def run_discussion():
                loop = asyncio.new_event_loop()
                state = self._get_game_state_snapshot()
                loop.run_until_complete(
                    self.decision_loop.run_meeting_discussion(state, self.meeting_manager)
                )
                loop.close()
            threading.Thread(target=run_discussion, daemon=True).start()

        elif new_phase == MeetingPhase.VOTING:
            # Trigger async voting
            import asyncio
            import threading
            alive_colours = [p.bot_colour for p in self.ai_players if p.alive_status]
            def run_votes():
                loop = asyncio.new_event_loop()
                state = self._get_game_state_snapshot()
                loop.run_until_complete(
                    self.decision_loop.run_meeting_votes(
                        state, self.meeting_manager, alive_colours
                    )
                )
                # Force end voting when all votes are in
                if self.meeting_manager.all_voted(alive_colours):
                    self.meeting_manager.force_end_voting()
                loop.close()
            threading.Thread(target=run_votes, daemon=True).start()

        elif new_phase == MeetingPhase.EJECTION:
            ejected = self.meeting_manager.ejected_colour
            if ejected:
                for ai in self.ai_players:
                    if ai.bot_colour == ejected:
                        ai.alive_status = False
                        ai.image = self.invisible_player_image or ai.image
                        role = "IMPOSTOR" if ai.imposter else "Crewmate"
                        self._log_event(f"{ejected} was ejected! They were {role}.")
                        break
            else:
                self._log_event("No one was ejected (tie/skip).")

        elif new_phase == MeetingPhase.RESUME or new_phase == MeetingPhase.NONE:
            self.decision_loop.meeting_active = False
            self.meeting_manager.reset()
            # Reset votes for all players
            for ai in self.ai_players:
                ai.voted = None
                ai.got_votes = 0

    def _check_win_conditions(self):
        """Check if crew or impostors have won."""
        alive_crew = [p for p in self.ai_players if p.alive_status and not p.imposter]
        alive_impostors = [p for p in self.ai_players if p.alive_status and p.imposter]

        # Crew wins: all tasks complete
        crew_colours = [p.bot_colour for p in self.ai_players if not p.imposter]
        total_done = self.task_manager.get_total_completed_all_crew(crew_colours)
        total_tasks = self.task_manager.get_total_tasks_all_crew(crew_colours)
        if total_tasks > 0 and total_done >= total_tasks:
            self._end_game("crew_wins", "Crew completed all tasks!")
            return

        # Crew wins: all impostors ejected
        if not alive_impostors:
            self._end_game("crew_wins", "All impostors were ejected!")
            return

        # Impostor wins: crew count <= impostor count
        if len(alive_crew) <= len(alive_impostors) and not self.emergency:
            self._end_game("impostor_wins", "Impostors outnumber crew!")
            return

        # Impostor wins: reactor meltdown
        if self.night_reactor and self.timers.get('reactor_meltdown').finished:
            self._end_game("impostor_wins", "Reactor meltdown!")
            return

        # Auto-fix lights when timer expires
        if self.night and self.timers.get('lights_duration').finished:
            self.night = False
            self._log_event("Lights restored automatically.")

        # Check if crew is near reactor/lights to fix
        self._check_sabotage_fixes()

    def _check_sabotage_fixes(self):
        """Check if any crewmate is at the sabotage fix location."""
        if self.night:
            for ai in self.ai_players:
                if ai.alive_status and not ai.imposter:
                    dist = self.pathfinder.distance_between(
                        (ai.pos.x, ai.pos.y), ROOMS["Electrical"]
                    )
                    if dist <= 100:
                        self.night = False
                        self.sound_manager.play_effect('task_completed')
                        self._log_event(f"{ai.bot_colour} fixed the lights!")
                        break

        if self.night_reactor:
            for ai in self.ai_players:
                if ai.alive_status and not ai.imposter:
                    dist = self.pathfinder.distance_between(
                        (ai.pos.x, ai.pos.y), ROOMS["Reactor"]
                    )
                    if dist <= 100:
                        self.night_reactor = False
                        self.timers.get('reactor_meltdown').stop()
                        self.sound_manager.play_effect('task_completed')
                        self._log_event(f"{ai.bot_colour} fixed the reactor!")
                        break

    def _end_game(self, result: str, message: str):
        """End the game with a result."""
        self.game_over_flag = True
        self.game_result = result
        self._log_event(f"GAME OVER: {message}")

        if result == "crew_wins":
            self.sound_manager.play_effect('victory_crew')
        else:
            self.sound_manager.play_effect('victory_imposter')

        # Show game over screen for 5 seconds then stop
        self._draw_game_over(message)
        pg.display.flip()
        pg.time.wait(5000)
        self.playing = False

    def draw(self):
        """Render everything to screen."""
        # Draw map
        self.screen.fill(BGCOLOR)
        if self.camera:
            self.screen.blit(self.map_img, self.camera.apply_rect(self.map_rect))

        # Draw all sprites
        for sprite in self.all_sprites:
            if self.camera:
                self.screen.blit(sprite.image, self.camera.apply(sprite))

        # Fog of war when lights sabotaged
        if self.night and self.light_mask and self.player:
            self._draw_fog()

        # Draw meeting UI
        if self.meeting_manager.is_active:
            self.chat_renderer.render(
                self.screen,
                self.meeting_manager.chat_messages,
                self.meeting_manager.phase.value,
                self.meeting_manager.get_time_remaining(),
                self.meeting_manager.get_vote_summary()
                if self.meeting_manager.phase in (MeetingPhase.VOTING, MeetingPhase.RESULTS)
                else None,
            )

        # HUD
        self._draw_hud()

        # Event log
        self._draw_event_log()

        pg.display.flip()

    def _draw_fog(self):
        """Draw fog of war overlay when lights are sabotaged."""
        fog = pg.Surface((WIDTH, HEIGHT))
        fog.fill(NIGHT_COLOR)
        if self.player and self.camera:
            light_offset = self.camera.apply(self.player)
            lx = light_offset.x - LIGHT_RADIUS[0] // 2 + 32
            ly = light_offset.y - LIGHT_RADIUS[1] // 2 + 43
            fog.blit(self.light_mask, (lx, ly))
        self.screen.blit(fog, (0, 0), special_flags=pg.BLEND_MULT)

    def _draw_hud(self):
        """Draw heads-up display: player info, task progress, etc."""
        try:
            font = pg.font.Font(FONT, 14)
            small = pg.font.Font(FONT, 11)
        except Exception:
            font = pg.font.SysFont("arial", 14)
            small = pg.font.SysFont("arial", 11)

        # Watching indicator
        if self.player:
            colour = self.player.bot_colour if hasattr(self.player, 'bot_colour') else "?"
            role = "IMPOSTOR" if hasattr(self.player, 'imposter') and self.player.imposter else "Crew"
            provider_name = ""
            if hasattr(self.player, 'brain') and self.player.brain and self.player.brain.provider:
                provider_name = f" [{self.player.brain.provider.get_provider_name()}]"
            text = font.render(
                f"Watching: {colour} ({role}){provider_name} | TAB to switch | SPACE to pause",
                True, WHITE
            )
            self.screen.blit(text, (10, HEIGHT - 30))

        # Task progress bar
        crew = [p.bot_colour for p in self.ai_players if not p.imposter]
        done = self.task_manager.get_total_completed_all_crew(crew)
        total = self.task_manager.get_total_tasks_all_crew(crew)
        if total > 0:
            pct = done / total
            bar_w = 200
            bar_h = 16
            bx, by = WIDTH - bar_w - 10, 10
            pg.draw.rect(self.screen, (50, 50, 50), (bx, by, bar_w, bar_h))
            pg.draw.rect(self.screen, (0, 200, 0), (bx, by, int(bar_w * pct), bar_h))
            pg.draw.rect(self.screen, WHITE, (bx, by, bar_w, bar_h), 1)
            text = small.render(f"Tasks: {done}/{total}", True, WHITE)
            self.screen.blit(text, (bx + 5, by + 1))

        # Alive count
        alive = sum(1 for p in self.ai_players if p.alive_status)
        total_p = len(self.ai_players)
        alive_text = small.render(f"Alive: {alive}/{total_p}", True, WHITE)
        self.screen.blit(alive_text, (WIDTH - 210, 32))

        # Sabotage indicators
        if self.night:
            sab = font.render("LIGHTS OFF!", True, (255, 50, 50))
            self.screen.blit(sab, (WIDTH // 2 - 50, 10))
        if self.night_reactor:
            remaining = self.timers.get('reactor_meltdown').get_remaining_int()
            sab = font.render(f"REACTOR MELTDOWN: {remaining}s", True, (255, 50, 50))
            self.screen.blit(sab, (WIDTH // 2 - 80, 10))

        # Player list
        y = 55
        for ai in self.ai_players:
            colour = PLAYER_DISPLAY_COLORS.get(ai.bot_colour, WHITE)
            status = "ALIVE" if ai.alive_status else "DEAD"
            room = self.pathfinder.get_room_at((ai.pos.x, ai.pos.y))
            provider = ""
            if ai.brain and ai.brain.provider:
                provider = f" [{ai.brain.provider.get_provider_name()}]"
            alpha = 255 if ai.alive_status else 100
            text = small.render(f"{ai.bot_colour}: {room}{provider}", True, colour)
            if not ai.alive_status:
                text.set_alpha(100)
            self.screen.blit(text, (WIDTH - 210, y))
            y += 16

    def _draw_event_log(self):
        """Draw recent events in bottom-left corner."""
        try:
            font = pg.font.Font(FONT, 11)
        except Exception:
            font = pg.font.SysFont("arial", 11)

        y = HEIGHT - 50
        for msg in self.event_log[-3:]:
            text = font.render(msg, True, (200, 200, 200))
            self.screen.blit(text, (10, y))
            y -= 16

    def _draw_game_over(self, message: str):
        """Draw game over screen."""
        self.screen.blit(self.dim_screen, (0, 0))
        try:
            font = pg.font.Font(FONT, 32)
            small = pg.font.Font(FONT, 18)
        except Exception:
            font = pg.font.SysFont("arial", 32)
            small = pg.font.SysFont("arial", 18)

        title_colour = (0, 200, 0) if self.game_result == "crew_wins" else (200, 0, 0)
        title = "CREW WINS!" if self.game_result == "crew_wins" else "IMPOSTOR WINS!"
        title_surf = font.render(title, True, title_colour)
        msg_surf = small.render(message, True, WHITE)
        self.screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, HEIGHT//2 - 40))
        self.screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, HEIGHT//2 + 20))

        # Show impostors
        impostors = [p.bot_colour for p in self.ai_players if p.imposter]
        imp_text = small.render(f"Impostors were: {', '.join(impostors)}", True, (255, 100, 100))
        self.screen.blit(imp_text, (WIDTH//2 - imp_text.get_width()//2, HEIGHT//2 + 60))

    def _log_event(self, message: str):
        """Add an event to the log."""
        timestamp = time.time() - self.start_time
        self.event_log.append(f"[{int(timestamp)}s] {message}")
        print(f"[GAME] {message}")
        # Keep log bounded
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]

    def _get_game_state_snapshot(self) -> GameStateSnapshot:
        """Create a frozen snapshot of the game state for AI consumption."""
        if self._game_state_snapshot:
            return self._game_state_snapshot
        return self._build_snapshot()

    def _update_game_state_snapshot(self):
        """Update the shared game state snapshot."""
        self._game_state_snapshot = self._build_snapshot()

    def _build_snapshot(self) -> GameStateSnapshot:
        all_players = []
        for ai in self.ai_players:
            all_players.append(PlayerSnapshot(
                colour=ai.bot_colour,
                position=(ai.pos.x, ai.pos.y),
                room=self.pathfinder.get_room_at((ai.pos.x, ai.pos.y)),
                alive=ai.alive_status,
                is_impostor=ai.imposter,
                tasks_completed=ai.tasks_completed,
            ))

        sabotage = None
        if self.night:
            sabotage = "lights"
        elif self.night_reactor:
            sabotage = "reactor"

        reactor_countdown = None
        if self.night_reactor:
            reactor_countdown = self.timers.get('reactor_meltdown').get_remaining_int()

        phase = "gameplay"
        if self.meeting_manager.is_active:
            phase = self.meeting_manager.phase.value

        return GameStateSnapshot(
            game_time=time.time() - self.start_time,
            phase=phase,
            sabotage_active=sabotage,
            reactor_countdown=reactor_countdown,
            all_players=all_players,
            kill_cooldown_remaining=self.timers.remaining('kill_cooldown'),
            sabotage_cooldown_remaining=self.timers.remaining('sabotage_cooldown'),
            meeting_cooldown_remaining=self.timers.remaining('meeting_cooldown'),
            can_call_meeting=self.timers.is_ready('meeting_cooldown'),
            chat_history=self.meeting_manager.chat_messages
            if self.meeting_manager.is_active else None,
        )
