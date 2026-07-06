"""Demo script for the PawPal+ logic layer.

Temporary testing ground: builds an owner with two pets and several tasks,
runs the scheduler, and prints today's schedule to the terminal.

Run with:  python main.py
"""

from datetime import date

from pawpal_system import (
    Constraints,
    Owner,
    Pet,
    Preferences,
    Priority,
    Scheduler,
    Species,
    Task,
    to_minutes,
)


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

    # --- tasks (varied durations, priorities, and times) --------------------
    owner.add_task(biscuit, Task("t1", "Morning walk (Biscuit)", 30, Priority.HIGH))
    owner.add_task(biscuit, Task("t2", "Feeding (Biscuit)", 10, Priority.HIGH))
    owner.add_task(
        biscuit,
        Task(
            "t3",
            "Vet appointment (Biscuit)",
            45,
            Priority.MEDIUM,
            preferred_time=to_minutes("15:00"),
            is_fixed=True,
        ),
    )
    owner.add_task(mochi, Task("t4", "Feeding (Mochi)", 10, Priority.HIGH))
    owner.add_task(mochi, Task("t5", "Litter box cleanup (Mochi)", 15, Priority.MEDIUM))
    owner.add_task(mochi, Task("t6", "Laser-pointer playtime (Mochi)", 60, Priority.LOW))

    # --- schedule ------------------------------------------------------------
    constraints = Constraints.from_preferences(owner.preferences)
    plan = Scheduler().generate(owner.all_tasks(), constraints, day=date.today())

    # --- output --------------------------------------------------------------
    pets = ", ".join(f"{p.name} ({p.species.value})" for p in owner.pets)
    header = f"Today's Schedule — {owner.name} | pets: {pets} | {plan.day}"
    print(header)
    print("=" * len(header))
    print(plan.explain())


if __name__ == "__main__":
    main()
