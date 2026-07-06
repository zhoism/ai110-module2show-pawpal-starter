"""Tests for the algorithmic features: sorting, filtering, recurrence, conflicts."""

from datetime import date, timedelta

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Recurrence,
    ScheduledTask,
    Species,
    Task,
)


# --- sorting by time ---------------------------------------------------------

def test_sort_by_time_orders_by_preferred_time(scheduler, make_task):
    late = make_task("Evening walk", 30, preferred_time=18 * 60)
    early = make_task("Breakfast", 10, preferred_time=7 * 60)
    noon = make_task("Midday play", 20, preferred_time=12 * 60)
    result = scheduler.sort_by_time([late, early, noon])
    assert [t.title for t in result] == ["Breakfast", "Midday play", "Evening walk"]


def test_sort_by_time_puts_untimed_last_in_input_order(scheduler, make_task):
    a = make_task("Untimed A", 10)
    timed = make_task("Timed", 10, preferred_time=9 * 60)
    b = make_task("Untimed B", 10)
    result = scheduler.sort_by_time([a, timed, b])
    assert [t.title for t in result] == ["Timed", "Untimed A", "Untimed B"]


# --- filtering ---------------------------------------------------------------

def test_pet_pending_and_completed_tasks(make_task):
    pet = Pet(name="Mochi", species=Species.CAT)
    done, todo = make_task("Done"), make_task("Todo")
    done.completed = True
    pet.add_task(done)
    pet.add_task(todo)
    assert pet.pending_tasks() == [todo]
    assert pet.completed_tasks() == [done]


def test_owner_tasks_for_pet_case_insensitive(make_task):
    owner = Owner(name="Jordan")
    dog, cat = Pet(name="Biscuit"), Pet(name="Mochi", species=Species.CAT)
    owner.add_pet(dog)
    owner.add_pet(cat)
    owner.add_task(dog, make_task("Walk"))
    owner.add_task(cat, make_task("Brush"))
    assert [t.title for t in owner.tasks_for("biscuit")] == ["Walk"]
    assert owner.tasks_for("Goldfish") == []  # unknown pet -> empty, no crash


def test_owner_tasks_by_status(make_task):
    owner = Owner(name="Jordan")
    pet = Pet(name="Biscuit")
    owner.add_pet(pet)
    done, todo = make_task("Done"), make_task("Todo")
    done.completed = True
    owner.add_task(pet, done)
    owner.add_task(pet, todo)
    assert owner.tasks_by_status(completed=True) == [done]
    assert owner.tasks_by_status(completed=False) == [todo]


# --- recurring tasks -----------------------------------------------------------

def test_daily_task_completion_spawns_next_day(make_task):
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    task.due_date = date(2026, 7, 5)
    nxt = task.mark_complete()
    assert task.completed is True
    assert nxt is not None and nxt.completed is False
    assert nxt.due_date == date(2026, 7, 6)  # today + 1 day
    assert nxt.title == task.title and nxt.id != task.id


def test_weekly_task_completion_spawns_next_week(make_task):
    task = make_task("Grooming", 30, recurrence=Recurrence.WEEKLY)
    task.due_date = date(2026, 7, 5)
    nxt = task.mark_complete()
    assert nxt.due_date == date(2026, 7, 12)  # today + 7 days


def test_once_task_completion_spawns_nothing(make_task):
    task = make_task("Vet visit", 45)  # Recurrence.ONCE default
    assert task.mark_complete() is None


def test_double_completion_does_not_duplicate(make_task):
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    assert task.mark_complete() is not None
    assert task.mark_complete() is None  # second call is a no-op


def test_recurrence_defaults_due_date_to_today(make_task):
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    nxt = task.mark_complete()
    assert nxt.due_date == date.today() + timedelta(days=1)


def test_pet_complete_task_appends_next_occurrence(make_task):
    pet = Pet(name="Biscuit")
    task = make_task("Feeding", 10, recurrence=Recurrence.DAILY)
    pet.add_task(task)
    nxt = pet.complete_task(task.id)
    assert task.completed is True
    assert nxt in pet.tasks and len(pet.tasks) == 2


