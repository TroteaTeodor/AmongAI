"""Orchestrates AI discussion rounds during emergency meetings."""

import asyncio
import random
from typing import Optional
from among_ai.ai.interfaces import GameStateSnapshot


class ChatManager:
    """Manages the chat/discussion phase of emergency meetings."""

    def __init__(self, discussion_rounds: int = 3):
        self.discussion_rounds = discussion_rounds
        self.messages: list[dict] = []

    def clear(self):
        self.messages.clear()

    def add_message(self, speaker: str, text: str):
        self.messages.append({"speaker": speaker, "text": text})

    def get_messages(self) -> list[dict]:
        return list(self.messages)
