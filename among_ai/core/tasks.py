"""Task state machine for AI players. Tasks take real time to complete."""

import random
import time
from enum import Enum
from among_ai.constants import TASK_DEFINITIONS, NUM_TASKS_TO_WIN


class TaskState(Enum):
    AVAILABLE = "available"
    TRAVELING = "traveling"     # AI is walking to the task location
    IN_PROGRESS = "in_progress" # AI is standing at location, "doing" the task
    COMPLETED = "completed"


class TaskInstance:
    """A single task assigned to a player."""

    def __init__(self, task_name: str, duration: float):
        self.name = task_name
        self.definition = TASK_DEFINITIONS[task_name]
        self.state = TaskState.AVAILABLE
        self.duration = duration       # How long the AI stands at the task doing it
        self.progress_start = 0.0      # Timestamp when IN_PROGRESS started
        self.location = self.definition["location"]
        self.room = self.definition["room"]

    def start_progress(self):
        """Begin working on the task (AI has arrived at location)."""
        self.state = TaskState.IN_PROGRESS
        self.progress_start = time.time()

    def update(self) -> bool:
        """Update task state. Returns True if just completed."""
        if self.state == TaskState.IN_PROGRESS:
            elapsed = time.time() - self.progress_start
            if elapsed >= self.duration:
                self.state = TaskState.COMPLETED
                return True
        return False

    def is_completed(self) -> bool:
        return self.state == TaskState.COMPLETED

    def is_in_progress(self) -> bool:
        return self.state == TaskState.IN_PROGRESS

    def get_progress_fraction(self) -> float:
        """Get 0.0-1.0 progress for in-progress tasks."""
        if self.state != TaskState.IN_PROGRESS:
            return 1.0 if self.is_completed() else 0.0
        elapsed = time.time() - self.progress_start
        return min(1.0, elapsed / self.duration)


class TaskManager:
    """Manages task assignment and completion for all players."""

    def __init__(self, task_duration_min: float = 3.0, task_duration_max: float = 8.0):
        self.task_duration_min = task_duration_min
        self.task_duration_max = task_duration_max
        self.player_tasks: dict[str, list[TaskInstance]] = {}  # colour -> tasks

    def assign_tasks(self, player_colour: str, num_tasks: int = 8) -> list[TaskInstance]:
        """Assign random tasks to a player with randomized durations."""
        available = list(TASK_DEFINITIONS.keys())
        selected = random.sample(available, min(num_tasks, len(available)))
        tasks = []
        for task_name in selected:
            base_duration = TASK_DEFINITIONS[task_name]["duration_base"]
            # Randomize duration around the base, clamped to min/max
            duration = base_duration + random.uniform(-1.0, 2.0)
            duration = max(self.task_duration_min, min(self.task_duration_max, duration))
            tasks.append(TaskInstance(task_name, duration))
        self.player_tasks[player_colour] = tasks
        return tasks

    def get_player_tasks(self, player_colour: str) -> list[TaskInstance]:
        return self.player_tasks.get(player_colour, [])

    def get_available_tasks(self, player_colour: str) -> list[TaskInstance]:
        """Get tasks that haven't been completed yet."""
        return [t for t in self.get_player_tasks(player_colour)
                if t.state in (TaskState.AVAILABLE, TaskState.TRAVELING)]

    def get_completed_count(self, player_colour: str) -> int:
        return sum(1 for t in self.get_player_tasks(player_colour) if t.is_completed())

    def get_total_completed_all_crew(self, crew_colours: list[str]) -> int:
        """Get total tasks completed by all crew members."""
        return sum(self.get_completed_count(c) for c in crew_colours)

    def get_total_tasks_all_crew(self, crew_colours: list[str]) -> int:
        """Get total tasks assigned to all crew members."""
        return sum(len(self.get_player_tasks(c)) for c in crew_colours)

    def update_player_tasks(self, player_colour: str) -> list[str]:
        """Update all in-progress tasks for a player. Returns list of just-completed task names."""
        completed = []
        for task in self.get_player_tasks(player_colour):
            if task.update():
                completed.append(task.name)
        return completed