# --- conflict detection -----------------------------------------------------------

def test_detect_conflicts_reports_overlap(scheduler, make_task):
    a = ScheduledTask(make_task("Walk"), start_time=480, end_time=520)
    b = ScheduledTask(make_task("Feeding"), start_time=500, end_time=530)
    warnings = scheduler.detect_conflicts([a, b])
    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Feeding" in warnings[0]


def test_detect_conflicts_ignores_back_to_back(scheduler, make_task):
    a = ScheduledTask(make_task("Walk"), start_time=480, end_time=510)
    b = ScheduledTask(make_task("Feeding"), start_time=510, end_time=520)
    assert scheduler.detect_conflicts([a, b]) == []


def test_detect_preferred_time_conflicts(scheduler, make_task):
    vet = make_task("Vet", 45, preferred_time=15 * 60, is_fixed=True)
    groom = make_task("Grooming", 30, preferred_time=15 * 60, is_fixed=True)
    warnings = scheduler.detect_preferred_time_conflicts([vet, groom])
    assert len(warnings) == 1
    assert "Vet" in warnings[0] and "Grooming" in warnings[0]
    # untimed tasks never conflict
    assert scheduler.detect_preferred_time_conflicts([make_task("A"), make_task("B")]) == []


def test_long_task_conflicts_with_all_spanned_tasks(scheduler, make_task):
    # A (09:00, 120min) spans both B (09:30) and C (10:00) — both must be reported,
    # not just the adjacent pair (regression for the max-reach sweep).
    a = make_task("Long groom", 120, preferred_time=9 * 60)
    b = make_task("Snack", 10, preferred_time=9 * 60 + 30)
    c = make_task("Walk", 10, preferred_time=10 * 60)
    warnings = scheduler.detect_preferred_time_conflicts([a, b, c])
    assert len(warnings) == 2
    assert all("Long groom" in w for w in warnings)


def test_completed_tasks_never_conflict(scheduler, make_task):
    done = make_task("Done breakfast", 10, preferred_time=8 * 60)
    done.completed = True
    fresh = make_task("New breakfast", 10, preferred_time=8 * 60)
    assert scheduler.detect_preferred_time_conflicts([done, fresh]) == []


def test_shifted_slot_reason_reflects_new_time(scheduler, make_task, default_constraints):
    vet = make_task("Vet", 45, preferred_time=15 * 60, is_fixed=True)
    groom = make_task("Grooming", 30, preferred_time=15 * 60, is_fixed=True)
    plan = scheduler.generate([vet, groom], default_constraints)
    shifted = [i for i in plan.items if "shifted" in i.reason]
    assert shifted, "one of the colliding fixed tasks should be shifted"
    assert fmt_start(shifted[0]) in shifted[0].reason


def fmt_start(item):
    from pawpal_system import fmt
    return fmt(item.start_time)


def test_generate_warns_on_fixed_conflict(scheduler, make_task, default_constraints):
    vet = make_task("Vet", 45, preferred_time=15 * 60, is_fixed=True)
    groom = make_task("Grooming", 30, preferred_time=15 * 60, is_fixed=True)
    plan = scheduler.generate([vet, groom], default_constraints)
    assert plan.warnings  # conflict surfaced as warning, not a crash
    assert "Warnings:" in plan.explain()


# --- generate() skips completed ------------------------------------------------

def test_generate_skips_completed_tasks(scheduler, make_task, default_constraints):
    done = make_task("Already walked", 30, Priority.HIGH)
    done.completed = True
    todo = make_task("Feeding", 10, Priority.HIGH)
    plan = scheduler.generate([done, todo], default_constraints)
    assert [i.task.title for i in plan.items] == ["Feeding"]
    assert done in plan.skipped
    assert plan.skipped_reasons[done.id] == "already completed"


def test_fixed_task_before_day_start_is_skipped(scheduler, make_task, default_constraints):
    early = make_task("Dawn walk", 30, preferred_time=6 * 60, is_fixed=True)
    plan = scheduler.generate([early], default_constraints)  # day starts 08:00
    assert plan.items == []
    assert plan.skipped_reasons[early.id] == "before day start"
