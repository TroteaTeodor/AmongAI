"""OpenRouter LLM provider (using OpenAI-compatible API)."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class OpenRouterProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        # Default to a good model if none specified
        super().__init__(api_key, model, "OpenRouter")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url="https://openrouter.ai/api/v1",
            )
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
            # OpenRouter specific headers if needed, but standard OpenAI client handles basic auth
            # "extra_headers": {
            #     "HTTP-Referer": "https://github.com/AI0702/Among-Us-clone", 
            #     "X-Title": "AmongAI"
            # }
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
