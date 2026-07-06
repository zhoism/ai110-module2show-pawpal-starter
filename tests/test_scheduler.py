"""Behavioral tests for the PawPal+ Scheduler.

These define the contract the scheduler must satisfy. Times are int minutes
from midnight; day_start defaults to 08:00 (480) in the fixtures.
"""

from datetime import date

import pytest

from pawpal_system import Constraints, Priority, SortStrategy


# --- sorting ---------------------------------------------------------------

def test_priority_first_orders_high_before_low(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    priorities = [item.task.priority for item in plan.items]
    # non-increasing priority order
    assert priorities == sorted(priorities, reverse=True)
    assert priorities[0] is Priority.HIGH


def test_shortest_first_orders_by_duration(scheduler, sample_tasks, default_constraints):
    default_constraints.strategy = SortStrategy.SHORTEST_FIRST
    plan = scheduler.generate(sample_tasks, default_constraints)
    durations = [item.task.duration_minutes for item in plan.items]
    assert durations == sorted(durations)


def test_tie_break_priority_then_duration(scheduler, make_task, default_constraints):
    longer = make_task("Long medium", 40, Priority.MEDIUM)
    shorter = make_task("Short medium", 10, Priority.MEDIUM)
    plan = scheduler.generate([longer, shorter], default_constraints)
    # equal priority -> shorter duration scheduled first
    assert plan.items[0].task.title == "Short medium"


def test_sort_stable_for_equal_priority_and_duration(scheduler, make_task, default_constraints):
    first = make_task("First", 20, Priority.MEDIUM)
    second = make_task("Second", 20, Priority.MEDIUM)
    plan = scheduler.generate([first, second], default_constraints)
    assert [i.task.title for i in plan.items] == ["First", "Second"]


# --- filtering / capacity --------------------------------------------------

def test_skips_tasks_when_time_runs_out(scheduler, sample_tasks, tight_constraints):
    plan = scheduler.generate(sample_tasks, tight_constraints)
    assert len(plan.skipped) >= 1
    scheduled_ids = {i.task.id for i in plan.items}
    skipped_ids = {t.id for t in plan.skipped}
    assert scheduled_ids.isdisjoint(skipped_ids)


def test_total_minutes_never_exceeds_available(scheduler, sample_tasks, tight_constraints):
    plan = scheduler.generate(sample_tasks, tight_constraints)
    assert plan.total_minutes <= tight_constraints.available_minutes
    assert plan.total_minutes == sum(i.duration() for i in plan.items)


def test_respects_max_tasks(scheduler, sample_tasks, default_constraints):
    default_constraints.max_tasks = 2
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert len(plan.items) == 2
    assert len(plan.skipped) == 2


def test_low_priority_dropped_before_high_under_pressure(scheduler, sample_tasks, tight_constraints):
    plan = scheduler.generate(sample_tasks, tight_constraints)
    scheduled_priorities = {i.task.priority for i in plan.items}
    skipped_priorities = {t.priority for t in plan.skipped}
    assert Priority.HIGH in scheduled_priorities
    assert Priority.LOW in skipped_priorities


def test_skipped_records_reason(scheduler, sample_tasks, tight_constraints):
    plan = scheduler.generate(sample_tasks, tight_constraints)
    for task in plan.skipped:
        assert plan.skipped_reasons.get(task.id)  # present and non-empty


# --- time assignment / conflicts ------------------------------------------

def test_first_task_starts_at_day_start(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert plan.items[0].start_time == default_constraints.day_start


def test_tasks_are_back_to_back(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    for prev, nxt in zip(plan.items, plan.items[1:]):
        assert nxt.start_time == prev.end_time


def test_no_overlapping_slots(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    items = plan.items
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            assert not a.overlaps(b)


def test_all_tasks_within_day_window(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    for item in plan.items:
        assert item.start_time >= default_constraints.day_start
        assert item.end_time <= default_constraints.day_end


# --- explanation / output --------------------------------------------------

def test_explain_non_empty(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert plan.explain().strip()


def test_explain_mentions_each_scheduled_task(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    text = plan.explain()
    for item in plan.items:
        assert item.task.title in text


def test_explain_includes_reasoning(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert "priority" in plan.explain().lower()


def test_output_time_formatted_hhmm(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert "08:00" in plan.explain()


def test_to_dict_contains_items_with_times(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints)
    data = plan.to_dict()
    assert isinstance(data["items"], list) and data["items"]
    first = data["items"][0]
    assert {"title", "start", "end"} <= set(first)
    assert first["start"] == "08:00"


# --- edge cases ------------------------------------------------------------

def test_empty_task_list_returns_empty_plan(scheduler, default_constraints):
    plan = scheduler.generate([], default_constraints)
    assert plan.items == []
    assert plan.skipped == []
    assert plan.total_minutes == 0


def test_single_task_schedules_at_start(scheduler, make_task, default_constraints):
    task = make_task("Solo walk", 30, Priority.HIGH)
    plan = scheduler.generate([task], default_constraints)
    assert len(plan.items) == 1
    assert plan.items[0].start_time == default_constraints.day_start
    assert plan.items[0].end_time == default_constraints.day_start + 30


def test_zero_available_minutes_skips_all(scheduler, sample_tasks, default_constraints):
    default_constraints.available_minutes = 0
    plan = scheduler.generate(sample_tasks, default_constraints)
    assert plan.items == []
    assert len(plan.skipped) == len(sample_tasks)


def test_task_longer_than_window_is_skipped(scheduler, make_task):
    constraints = Constraints(day_start=8 * 60, day_end=20 * 60, available_minutes=60)
    big = make_task("Marathon hike", 120, Priority.HIGH)
    plan = scheduler.generate([big], constraints)
    assert plan.items == []
    assert big in plan.skipped


def test_invalid_duration_is_skipped(scheduler, make_task, default_constraints):
    bad = make_task("Broken", 0, Priority.HIGH)
    plan = scheduler.generate([bad], default_constraints)
    assert bad not in [i.task for i in plan.items]
    assert bad in plan.skipped


def test_inverted_window_skips_all(scheduler, sample_tasks):
    # day_end before day_start -> capacity clamps to 0 instead of going negative
    bad = Constraints(day_start=20 * 60, day_end=8 * 60, available_minutes=None)
    plan = scheduler.generate(sample_tasks, bad)
    assert plan.items == []
    assert len(plan.skipped) == len(sample_tasks)


# --- refinements from the AI code review ----------------------------------

def test_generate_stamps_day(scheduler, sample_tasks, default_constraints):
    plan = scheduler.generate(sample_tasks, default_constraints, day=date(2026, 6, 25))
    assert plan.day == date(2026, 6, 25)
    assert plan.to_dict()["day"] == "2026-06-25"


def test_explain_shows_slot_reason(scheduler, make_task, default_constraints):
    plan = scheduler.generate([make_task("Walk", 30, Priority.HIGH)], default_constraints)
    assert plan.items[0].reason in plan.explain()


def test_fixed_task_placed_at_preferred_time(scheduler, make_task, default_constraints):
    vet = make_task("Vet appt", 30, Priority.MEDIUM, preferred_time=15 * 60, is_fixed=True)
    plan = scheduler.generate([vet], default_constraints)
    assert plan.items[0].start_time == 15 * 60
    assert plan.items[0].end_time == 15 * 60 + 30


def test_floating_task_avoids_fixed_slot(scheduler, make_task, default_constraints):
    vet = make_task("Vet appt", 60, Priority.LOW, preferred_time=8 * 60, is_fixed=True)
    walk = make_task("Walk", 30, Priority.HIGH)  # higher priority, but must not overlap
    plan = scheduler.generate([vet, walk], default_constraints)
    slots = {i.task.title: i for i in plan.items}
    assert slots["Vet appt"].start_time == 8 * 60          # fixed time honored
    assert not slots["Walk"].overlaps(slots["Vet appt"])   # floating steps around it


def test_slot_pushed_past_day_end_is_skipped(scheduler, make_task):
    # fixed task placed so late it would end after the day window -> re-skipped
    c = Constraints(day_start=8 * 60, day_end=9 * 60, available_minutes=None)
    late = make_task("Late vet", 30, Priority.HIGH, preferred_time=8 * 60 + 45, is_fixed=True)
    plan = scheduler.generate([late], c)
    assert plan.items == []
    assert late in plan.skipped
    assert "past day end" in plan.skipped_reasons[late.id]
