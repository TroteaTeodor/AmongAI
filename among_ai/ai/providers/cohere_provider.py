"""Cohere LLM provider."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class CohereProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "command-r"):
        super().__init__(api_key, model, "Cohere")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import cohere
            self._client = cohere.AsyncClientV2(api_key=self._api_key)
        return self._client

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        client = self._get_client()
        response = await client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.message.content[0].text if response.message.content else ""
        usage = response.usage
        return LLMResponse(
            text=text or "",
            model=self._model,
            prompt_tokens=usage.tokens.input_tokens if usage and usage.tokens else 0,
            completion_tokens=usage.tokens.output_tokens if usage and usage.tokens else 0,
            latency_ms=0,
        )
