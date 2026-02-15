"""Mistral AI provider."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class MistralProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "mistral-small-latest"):
        super().__init__(api_key, model, "Mistral")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from mistralai import Mistral
            self._client = Mistral(api_key=self._api_key)
        return self._client

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        client = self._get_client()
        import asyncio

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.complete(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
        text = response.choices[0].message.content if response.choices else ""
        usage = response.usage
        return LLMResponse(
            text=text or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=0,
        )
