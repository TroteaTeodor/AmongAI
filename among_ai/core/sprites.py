"""Game sprites: Player, AIPlayer, Wall, Obstacle, Item.
AIPlayer extends the original Bot with brain/memory/pathfinding integration."""

import time
import random
import collections
import pygame as pg
from among_ai.constants import (
    PLAYER_LAYER, BOT_LAYER, WALL_LAYER, ITEM_LAYER,
    PLAYER_SPEED, PLAYER_SPRITE_SIZE, STEPPING_RATE,
)

vec = pg.math.Vector2


class Player(pg.sprite.Sprite):
    """Human-controlled player sprite."""

    def __init__(self, game, pos, player_id, player_colour, asset_manager):
        self._layer = PLAYER_LAYER
        self.groups = game.all_sprites
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.player_id = player_id
        self.player_colour = player_colour
        self.alive_status = True
        self.imposter = False

        # Load sprites from asset manager (dict-based, no if/elif)
        self.assets = asset_manager
        walk_data = asset_manager.get_all_walk_data(player_colour)
        self.player_imgs_left = walk_data["left"]
        self.player_imgs_right = walk_data["right"]
        self.player_imgs_down = walk_data["down"]
        self.player_imgs_up = walk_data["up"]
        self.image = self.player_imgs_down[0]
        self.image_dead = asset_manager.get_dead_image(player_colour)
        ghosts = asset_manager.get_ghost_images(player_colour)
        self.image_ghost_left = ghosts["left"]
        self.image_ghost_right = ghosts["right"]
        self.emergency_meeting_img = asset_manager.get_meeting_image(player_colour)
        self.eject_img = asset_manager.get_eject_image(player_colour)

        # Frame indices
        self.left_img_index = 0
        self.right_img_index = 0
        self.up_img_index = 0
        self.down_img_index = 0

        self.rect = self.image.get_rect()
        self.hit_rect = self.rect
        self.vel = vec(0, 0)
        self.pos = vec(pos)
        self.pos_corpse = vec(0, 0)

        self.last_played = 0
        self.now = 0
        self.tasks_completed = 0
        self.victim_id = 0
        self.victim_id_report = 0
        self.voted = None
        self.got_votes = 0
        self.got_reported = False

    def get_keys(self):
        if not self.alive_status or self.game.emergency:
            if not self.alive_status and not self.game.emergency:
                # Ghost movement
                self.vel = vec(0, 0)
                keys = pg.key.get_pressed()
                if keys[pg.K_LEFT] or keys[pg.K_a]:
                    self.vel.x = -PLAYER_SPEED
                    self.image = self.image_ghost_left
                if keys[pg.K_RIGHT] or keys[pg.K_d]:
                    self.vel.x = PLAYER_SPEED
                    self.image = self.image_ghost_right
                if keys[pg.K_UP] or keys[pg.K_w]:
                    self.vel.y = -PLAYER_SPEED
                if keys[pg.K_DOWN] or keys[pg.K_s]:
                    self.vel.y = PLAYER_SPEED
                if self.vel.x != 0 and self.vel.y != 0:
                    self.vel *= 0.7071
            return

        if self.game.invisible_play_count != 0 or self.game.isdoingTask:
            return

        self.vel = vec(0, 0)
        keys = pg.key.get_pressed()

        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.image = self.player_imgs_left[self.left_img_index]
            self.left_img_index = (self.left_img_index + 1) % len(self.player_imgs_left)
            self.vel.x = -PLAYER_SPEED
            self._play_footstep()
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.image = self.player_imgs_right[self.right_img_index]
            self.right_img_index = (self.right_img_index + 1) % len(self.player_imgs_right)
            self.vel.x = PLAYER_SPEED
            self._play_footstep()
        if keys[pg.K_UP] or keys[pg.K_w]:
            self.image = self.player_imgs_up[self.up_img_index]
            self.up_img_index = (self.up_img_index + 1) % len(self.player_imgs_up)
            self.vel.y = -PLAYER_SPEED
            self._play_footstep()
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            self.image = self.player_imgs_down[self.down_img_index]
            self.down_img_index = (self.down_img_index + 1) % len(self.player_imgs_down)
            self.vel.y = PLAYER_SPEED
            self._play_footstep()

        if self.vel.x != 0 and self.vel.y != 0:
            self.vel *= 0.7071

    def _play_footstep(self):
        self.now = pg.time.get_ticks()
        if self.now - self.last_played > STEPPING_RATE:
            self.last_played = self.now
            if hasattr(self.game, 'foot_sounds') and self.game.foot_sounds:
                random.choice(self.game.foot_sounds['footsteps']).play()

    def collide_with_walls(self, direction):
        if not self.alive_status:
            return
        if direction == 'x':
            hits = pg.sprite.spritecollide(self, self.game.walls, False)
            if hits:
                if self.vel.x > 0:
                    self.pos.x = hits[0].rect.left - self.rect.width
                if self.vel.x < 0:
                    self.pos.x = hits[0].rect.right
                self.vel.x = 0
                self.rect.x = self.pos.x
        if direction == 'y':
            hits = pg.sprite.spritecollide(self, self.game.walls, False)
            if hits:
                if self.vel.y > 0:
                    self.pos.y = hits[0].rect.top - self.rect.height
                if self.vel.y < 0:
                    self.pos.y = hits[0].rect.bottom
                self.vel.y = 0
                self.rect.y = self.pos.y

    def update(self):
        self.get_keys()
        self.pos += self.vel * self.game.dt
        self.rect.x = self.pos.x
        self.collide_with_walls('x')
        self.rect.y = self.pos.y
        self.collide_with_walls('y')


