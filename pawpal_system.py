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
    hours, minutes = hhmm.strip().split(":")
    return int(hours) * 60 + int(minutes)


def fmt(minutes: int) -> str:
    """Format minutes from midnight as an ``"HH:MM"`` string (480 -> ``"08:00"``)."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


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
        return cls[label.strip().upper()]

    @property
    def label(self) -> str:
        """Lowercase UI label for this member (``Priority.HIGH`` -> ``"high"``)."""
        return self.name.lower()


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
    completed: bool = False                # done for today

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def score(self) -> float:
        """Ranking score; higher = scheduled sooner. Driven by priority."""
        return float(self.priority.value)

    def fits_in(self, remaining_minutes: int) -> bool:
        """True if this task's duration fits within ``remaining_minutes``."""
        return self.duration_minutes <= remaining_minutes

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a Task from the app's session_state dict (title/duration/priority)."""
        return cls(
            id=str(data.get("id") or data["title"]),
            title=data["title"],
            duration_minutes=int(data["duration_minutes"]),
            priority=Priority.from_label(str(data.get("priority", "medium"))),
            preferred_time=data.get("preferred_time"),
            is_fixed=bool(data.get("is_fixed", False)),
        )


@dataclass
class Pet:
    """A pet that care tasks belong to."""

    name: str
    species: Species = Species.DOG
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove the task with the given id from this pet (no-op if absent)."""
        self.tasks = [t for t in self.tasks if t.id != task_id]


@dataclass
class Owner:
    """The pet owner: holds pets and scheduling preferences."""

    name: str
    preferences: Preferences = field(default_factory=Preferences)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def add_task(self, pet: Pet, task: Task) -> None:
        """Convenience: attach a task to one of this owner's pets."""
        pet.add_task(task)

    def all_tasks(self) -> list[Task]:
        """Flatten every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Constraints:
    """Resolved, UI-agnostic contract the scheduler consumes for one run."""

    day_start: int = 8 * 60
    day_end: int = 20 * 60
    max_tasks: int | None = None
    strategy: SortStrategy = SortStrategy.PRIORITY_FIRST
    available_minutes: int | None = None   # None -> day_end - day_start

    def capacity(self) -> int:
        """Total schedulable minutes: the smaller of the budget and the day window.

        Clamped at 0 so an inverted/empty window (``day_end <= day_start``) or a
        negative budget can never produce negative capacity (review finding L3)."""
        window = max(0, self.day_end - self.day_start)
        if self.available_minutes is None:
            return window
        return max(0, min(self.available_minutes, window))

    def remaining_minutes(self, used: int) -> int:
        """Minutes of capacity left after ``used`` minutes are already scheduled."""
        return self.capacity() - used

    @classmethod
    def from_preferences(cls, prefs: Preferences, **overrides) -> "Constraints":
        """Derive run Constraints from an Owner's Preferences (plus overrides)."""
        base = dict(
            day_start=prefs.day_start,
            day_end=prefs.day_end,
            available_minutes=prefs.available_minutes,
        )
        base.update(overrides)
        return cls(**base)


@dataclass
class ScheduledTask:
    """A task placed at a concrete time slot, with the reason it was chosen."""

    task: Task
    start_time: int       # minutes from midnight
    end_time: int         # minutes from midnight
    reason: str = ""

    def duration(self) -> int:
        """Length of this slot in minutes (``end_time - start_time``)."""
        return self.end_time - self.start_time

    def overlaps(self, other: "ScheduledTask") -> bool:
        """True if this slot overlaps ``other`` in time (touching ends do not count)."""
        return self.start_time < other.end_time and other.start_time < self.end_time


