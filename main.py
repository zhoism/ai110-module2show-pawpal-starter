"""Demo script for the PawPal+ logic layer.

Temporary testing ground: builds an owner with two pets and several tasks,
then exercises the scheduler plus the algorithmic features — sorting by time,
filtering by pet/status, recurring-task respawn, and conflict detection.

Run with:  python main.py
"""

from datetime import date

from pawpal_system import (
    Constraints,
    Owner,
    Pet,
    Preferences,
    Priority,
    Recurrence,
    Scheduler,
    Species,
    Task,
    fmt,
    to_minutes,
)


def section(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def main() -> None:
    # --- owner + pets ------------------------------------------------------
    owner = Owner(
        name="Jordan",
        preferences=Preferences(
            day_start=to_minutes("08:00"),
            day_end=to_minutes("20:00"),
            available_minutes=150,  # Jordan only has 2.5 free hours today
        ),
    )
    biscuit = Pet(name="Biscuit", species=Species.DOG)
    mochi = Pet(name="Mochi", species=Species.CAT)
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    # --- tasks, deliberately added OUT of time order -------------------------
    owner.add_task(
        biscuit,
        Task("t1", "Evening walk (Biscuit)", 30, Priority.HIGH,
             preferred_time=to_minutes("18:00")),
    )
    owner.add_task(
        biscuit,
        Task("t2", "Breakfast (Biscuit)", 10, Priority.HIGH,
             preferred_time=to_minutes("08:00"), recurrence=Recurrence.DAILY,
             due_date=date.today()),
    )
    owner.add_task(
        biscuit,
        Task("t3", "Vet appointment (Biscuit)", 45, Priority.MEDIUM,
             preferred_time=to_minutes("15:00"), is_fixed=True),
    )
    owner.add_task(
        mochi,
        Task("t4", "Midday play (Mochi)", 20, Priority.LOW,
             preferred_time=to_minutes("12:30")),
    )
    owner.add_task(
        mochi,
        Task("t5", "Litter box cleanup (Mochi)", 15, Priority.MEDIUM),  # no set time
    )
    # deliberate CONFLICT: grooming wants 15:00, same as the fixed vet slot
    owner.add_task(
        mochi,
        Task("t6", "Grooming (Mochi)", 30, Priority.MEDIUM,
             preferred_time=to_minutes("15:00"), is_fixed=True),
    )

    scheduler = Scheduler()

    # --- sorting: tasks listed by time even though they were added out of order --
    section("Tasks sorted by time (untimed last)")
    for t in scheduler.sort_by_time(owner.all_tasks()):
        when = fmt(t.preferred_time) if t.preferred_time is not None else "--:--"
        print(f"  {when}  {t.title}  ({t.duration_minutes} min)")

    # --- filtering: by pet and by completion status --------------------------
    section("Filtering")
    print("  Biscuit's tasks:", [t.title for t in owner.tasks_for("biscuit")])
    print("  Mochi's tasks:  ", [t.title for t in owner.tasks_for("Mochi")])

    # --- recurring tasks: completing today's breakfast spawns tomorrow's ------
    section("Recurring task: complete daily breakfast")
    nxt = biscuit.complete_task("t2")
    print(f"  Completed 't2'; auto-created next occurrence: "
          f"'{nxt.title}' due {nxt.due_date} (id={nxt.id})")
    print("  Pending:  ", [t.title for t in owner.tasks_by_status(completed=False)])
    print("  Completed:", [t.title for t in owner.tasks_by_status(completed=True)])

    # --- conflict detection: vet and grooming both want 15:00 -----------------
    section("Conflict detection (before scheduling)")
    for warning in scheduler.detect_preferred_time_conflicts(owner.all_tasks()):
        print(f"  ⚠️  {warning}")

    # --- schedule --------------------------------------------------------------
    section("Today's Schedule")
    constraints = Constraints.from_preferences(owner.preferences)
    plan = scheduler.generate(owner.all_tasks(), constraints, day=date.today())
    pets = ", ".join(f"{p.name} ({p.species.value})" for p in owner.pets)
    print(f"{owner.name} | pets: {pets} | {plan.day}\n")
    print(plan.explain())


if __name__ == "__main__":
    main()