class AIPlayer(pg.sprite.Sprite):
    """AI-controlled player with LLM brain, memory, and pathfinding.
    Replaces the original static Bot class. Actually moves, does tasks, votes, chats."""

    def __init__(self, game, x, y, bot_id, colour, asset_manager):
        self._layer = BOT_LAYER
        self.groups = game.all_sprites, game.bots
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.bot_id = bot_id
        self.bot_colour = colour
        self.alive_status = True
        self.imposter = False
        self.type = f'ai_{bot_id}'

        # Assets via dict lookup
        self.assets = asset_manager
        walk_data = asset_manager.get_all_walk_data(colour)
        self.walk_frames = walk_data  # {direction: [frames]}
        self.image = walk_data["down"][0]
        self.dead_player_img = asset_manager.get_dead_image(colour)
        ghosts = asset_manager.get_ghost_images(colour)
        self.image_ghost_left = ghosts["left"]
        self.image_ghost_right = ghosts["right"]
        self.eject_img = asset_manager.get_eject_image(colour)

        # Animation state
        self._frame_indices = {"left": 0, "right": 0, "up": 0, "down": 0}
        self._current_direction = "down"
        self._anim_timer = 0
        self._anim_interval = 0.08  # seconds between frames

        self.rect = self.image.get_rect()
        self.hit_rect = self.rect
        self.vel = vec(0, 0)
        self.pos = vec(x, y)
        self.pos_corpse = vec(0, 0)
        self.play_kill_count = 0

        # AI state
        self.tasks_completed = 0
        self.voted = None
        self.got_votes = 0
        self.got_reported = False
        self.is_doing_task = False
        self.is_in_vent = False

        # AI components (set by game engine after construction)
        self.brain = None           # IAIBrain
        self.memory = None          # IMemory
        self.movement_ctrl = None   # MovementController

        # Thread-safe action queue (LLM decisions arrive here from background thread)
        self.action_queue = collections.deque(maxlen=5)
        self.current_action = None
        self.last_decision_time = 0.0

        # Task system
        self.assigned_tasks = []    # list[TaskInstance]
        self.completed_task_names = []

        # Idle/pause state (for realistic behavior after completing tasks)
        self._idle_until = 0.0
        self._task_just_completed = False

        # Individual kill cooldown
        self.kill_timer = 20.0
        
        # Debug: reasoning text from last decision
        self.last_reasoning = ""

    def set_ai_components(self, brain, memory, movement_ctrl):
        """Inject AI components after construction."""
        self.brain = brain
        self.memory = memory
        self.movement_ctrl = movement_ctrl

    def collide_with_walls(self, direction):
        if direction == 'x':
            hits = pg.sprite.spritecollide(self, self.game.walls, False)
            if hits:
                if self.vel.x > 0:
                    self.pos.x = hits[0].rect.left - self.rect.width
                if self.vel.x < 0:
                    self.pos.x = hits[0].rect.right
                self.vel.x = 0
                self.rect.x = self.pos.x
        if direction == 'y':
            hits = pg.sprite.spritecollide(self, self.game.walls, False)
            if hits:
                if self.vel.y > 0:
                    self.pos.y = hits[0].rect.top - self.rect.height
                if self.vel.y < 0:
                    self.pos.y = hits[0].rect.bottom
                self.vel.y = 0
                self.rect.y = self.pos.y

    def update(self):
        if not self.alive_status:
            return

        # Don't move during meetings
        if self.game.emergency:
            self.vel = vec(0, 0)
            return

        # Check if idling (pausing after task, natural behavior)
        now = time.time()
        if now < self._idle_until:
            self.vel = vec(0, 0)
            self._apply_movement()
            return

        # Update movement from movement controller
        if self.movement_ctrl and not self.is_doing_task:
            vel, direction = self.movement_ctrl.get_velocity_and_direction((self.pos.x, self.pos.y))
            self.vel = vec(vel[0], vel[1])
            if direction:
                self._update_animation(direction)
        elif self.is_doing_task:
            self.vel = vec(0, 0)
            
        # Update path tracker
        if self.movement_ctrl:
            self.movement_ctrl.update_position((self.pos.x, self.pos.y))

        self._apply_movement()

        # Update kill timer
        if hasattr(self, 'kill_timer') and self.kill_timer > 0:
            self.kill_timer -= self.game.dt
            
        # Check for urgent vision events (bodies) every few frames
        # Only check every 10 frames to save performance
        if self.game.frame_count % 10 == 0:
            self._check_vision_events()

    def _check_vision_events(self):
        """Passive vision check for high-priority events (bodies)."""
        # Simple distance check for bodies
        if not self.alive_status: 
            return
            
        # Don't interrupt if already reporting/meeting
        if self.game.meeting_manager.is_active:
            return

        vision_radius = self.game.config.ai.vision_radius
        
        # Check bodies
        for body in self.game.dead_bodies:
            # Skip if already reported
            if body.reported:
                continue

            # Calculate distance
            dx = body.pos.x - self.pos.x
            dy = body.pos.y - self.pos.y
            dist = (dx*dx + dy*dy)**0.5
            
            # If body is close
            if dist < vision_radius:
                # Force an interrupt!
                # If we are NOT already going to report it
                if self.current_action and self.current_action.action == "REPORT_BODY":
                    continue
                    
                # Store that we saw a body to memory immediately
                if self.memory:
                    self.memory.add_event(f"Saw dead body of {body.player_colour}!")
                
                # Stop current movement/task
                self.action_queue.clear()
                self.current_action = None
                if self.movement_ctrl:
                    self.movement_ctrl.stop()
                self.is_doing_task = False
                
                # Force immediate re-decision
                self.last_decision_time = 0
                print(f"[{self.bot_colour}] SAW BODY! Interrupting task.")
                break

    def _apply_movement(self):
        """Apply velocity, check collisions."""
        self.pos += self.vel * self.game.dt
        self.rect.x = self.pos.x
        self.collide_with_walls('x')
        self.rect.y = self.pos.y
        self.collide_with_walls('y')

    def _update_animation(self, direction: str):
        """Update sprite animation based on movement direction."""
        self._current_direction = direction
        frames = self.walk_frames[direction]
        idx = self._frame_indices[direction]
        self.image = frames[idx]
        now = time.time()
        if now - self._anim_timer >= self._anim_interval:
            self._anim_timer = now
            self._frame_indices[direction] = (idx + 1) % len(frames)

    def start_idle(self, min_time: float, max_time: float):
        """Pause movement for a random duration (natural behavior)."""
        self._idle_until = time.time() + random.uniform(min_time, max_time)

    def kill_target(self):
        """Visual: show dead body at current position."""
        self.alive_status = False
        self.pos_corpse = vec(self.pos.x, self.pos.y)
        self.image = self.dead_player_img

    def enter_vent(self):
        """Make invisible (in vent)."""
        self.is_in_vent = True
        invis = self.game.invisible_player_image
        if invis:
            self.image = invis

    def exit_vent(self):
        """Become visible again."""
        self.is_in_vent = False
        self.image = self.walk_frames["down"][0]

    def teleport_to(self, x, y):
        """Teleport to a position (for vent travel)."""
        self.pos = vec(x, y)
        self.rect.x = self.pos.x
        self.rect.y = self.pos.y


class Wall(pg.sprite.Sprite):
    def __init__(self, game, x, y):
        self._layer = WALL_LAYER
        self.groups = game.walls
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.image = pg.Surface((1, 1))
        self.rect = self.image.get_rect()
        self.x = x
        self.y = y
        self.rect.x = x
        self.rect.y = y


class Obstacle(pg.sprite.Sprite):
    """Invisible collision rectangle."""
    def __init__(self, game, x, y, width, height):
        self.groups = game.walls
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.rect = pg.Rect(x, y, width, height)
        self.x = x
        self.y = y


class Item(pg.sprite.Sprite):
    def __init__(self, game, pos, item_type):
        self._layer = ITEM_LAYER
        self.groups = game.all_sprites, game.items
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.image = game.item_images[item_type]
        self.rect = self.image.get_rect()
        self.hit_rect = self.rect
        self.type = item_type
        self.rect.center = pos