@dataclass
class DailyPlan:
    """The scheduler's output: ordered slots, skipped tasks, and an explanation."""

    day: date | None = None
    items: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    skipped_reasons: dict[str, str] = field(default_factory=dict)  # task.id -> why
    total_minutes: int = 0

    def add_item(self, item: ScheduledTask) -> None:
        """Append a scheduled slot to the plan and update the running total."""
        self.items.append(item)
        self.total_minutes += item.duration()

    def skip(self, task: Task, reason: str) -> None:
        """Record a task that did not make the plan, with the reason why."""
        self.skipped.append(task)
        self.skipped_reasons[task.id] = reason

    def explain(self) -> str:
        """Human-readable rationale for the plan (order, timing, what was skipped)."""
        if not self.items and not self.skipped:
            return "No tasks to schedule."

        lines: list[str] = []
        if self.items:
            lines.append("Daily plan:")
            for item in self.items:
                t = item.task
                lines.append(
                    f"  {fmt(item.start_time)}–{fmt(item.end_time)} — {t.title} "
                    f"({t.duration_minutes} min) [priority: {t.priority.label}]"
                )
                if item.reason:
                    lines.append(f"      ↳ {item.reason}")
            lines.append(f"Total scheduled: {self.total_minutes} min.")
        if self.skipped:
            lines.append("Skipped:")
            for task in self.skipped:
                reason = self.skipped_reasons.get(task.id, "no reason given")
                lines.append(f"  - {task.title} ({reason})")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize the plan (for the Streamlit UI / JSON)."""
        return {
            "day": self.day.isoformat() if self.day else None,
            "items": [
                {
                    "title": i.task.title,
                    "start": fmt(i.start_time),
                    "end": fmt(i.end_time),
                    "duration_minutes": i.duration(),
                    "priority": i.task.priority.label,
                    "reason": i.reason,
                }
                for i in self.items
            ],
            "skipped": [
                {"title": t.title, "reason": self.skipped_reasons.get(t.id, "")}
                for t in self.skipped
            ],
            "total_minutes": self.total_minutes,
        }


# ---------------------------------------------------------------------------
# Scheduler (stateless engine)
# ---------------------------------------------------------------------------

class Scheduler:
    """Turns a list of tasks + constraints into an ordered, explained DailyPlan."""

    def generate(
        self, tasks: list[Task], constraints: Constraints, day: date | None = None
    ) -> DailyPlan:
        """Build the daily plan: sort, select within capacity, assign times.

        ``day`` is stamped onto the plan (so ``to_dict()`` / ``explain()`` can name
        the date and future recurrence logic has a day to branch on). Any slot that
        ends after ``day_end`` (e.g. a fixed task placed too late) is re-skipped
        rather than emitted (review findings M5 + L2)."""
        plan = DailyPlan(day=day)
        ordered = self._sort_tasks(tasks, constraints)
        kept, skipped = self._select_tasks(ordered, constraints)
        items = self._resolve_conflicts(self._assign_times(kept, constraints))
        for item in items:
            if item.end_time > constraints.day_end:
                plan.skip(item.task, "pushed past day end")
            else:
                plan.add_item(item)
        for task, reason in skipped:
            plan.skip(task, reason)
        return plan

    def _sort_tasks(self, tasks: list[Task], constraints: Constraints) -> list[Task]:
        """Order candidate tasks per ``constraints.strategy`` (deterministic).

        Tie-break is always (chosen key, then insertion index) so equal tasks
        keep their input order — sorting is reproducible for tests.
        """
        indexed = list(enumerate(tasks))
        strategy = constraints.strategy
        if strategy is SortStrategy.SHORTEST_FIRST:
            key = lambda pair: (pair[1].duration_minutes, pair[0])
        elif strategy is SortStrategy.PREFERRED_TIME:
            far = self.UNSET_TIME
            key = lambda pair: (
                pair[1].preferred_time if pair[1].preferred_time is not None else far,
                -int(pair[1].priority),
                pair[0],
            )
        else:  # PRIORITY_FIRST: highest score, then shortest, then input order
            # uses Task.score() so the model's ranking method is the single source
            # of truth — enriching score() now actually changes ordering (M4).
            key = lambda pair: (-pair[1].score(), pair[1].duration_minutes, pair[0])
        return [task for _, task in sorted(indexed, key=key)]

    # sentinel "no preferred time" sort value (24h in minutes, past any real slot)
    UNSET_TIME = 24 * 60

    def _select_tasks(
        self, tasks: list[Task], constraints: Constraints
    ) -> tuple[list[Task], list[tuple[Task, str]]]:
        """Split sorted tasks into (kept, [(skipped, reason), ...]) by capacity/max."""
        kept: list[Task] = []
        skipped: list[tuple[Task, str]] = []
        cap = constraints.capacity()
        used = 0
        for task in tasks:
            # ordered so the most fundamental problem wins the reason label:
            # invalid duration, then can-never-fit, then max_tasks, then no-room-left (L3).
            if task.duration_minutes <= 0:
                skipped.append((task, "invalid duration"))
            elif task.duration_minutes > cap:
                skipped.append((task, "longer than available time"))
            elif constraints.max_tasks is not None and len(kept) >= constraints.max_tasks:
                skipped.append((task, "max_tasks reached"))
            elif not task.fits_in(cap - used):  # Task owns the fit check (M4)
                skipped.append((task, "no time left"))
            else:
                kept.append(task)
                used += task.duration_minutes
        return kept, skipped

    def _assign_times(
        self, tasks: list[Task], constraints: Constraints
    ) -> list[ScheduledTask]:
        """Assign concrete time slots.

        Fixed tasks (``is_fixed`` with a ``preferred_time``) are pinned at their
        requested time; floating tasks fill the earliest free gaps from
        ``day_start``, stepping over the pinned slots so nothing overlaps (M1).
        """
        fixed = [t for t in tasks if t.is_fixed and t.preferred_time is not None]
        floating = [t for t in tasks if not (t.is_fixed and t.preferred_time is not None)]

        items: list[ScheduledTask] = []
        busy: list[tuple[int, int]] = []
        for task in fixed:
            start = task.preferred_time
            end = start + task.duration_minutes
            items.append(ScheduledTask(
                task=task, start_time=start, end_time=end,
                reason=f"fixed at {fmt(start)} (priority: {task.priority.label})",
            ))
            busy.append((start, end))
        busy.sort()

        cursor = constraints.day_start
        for task in floating:
            start = self._earliest_free(cursor, task.duration_minutes, busy)
            end = start + task.duration_minutes
            items.append(ScheduledTask(
                task=task, start_time=start, end_time=end,
                reason=f"placed at {fmt(start)} via {constraints.strategy.value} "
                       f"(priority: {task.priority.label})",
            ))
            cursor = end
        return items

    @staticmethod
    def _earliest_free(start: int, duration: int, busy: list[tuple[int, int]]) -> int:
        """Earliest start >= ``start`` whose [start, start+duration) avoids all busy slots."""
        candidate = start
        moved = True
        while moved:
            moved = False
            for bs, be in busy:
                if candidate < be and bs < candidate + duration:  # overlaps a busy slot
                    candidate = be
                    moved = True
        return candidate

    def _resolve_conflicts(self, items: list[ScheduledTask]) -> list[ScheduledTask]:
        """Shift any overlapping slots later so none overlap (defensive; back-to-back
        assignment is already conflict-free, but fixed/preferred-time slots may not be)."""
        resolved: list[ScheduledTask] = []
        cursor: int | None = None
        for item in sorted(items, key=lambda i: i.start_time):
            if cursor is not None and item.start_time < cursor:
                shift = cursor - item.start_time
                item = ScheduledTask(
                    item.task, item.start_time + shift, item.end_time + shift, item.reason
                )
            cursor = item.end_time
            resolved.append(item)
        return resolved
