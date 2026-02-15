"""GPT (OpenAI) LLM provider."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class OpenAIProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__(api_key, model, "OpenAI")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        client = self._get_client()
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if stop_sequences:
            kwargs["stop"] = stop_sequences

        response = await client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content if response.choices else ""
        usage = response.usage
        return LLMResponse(
            text=text or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=0,
        )
