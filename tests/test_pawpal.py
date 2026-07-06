"""Core verification suite for PawPal+ (smoke tests + edge cases).

Covers the three required categories — sorting correctness, recurrence logic,
conflict detection — plus edge cases surfaced by a fresh-session test-plan
review (chained recurrences, ties, zero-duration windows, all-done inputs,
and due-date-aware scheduling).
"""

from datetime import date

from pawpal_system import (
    Pet,
    Priority,
    Recurrence,
    Species,
    SortStrategy,
    Task,
)


# --- smoke tests -------------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task(id="t1", title="Morning walk", duration_minutes=30, priority=Priority.HIGH)
    assert task.completed is False  # starts incomplete
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species=Species.DOG)
    before = len(pet.tasks)
    pet.add_task(Task(id="t2", title="Feeding", duration_minutes=10))
    assert len(pet.tasks) == before + 1


# --- sorting correctness -------------------------------------------------------

def test_tasks_returned_in_chronological_order(scheduler, make_task):
    evening = make_task("Evening walk", 30, preferred_time=18 * 60)
    morning = make_task("Breakfast", 10, preferred_time=8 * 60)
    noon = make_task("Lunch", 10, preferred_time=12 * 60)
    result = scheduler.sort_by_time([evening, morning, noon])
    times = [t.preferred_time for t in result]
    assert times == sorted(times)
    assert [t.title for t in result] == ["Breakfast", "Lunch", "Evening walk"]


def test_preferred_time_strategy_ties_break_by_priority(scheduler, make_task, default_constraints):
    default_constraints.strategy = SortStrategy.PREFERRED_TIME
    low = make_task("Low", 10, Priority.LOW, preferred_time=9 * 60)
    high = make_task("High", 10, Priority.HIGH, preferred_time=9 * 60)
    plan = scheduler.generate([low, high], default_constraints)
    assert [i.task.title for i in plan.items] == ["High", "Low"]


# --- recurrence logic -----------------------------------------------------------

def test_completing_daily_task_creates_tomorrows_task(make_task):
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    task.due_date = date(2026, 7, 5)
    nxt = task.mark_complete()
    assert nxt is not None
    assert nxt.due_date == date(2026, 7, 6)  # the following day
    assert nxt.completed is False


def test_chained_daily_completions_keep_unique_ids_and_advance_dates(make_task):
    pet = Pet(name="Biscuit")
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    task.due_date = date(2026, 7, 5)
    pet.add_task(task)
    gen2 = pet.complete_task(task.id)   # spawns day 2
    gen3 = pet.complete_task(gen2.id)   # spawns day 3
    ids = [t.id for t in pet.tasks]
    assert len(ids) == len(set(ids)) == 3  # every occurrence keeps a unique id
    assert gen3.due_date == date(2026, 7, 7)  # advances from gen2's due date


def test_spawned_instance_inherits_recurrence_and_can_respawn(make_task):
    task = make_task("Meds", 5, recurrence=Recurrence.WEEKLY)
    task.due_date = date(2026, 7, 5)
    nxt = task.mark_complete()
    assert nxt.recurrence is Recurrence.WEEKLY
    assert nxt.mark_complete().due_date == date(2026, 7, 19)  # 7/12 + 7 days


def test_generate_defers_task_due_after_plan_day(scheduler, make_task, default_constraints):
    """Completing today's daily task must not put tomorrow's instance in today's plan."""
    pet = Pet(name="Biscuit")
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    task.due_date = date(2026, 7, 5)
    pet.add_task(task)
    pet.complete_task(task.id)  # spawns the occurrence due 2026-07-06
    plan = scheduler.generate(pet.pending_tasks(), default_constraints, day=date(2026, 7, 5))
    assert plan.items == []  # tomorrow's task is NOT scheduled today
    assert "not due" in " ".join(plan.skipped_reasons.values())


# --- conflict detection -----------------------------------------------------------

def test_scheduler_flags_duplicate_times(scheduler, make_task):
    vet = make_task("Vet visit", 30, preferred_time=15 * 60)
    groom = make_task("Grooming", 30, preferred_time=15 * 60)  # exact same time
    warnings = scheduler.detect_preferred_time_conflicts([vet, groom])
    assert len(warnings) == 1
    assert "Vet visit" in warnings[0] and "Grooming" in warnings[0]


def test_zero_duration_window_does_not_conflict(scheduler, make_task):
    ping = make_task("Ping", 0, preferred_time=9 * 60)  # empty window [t, t)
    walk = make_task("Walk", 30, preferred_time=9 * 60)
    assert scheduler.detect_preferred_time_conflicts([ping, walk]) == []


# --- degenerate inputs -------------------------------------------------------------

def test_pet_with_no_tasks_yields_empty_plan(scheduler, default_constraints):
    pet = Pet(name="Goldie", species=Species.OTHER)
    plan = scheduler.generate(pet.tasks, default_constraints)
    assert plan.items == [] and plan.skipped == [] and plan.total_minutes == 0


def test_all_tasks_completed_yields_empty_plan_with_reasons(scheduler, make_task, default_constraints):
    tasks = [make_task("A"), make_task("B")]
    for t in tasks:
        t.completed = True
    plan = scheduler.generate(tasks, default_constraints)
    assert plan.items == [] and len(plan.skipped) == 2
    assert all(plan.skipped_reasons[t.id] == "already completed" for t in tasks)
