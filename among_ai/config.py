"""Configuration loader: reads config.yaml, resolves env vars, provides factories."""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PersonalityConfig:
    name: str = "Default"
    aggression: float = 0.5
    suspicion_tendency: float = 0.5
    chattiness: float = 0.5
    cooperation: float = 0.5
    deception_skill: float = 0.5
    risk_tolerance: float = 0.5
    speaking_style: str = "Neutral and balanced."


@dataclass
class PlayerConfig:
    colour: str
    provider: str = "anthropic"
    model: str = ""  # Per-player model override
    personality: PersonalityConfig = field(default_factory=PersonalityConfig)


@dataclass
class GameConfig:
    mode: str = "watch_ai"
    num_players: int = 10
    num_impostors: int = 2
    discussion_time: int = 30
    voting_time: int = 30
    kill_cooldown: int = 15
    sabotage_cooldown: int = 15
    task_count: int = 8
    game_speed: float = 1.0


@dataclass
class AIConfig:
    decision_interval: float = 3.0
    vision_radius: int = 500
    vision_radius_dark: int = 150
    fallback_enabled: bool = True
    llm_timeout: float = 6.0
    max_concurrent_calls: int = 3
    task_duration_min: float = 3.0
    task_duration_max: float = 8.0
    idle_after_task_min: float = 1.0
    idle_after_task_max: float = 3.0
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-5-20250929"


@dataclass
class ProviderConfig:
    api_key: str = ""
    model: str = ""


class Config:
    """Central configuration manager."""

    def __init__(self, config_path: str = "config.yaml"):
        self.game = GameConfig()
        self.ai = AIConfig()
        self.providers: dict[str, ProviderConfig] = {}
        self.players: list[PlayerConfig] = []
        self._load(config_path)

    def _resolve_env(self, value: str) -> str:
        """Resolve ${ENV_VAR} references in config values."""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, "")
        return value

    def _load(self, config_path: str):
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            print(f"[Config] No {config_path} found, using defaults.")
            return

        with open(config_path, 'r') as f:
            raw = yaml.safe_load(f) or {}

        # Game settings
        if 'game' in raw:
            g = raw['game']
            self.game = GameConfig(
                mode=g.get('mode', 'watch_ai'),
                num_players=g.get('num_players', 10),
                num_impostors=g.get('num_impostors', 2),
                discussion_time=g.get('discussion_time', 30),
                voting_time=g.get('voting_time', 30),
                kill_cooldown=g.get('kill_cooldown', 15),
                sabotage_cooldown=g.get('sabotage_cooldown', 15),
                task_count=g.get('task_count', 8),
                game_speed=g.get('game_speed', 1.0),
            )

        # AI settings
        if 'ai' in raw:
            a = raw['ai']
            self.ai = AIConfig(
                decision_interval=a.get('decision_interval', 3.0),
                vision_radius=a.get('vision_radius', 500),
                vision_radius_dark=a.get('vision_radius_dark', 150),
                fallback_enabled=a.get('fallback_enabled', True),
                llm_timeout=a.get('llm_timeout', 6.0),
                max_concurrent_calls=a.get('max_concurrent_calls', 3),
                task_duration_min=a.get('task_duration_min', 3.0),
                task_duration_max=a.get('task_duration_max', 8.0),
                idle_after_task_min=a.get('idle_after_task_min', 1.0),
                idle_after_task_max=a.get('idle_after_task_max', 3.0),
                default_provider=a.get('default_provider', 'anthropic'),
                default_model=a.get('default_model', 'claude-sonnet-4-5-20250929'),
            )

        # Providers
        if 'providers' in raw:
            for name, prov in raw['providers'].items():
                self.providers[name] = ProviderConfig(
                    api_key=self._resolve_env(prov.get('api_key', '')),
                    model=prov.get('model', ''),
                )

        # Players
        if 'players' in raw:
            for p in raw['players']:
                pers = p.get('personality', {})
                pc = PlayerConfig(
                    colour=p['colour'],
                    provider=p.get('provider', self.ai.default_provider),
                    model=p.get('model', ''),  # Per-player model
                    personality=PersonalityConfig(
                        name=pers.get('name', 'Default'),
                        aggression=pers.get('aggression', 0.5),
                        suspicion_tendency=pers.get('suspicion_tendency', 0.5),
                        chattiness=pers.get('chattiness', 0.5),
                        cooperation=pers.get('cooperation', 0.5),
                        deception_skill=pers.get('deception_skill', 0.5),
                        risk_tolerance=pers.get('risk_tolerance', 0.5),
                        speaking_style=pers.get('speaking_style', 'Neutral.'),
                    ),
                )
                self.players.append(pc)

    def get_player_config(self, colour: str) -> Optional[PlayerConfig]:
        """Get config for a specific player colour."""
        for p in self.players:
            if p.colour == colour:
                return p
        return None

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get provider config by name."""
        return self.providers.get(provider_name)
