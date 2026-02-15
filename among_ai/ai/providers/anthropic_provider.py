"""Claude (Anthropic) LLM provider."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class AnthropicProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        super().__init__(api_key, model, "Anthropic")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        client = self._get_client()
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        response = await client.messages.create(**kwargs)
        text = response.content[0].text if response.content else ""
        return LLMResponse(
            text=text,
            model=self._model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            latency_ms=0,
        )
