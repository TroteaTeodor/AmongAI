"""Chat message storage and querying."""

import time


class ChatLog:
    """Stores all chat messages from all meetings."""

    def __init__(self):
        self.messages: list[dict] = []
        self.meeting_count = 0

    def start_new_meeting(self):
        self.meeting_count += 1

    def add(self, speaker: str, text: str):
        self.messages.append({
            "speaker": speaker,
            "text": text,
            "time": time.time(),
            "meeting": self.meeting_count,
        })

    def get_current_meeting_messages(self) -> list[dict]:
        return [m for m in self.messages if m["meeting"] == self.meeting_count]

    def get_all_messages(self) -> list[dict]:
        return list(self.messages)

    def clear(self):
        self.messages.clear()
        self.meeting_count = 0
