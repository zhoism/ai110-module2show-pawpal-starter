"""Unit tests for the PawPal+ domain model (enums + dataclasses)."""

import pytest

from pawpal_system import (
    Constraints,
    Owner,
    Pet,
    Preferences,
    Priority,
    ScheduledTask,
    Species,
    Task,
    fmt,
    to_minutes,
)


# --- time helpers ----------------------------------------------------------

@pytest.mark.parametrize(
    "text,minutes",
    [("00:00", 0), ("08:00", 480), ("08:30", 510), ("20:00", 1200), ("23:59", 1439)],
)
def test_to_minutes_parses_hhmm(text, minutes):
    assert to_minutes(text) == minutes


@pytest.mark.parametrize(
    "minutes,text",
    [(0, "00:00"), (480, "08:00"), (510, "08:30"), (1200, "20:00")],
)
def test_fmt_formats_minutes(minutes, text):
    assert fmt(minutes) == text


def test_to_minutes_and_fmt_roundtrip():
    assert fmt(to_minutes("14:45")) == "14:45"


# --- Priority --------------------------------------------------------------

def test_priority_high_greater_than_low():
    assert Priority.HIGH > Priority.MEDIUM > Priority.LOW


def test_priority_from_label():
    assert Priority.from_label("high") is Priority.HIGH
    assert Priority.from_label("LOW") is Priority.LOW  # case-insensitive


def test_priority_from_label_invalid_raises():
    with pytest.raises((KeyError, ValueError)):
        Priority.from_label("urgent")


def test_priority_label_property():
    assert Priority.HIGH.label == "high"


# --- Task ------------------------------------------------------------------

@pytest.mark.parametrize(
    "duration,remaining,expected",
    [(30, 60, True), (60, 60, True), (61, 60, False), (1, 0, False)],
)
def test_task_fits_in_boundary(make_task, duration, remaining, expected):
    task = make_task("X", duration)
    assert task.fits_in(remaining) is expected


def test_task_score_increases_with_priority(make_task):
    low = make_task("a", 30, Priority.LOW)
    high = make_task("b", 30, Priority.HIGH)
    assert high.score() > low.score()


def test_task_from_dict_maps_ui_payload():
    task = Task.from_dict(
        {"title": "Morning walk", "duration_minutes": 20, "priority": "high"}
    )
    assert task.title == "Morning walk"
    assert task.duration_minutes == 20
    assert task.priority is Priority.HIGH


# --- ScheduledTask ---------------------------------------------------------

def test_scheduledtask_duration_matches(make_task):
    item = ScheduledTask(task=make_task("walk", 30), start_time=480, end_time=510)
    assert item.duration() == 30


def test_scheduledtask_overlaps_true(make_task):
    a = ScheduledTask(task=make_task(), start_time=480, end_time=520)
    b = ScheduledTask(task=make_task(), start_time=500, end_time=540)
    assert a.overlaps(b) is True
    assert b.overlaps(a) is True


def test_scheduledtask_overlaps_false_when_back_to_back(make_task):
    a = ScheduledTask(task=make_task(), start_time=480, end_time=510)
    b = ScheduledTask(task=make_task(), start_time=510, end_time=540)
    assert a.overlaps(b) is False


# --- Constraints -----------------------------------------------------------

def test_constraints_remaining_minutes(default_constraints):
    # available_minutes is 12*60 = 720
    assert default_constraints.remaining_minutes(120) == 600


def test_constraints_available_defaults_to_window():
    c = Constraints(day_start=8 * 60, day_end=12 * 60, available_minutes=None)
    # full plan capacity == the day window when not explicitly capped
    assert c.remaining_minutes(0) == 4 * 60


def test_constraints_from_preferences():
    prefs = Preferences(day_start=9 * 60, day_end=17 * 60, available_minutes=120)
    c = Constraints.from_preferences(prefs)
    assert c.day_start == 9 * 60
    assert c.day_end == 17 * 60
    assert c.available_minutes == 120


# --- Owner / Pet -----------------------------------------------------------

def test_pet_add_and_remove_task(make_task):
    pet = Pet(name="Mochi", species=Species.CAT)
    t = make_task("Litter", 5)
    pet.add_task(t)
    assert t in pet.tasks
    pet.remove_task(t.id)
    assert t not in pet.tasks


def test_owner_all_tasks_flattens_pets(make_task):
    owner = Owner(name="Jordan")
    dog = Pet(name="Biscuit", species=Species.DOG)
    cat = Pet(name="Mochi", species=Species.CAT)
    owner.add_pet(dog)
    owner.add_pet(cat)
    owner.add_task(dog, make_task("Walk", 30))
    owner.add_task(cat, make_task("Brush", 10))
    titles = {t.title for t in owner.all_tasks()}
    assert titles == {"Walk", "Brush"}
