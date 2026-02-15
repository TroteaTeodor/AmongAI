"""Meeting/voting/ejection state machine."""

import time
from enum import Enum
from typing import Optional


class MeetingPhase(Enum):
    NONE = "none"
    ALERT = "alert"             # 1.5s flash of who called meeting
    DISCUSSION = "discussion"   # AI chat phase
    VOTING = "voting"           # 30s voting
    RESULTS = "results"         # Show vote tallies
    EJECTION = "ejection"       # Ejection animation
    RESUME = "resume"           # Back to gameplay


class MeetingManager:
    """Manages the emergency meeting lifecycle."""

    def __init__(self, discussion_time: int = 30, voting_time: int = 30):
        self.phase = MeetingPhase.NONE
        self.discussion_time = discussion_time
        self.voting_time = voting_time
        self.caller_colour: Optional[str] = None
        self.body_colour: Optional[str] = None  # If reported body
        self.is_report: bool = False

        self._phase_start = 0.0
        self._alert_duration = 2.5
        self._ejection_duration = 5.0
        self._results_duration = 3.0

        # Votes: {voter_colour: voted_for_colour_or_None}
        self.votes: dict[str, Optional[str]] = {}
        self.ejected_colour: Optional[str] = None

        # Chat messages from discussion
        self.chat_messages: list[dict] = []

    @property
    def is_active(self) -> bool:
        return self.phase != MeetingPhase.NONE

    def start_meeting(self, caller_colour: str, body_colour: Optional[str] = None):
        """Trigger an emergency meeting."""
        self.caller_colour = caller_colour
        self.body_colour = body_colour
        self.is_report = body_colour is not None
        self.phase = MeetingPhase.ALERT
        self._phase_start = time.time()
        self.votes = {}
        self.ejected_colour = None
        self.chat_messages = []

    def update(self) -> Optional[MeetingPhase]:
        """Update meeting state. Returns the phase if it just changed, else None."""
        if self.phase == MeetingPhase.NONE:
            return None

        elapsed = time.time() - self._phase_start
        old_phase = self.phase

        if self.phase == MeetingPhase.ALERT:
            if elapsed >= self._alert_duration:
                self.phase = MeetingPhase.DISCUSSION
                self._phase_start = time.time()
        elif self.phase == MeetingPhase.DISCUSSION:
            if elapsed >= self.discussion_time:
                self.phase = MeetingPhase.VOTING
                self._phase_start = time.time()
        elif self.phase == MeetingPhase.VOTING:
            if elapsed >= self.voting_time:
                self._tally_votes()
                self.phase = MeetingPhase.RESULTS
                self._phase_start = time.time()
        elif self.phase == MeetingPhase.RESULTS:
            if elapsed >= self._results_duration:
                if self.ejected_colour:
                    self.phase = MeetingPhase.EJECTION
                else:
                    self.phase = MeetingPhase.RESUME
                self._phase_start = time.time()
        elif self.phase == MeetingPhase.EJECTION:
            if elapsed >= self._ejection_duration:
                self.phase = MeetingPhase.RESUME
                self._phase_start = time.time()
        elif self.phase == MeetingPhase.RESUME:
            self.phase = MeetingPhase.NONE

        if self.phase != old_phase:
            return self.phase
        return None

    def cast_vote(self, voter_colour: str, target_colour: Optional[str]):
        """Register a vote. target_colour=None means skip."""
        self.votes[voter_colour] = target_colour

    def all_voted(self, alive_players: list[str]) -> bool:
        """Check if all alive players have voted."""
        return all(p in self.votes for p in alive_players)

    def force_end_voting(self):
        """End voting early (all votes in)."""
        self._tally_votes()
        self.phase = MeetingPhase.RESULTS
        self._phase_start = time.time()

    def _tally_votes(self):
        """Count votes and determine who gets ejected."""
        counts: dict[str, int] = {}
        skips = 0
        for voter, target in self.votes.items():
            if target is None:
                skips += 1
            else:
                counts[target] = counts.get(target, 0) + 1

        if not counts:
            self.ejected_colour = None
            return

        max_votes = max(counts.values())
        # Need more than 1 vote and more than skips
        top_voted = [c for c, v in counts.items() if v == max_votes]
        if len(top_voted) == 1 and max_votes >= 2 and max_votes > skips:
            self.ejected_colour = top_voted[0]
        else:
            self.ejected_colour = None  # Tie or not enough votes

    def add_chat_message(self, speaker: str, text: str):
        self.chat_messages.append({
            "speaker": speaker,
            "text": text,
            "time": time.time(),
        })

    def get_time_remaining(self) -> float:
        """Get seconds remaining in current phase."""
        elapsed = time.time() - self._phase_start
        if self.phase == MeetingPhase.DISCUSSION:
            return max(0, self.discussion_time - elapsed)
        elif self.phase == MeetingPhase.VOTING:
            return max(0, self.voting_time - elapsed)
        return 0

    def get_vote_summary(self) -> dict:
        """Get summary of votes: {target: [list of voters]}."""
        summary = {"Skip": []}
        for voter, target in self.votes.items():
            if target is None:
                summary["Skip"].append(voter)
            else:
                if target not in summary:
                    summary[target] = []
                summary[target].append(voter)
        return summary

    def reset(self):
        """Full reset after meeting ends."""
        self.phase = MeetingPhase.NONE
        self.caller_colour = None
        self.body_colour = None
        self.is_report = False
        self.votes = {}
        self.ejected_colour = None
        self.chat_messages = []
