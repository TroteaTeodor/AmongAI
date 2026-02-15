"""Gemini (Google) LLM provider."""

from typing import Optional
from among_ai.ai.interfaces import LLMResponse
from among_ai.ai.providers.base_provider import BaseProvider


class GoogleProvider(BaseProvider):

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        super().__init__(api_key, model, "Google")
        self._configured = False

    def _configure(self):
        if not self._configured:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._configured = True

    async def _call_api(self, system_prompt: str, user_prompt: str,
                        temperature: float, max_tokens: int,
                        stop_sequences: Optional[list]) -> LLMResponse:
        self._configure()
        import google.generativeai as genai
        import asyncio

        model = genai.GenerativeModel(
            self._model,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        # google-generativeai is sync, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: model.generate_content(user_prompt)
        )
        text = response.text if response.text else ""
        return LLMResponse(
            text=text,
            model=self._model,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
        )
