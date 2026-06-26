"""PawPal+ logic layer.

Backend classes for the PawPal+ pet-care planning assistant. This module is the
"logic layer": it owns the domain model (Owner / Pet / Task) and the scheduling
engine (Scheduler -> DailyPlan). It must stay free of any Streamlit / UI imports
so it can be unit-tested independently (see CLAUDE.md).

Design notes
------------
* Times are represented as **integer minutes from midnight** everywhere internally
  (e.g. 08:00 -> 480). Use ``to_minutes`` / ``fmt`` to convert at the UI boundary.
* ``Priority`` is an ``IntEnum`` so tasks sort by importance with a plain key.
* ``Scheduler`` is stateless: ``generate(tasks, constraints) -> DailyPlan``.

This file currently contains **skeletons only** — method bodies raise
``NotImplementedError``. Dataclass fields are real, so objects still construct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, IntEnum


# ---------------------------------------------------------------------------
# Time helpers (UI boundary <-> internal int minutes-from-midnight)
# ---------------------------------------------------------------------------

def to_minutes(hhmm: str) -> int:
    """Parse an ``"HH:MM"`` string into minutes from midnight (``"08:00"`` -> 480)."""
    raise NotImplementedError


def fmt(minutes: int) -> str:
    """Format minutes from midnight as an ``"HH:MM"`` string (480 -> ``"08:00"``)."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Priority(IntEnum):
    """Task importance. Higher value = more important, so tasks sort by this key."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def from_label(cls, label: str) -> "Priority":
        """Map a UI string (``"low"``/``"medium"``/``"high"``) to a member."""
        raise NotImplementedError

    @property
    def label(self) -> str:
        """Lowercase UI label for this member (``Priority.HIGH`` -> ``"high"``)."""
        raise NotImplementedError


class Species(Enum):
    DOG = "dog"
    CAT = "cat"
    OTHER = "other"


class Recurrence(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class SortStrategy(Enum):
    """How the scheduler orders candidate tasks before placing them."""

    PRIORITY_FIRST = "priority_first"
    SHORTEST_FIRST = "shortest_first"
    PREFERRED_TIME = "preferred_time"


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

@dataclass
class Preferences:
    """Owner's persistent scheduling preferences (raw UI settings)."""

    day_start: int = 8 * 60        # 08:00
    day_end: int = 20 * 60         # 20:00
    available_minutes: int | None = None  # None -> derived from the day window
    avoid_times: list[str] = field(default_factory=list)
    explain_plan: bool = True


@dataclass
class Task:
    """A single pet-care task to be scheduled."""

    id: str
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    preferred_time: int | None = None     # minutes from midnight, if fixed-ish
    recurrence: Recurrence = Recurrence.ONCE
    is_fixed: bool = False                 # must run at preferred_time if True

    def score(self) -> float:
        """Ranking score; higher = scheduled sooner. Derived from priority/duration."""
        raise NotImplementedError

    def fits_in(self, remaining_minutes: int) -> bool:
        """True if this task's duration fits within ``remaining_minutes``."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a Task from the app's session_state dict (title/duration/priority)."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet that care tasks belong to."""

    name: str
    species: Species = Species.DOG
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def remove_task(self, task_id: str) -> None:
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner: holds pets and scheduling preferences."""

    name: str
    preferences: Preferences = field(default_factory=Preferences)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        raise NotImplementedError

    def add_task(self, pet: Pet, task: Task) -> None:
        """Convenience: attach a task to one of this owner's pets."""
        raise NotImplementedError

    def all_tasks(self) -> list[Task]:
        """Flatten every task across all of this owner's pets."""
        raise NotImplementedError


@dataclass
class Constraints:
    """Resolved, UI-agnostic contract the scheduler consumes for one run."""

    day_start: int = 8 * 60
    day_end: int = 20 * 60
    max_tasks: int | None = None
    strategy: SortStrategy = SortStrategy.PRIORITY_FIRST
    available_minutes: int | None = None   # None -> day_end - day_start

    def remaining_minutes(self, used: int) -> int:
        """Minutes of capacity left after ``used`` minutes are already scheduled."""
        raise NotImplementedError

    @classmethod
    def from_preferences(cls, prefs: Preferences, **overrides) -> "Constraints":
        """Derive run Constraints from an Owner's Preferences (plus overrides)."""
        raise NotImplementedError


@dataclass
class ScheduledTask:
    """A task placed at a concrete time slot, with the reason it was chosen."""

    task: Task
    start_time: int       # minutes from midnight
    end_time: int         # minutes from midnight
    reason: str = ""

    def duration(self) -> int:
        """Length of this slot in minutes (``end_time - start_time``)."""
        raise NotImplementedError

    def overlaps(self, other: "ScheduledTask") -> bool:
        """True if this slot overlaps ``other`` in time."""
        raise NotImplementedError


@dataclass
class DailyPlan:
    """The scheduler's output: ordered slots, skipped tasks, and an explanation."""

    day: date | None = None
    items: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def add_item(self, item: ScheduledTask) -> None:
        raise NotImplementedError

    def explain(self) -> str:
        """Human-readable rationale for the plan (order, timing, what was skipped)."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Serialize the plan (for the Streamlit UI / JSON)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Scheduler (stateless engine)
# ---------------------------------------------------------------------------

class Scheduler:
    """Turns a list of tasks + constraints into an ordered, explained DailyPlan."""

    def generate(self, tasks: list[Task], constraints: Constraints) -> DailyPlan:
        """Build the daily plan: sort, select within capacity, assign times."""
        raise NotImplementedError

    def _sort_tasks(self, tasks: list[Task], constraints: Constraints) -> list[Task]:
        """Order candidate tasks per ``constraints.strategy`` (deterministic)."""
        raise NotImplementedError

    def _select_tasks(
        self, tasks: list[Task], constraints: Constraints
    ) -> tuple[list[Task], list[tuple[Task, str]]]:
        """Split sorted tasks into (kept, [(skipped, reason), ...]) by capacity/max."""
        raise NotImplementedError

    def _assign_times(
        self, tasks: list[Task], constraints: Constraints
    ) -> list[ScheduledTask]:
        """Lay selected tasks into back-to-back slots starting at ``day_start``."""
        raise NotImplementedError

    def _resolve_conflicts(
        self, items: list[ScheduledTask]
    ) -> list[ScheduledTask]:
        """Shift flexible slots so none overlap (fixed/preferred tasks win)."""
        raise NotImplementedError
