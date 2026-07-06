"""Shared pytest fixtures for PawPal+ scheduler tests."""

import pytest

from pawpal_system import Constraints, Priority, Scheduler, SortStrategy, Task


@pytest.fixture
def make_task():
    """Factory for Tasks with sane defaults; override any field per test.

    Auto-increments the id so callers don't have to think about uniqueness.
    """
    counter = {"n": 0}

    def _make(
        title="Task",
        duration_minutes=30,
        priority=Priority.MEDIUM,
        *,
        id=None,
        preferred_time=None,
        recurrence=None,
        is_fixed=False,
    ):
        counter["n"] += 1
        kwargs = dict(
            id=id or f"t{counter['n']}",
            title=title,
            duration_minutes=duration_minutes,
            priority=priority,
            preferred_time=preferred_time,
            is_fixed=is_fixed,
        )
        if recurrence is not None:
            kwargs["recurrence"] = recurrence
        return Task(**kwargs)

    return _make


@pytest.fixture
def default_constraints():
    """08:00-20:00 window, generous capacity, PRIORITY_FIRST."""
    return Constraints(
        day_start=8 * 60,
        day_end=20 * 60,
        available_minutes=12 * 60,
        max_tasks=100,
        strategy=SortStrategy.PRIORITY_FIRST,
    )


@pytest.fixture
def tight_constraints():
    """Only 60 minutes of capacity to force filtering."""
    return Constraints(
        day_start=8 * 60,
        day_end=20 * 60,
        available_minutes=60,
        max_tasks=100,
        strategy=SortStrategy.PRIORITY_FIRST,
    )


@pytest.fixture
def sample_tasks(make_task):
    """A fixed mix of priorities and durations for ordering tests."""
    return [
        make_task("Feeding", 10, Priority.HIGH),
        make_task("Long enrichment", 60, Priority.LOW),
        make_task("Meds", 5, Priority.HIGH),
        make_task("Grooming", 30, Priority.MEDIUM),
    ]


@pytest.fixture
def scheduler():
    return Scheduler()
