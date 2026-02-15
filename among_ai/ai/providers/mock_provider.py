
"""Mock provider for testing."""
from typing import Optional
import random
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider

class MockProvider(BaseProvider):
    def __init__(self, api_key: str = "mock", model: str = "mock-model"):
        super().__init__(api_key, model, "Mock")

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        
        # Simple rule-based responses for testing game flow
        text = "I will go to the reactor."
        if "vote" in user_prompt.lower():
            text = "I vote for Red because they are sus."
        
        return LLMResponse(
            text=text,
            model=self._model,
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=10,
        )
