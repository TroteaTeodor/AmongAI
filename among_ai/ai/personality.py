"""AI personality system: defines behavioral traits embedded in LLM system prompts."""

from dataclasses import dataclass
from among_ai.config import PersonalityConfig


@dataclass
class Personality:
    """AI player personality traits."""
    name: str
    aggression: float       # 0-1: how aggressive (kill eagerness, accusation strength)
    suspicion_tendency: float  # 0-1: how suspicious of others
    chattiness: float       # 0-1: how much they talk in meetings
    cooperation: float      # 0-1: how much they work with others
    deception_skill: float  # 0-1: how good at lying (impostor)
    risk_tolerance: float   # 0-1: willingness to take risky actions
    speaking_style: str     # Description of how they talk

    @classmethod
    def from_config(cls, config: PersonalityConfig) -> 'Personality':
        return cls(
            name=config.name,
            aggression=config.aggression,
            suspicion_tendency=config.suspicion_tendency,
            chattiness=config.chattiness,
            cooperation=config.cooperation,
            deception_skill=config.deception_skill,
            risk_tolerance=config.risk_tolerance,
            speaking_style=config.speaking_style,
        )

    @classmethod
    def default(cls) -> 'Personality':
        return cls(
            name="Default",
            aggression=0.5,
            suspicion_tendency=0.5,
            chattiness=0.5,
            cooperation=0.5,
            deception_skill=0.5,
            risk_tolerance=0.5,
            speaking_style="Balanced and neutral.",
        )

    def to_system_prompt_section(self) -> str:
        """Generate the personality section for the LLM system prompt."""
        lines = [
            f"Your name/codename is '{self.name}'.",
            f"Speaking style: {self.speaking_style}",
            "",
            "Your behavioral tendencies (0=low, 1=high):",
        ]
        if self.aggression > 0.6:
            lines.append("- You are aggressive and confrontational")
        elif self.aggression < 0.4:
            lines.append("- You are passive and non-confrontational")
        if self.suspicion_tendency > 0.6:
            lines.append("- You are very suspicious and question everything")
        elif self.suspicion_tendency < 0.4:
            lines.append("- You tend to trust others easily")
        if self.chattiness > 0.6:
            lines.append("- You talk a lot and share observations freely")
        elif self.chattiness < 0.4:
            lines.append("- You are quiet and only speak when necessary")
        if self.cooperation > 0.6:
            lines.append("- You prefer working in groups and buddy systems")
        elif self.cooperation < 0.4:
            lines.append("- You prefer working alone")
        if self.risk_tolerance > 0.6:
            lines.append("- You take bold risks and make aggressive plays")
        elif self.risk_tolerance < 0.4:
            lines.append("- You play it safe and avoid risky situations")

        return "\n".join(lines)
