"""Base provider with shared retry/timeout logic."""

import time
import asyncio
from typing import Optional
from among_ai.ai.interfaces import ILLMProvider, LLMResponse


class BaseProvider(ILLMProvider):
    """Base class for all LLM providers with retry and rate limiting."""

    def __init__(self, api_key: str, model: str, provider_name: str):
        self._api_key = api_key
        self._model = model
        self._provider_name = provider_name
        self._max_retries = 2
        self._retry_delay = 1.0

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return self._provider_name

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def generate(self, system_prompt: str, user_prompt: str,
                       temperature: float = 0.7, max_tokens: int = 300,
                       stop_sequences: Optional[list] = None) -> LLMResponse:
        """Generate with retry logic."""
        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                start = time.time()
                response = await self._call_api(
                    system_prompt, user_prompt, temperature, max_tokens, stop_sequences
                )
                latency = (time.time() - start) * 1000
                response.latency_ms = latency
                return response
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise last_error

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        """Override in subclasses to implement actual API call."""
        raise NotImplementedError
