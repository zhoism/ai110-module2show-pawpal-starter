# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## ✨ Features

- **Plans that explain themselves** — every scheduled slot says why it's there ("placed at 08:00, highest priority", "fixed at 15:00", "shifted to avoid a conflict"), and every task that got cut says why it didn't make it (out of time, already done, not due yet).
- **Priority-aware scheduling** — tasks get packed into however much free time the owner actually has, most important first. There are also shortest-first and by-time modes.
- **Sorted by time** — the task list shows the day in order; tasks without a set time go last.
- **Fixed appointments** — a 15:00 vet visit stays at 15:00, and flexible tasks pack around it.
- **Conflict warnings** — if two tasks want the same time, you get a warning naming both (nothing crashes), and the scheduler shifts the later one out of the way automatically.
- **Daily/weekly repeats** — finish a recurring task and the next one gets created on its own, and it won't sneak into today's plan early.
- **Filter views** — see tasks per pet, or split by done vs. not done.
- **Testable core** — all the logic lives in one plain Python file with zero UI code in it, covered by 89 tests.

## 🧱 How it's built

Everything lives in `pawpal_system.py`, split into "the stuff" and "the brain":

- **Owner** — the user. Holds their pets and their preferences (day window, free minutes), and can hand over every task across all pets in one list.
- **Pet** — a name, a species, and its own list of tasks, with methods to add, remove, filter, and complete them.
- **Task** — one care item: what it is, how long it takes, its priority, done or not, and optionally a fixed time or a daily/weekly repeat.
- **Scheduler** — the brain. Stateless: give it tasks and constraints, it gives back a plan. Sorting, filtering, conflict handling, and time assignment all happen here.
- **DailyPlan / ScheduledTask** — the result. Ordered slots that each remember why they were placed, skipped tasks with reasons, and any conflict warnings.

`app.py` (Streamlit) and `main.py` (terminal demo) are both thin layers on top — they collect input, call the scheduler, and show the result.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Output of `python main.py` (the terminal demo script — one owner, two pets, six tasks, a 150-minute time budget, and a fixed 15:00 vet appointment):

```
Today's Schedule — Jordan | pets: Biscuit (dog), Mochi (cat) | 2026-07-05
=========================================================================
Daily plan:
  08:00–08:10 — Feeding (Biscuit) (10 min) [priority: high]
      ↳ placed at 08:00 via priority_first (priority: high)
  08:10–08:20 — Feeding (Mochi) (10 min) [priority: high]
      ↳ placed at 08:10 via priority_first (priority: high)
  08:20–08:50 — Morning walk (Biscuit) (30 min) [priority: high]
      ↳ placed at 08:20 via priority_first (priority: high)
  08:50–09:05 — Litter box cleanup (Mochi) (15 min) [priority: medium]
      ↳ placed at 08:50 via priority_first (priority: medium)
  15:00–15:45 — Vet appointment (Biscuit) (45 min) [priority: medium]
      ↳ fixed at 15:00 (priority: medium)
Total scheduled: 110 min.
Skipped:
  - Laser-pointer playtime (Mochi) (no time left)
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

<!-- Test documentation below — edit freely. -->

Run the suite with:

```bash
python -m pytest
```

**What the tests cover** (89 tests across four files):

- `tests/test_models.py` — the building blocks: time conversion, priority ordering, tasks knowing whether they fit in the remaining time, and owners/pets managing their task lists.
- `tests/test_scheduler.py` — the scheduling behavior: ordering by priority, never blowing the time budget, no overlapping slots, everything staying inside the day window, fixed times being honored, readable output, and weird inputs like an empty list or a day that ends before it starts.
- `tests/test_algorithms.py` — the smarter features: sorting by time, filtering by pet and status, recurring tasks creating their next occurrence, and conflict detection (including the tricky case where one long task overlaps several later ones).
- `tests/test_pawpal.py` — core checks and edge cases: the list comes out in chronological order, finishing a daily task creates tomorrow's copy (with unique ids), duplicate times get flagged, pets with no tasks don't break anything, and tasks due tomorrow stay out of today's plan.

Sample test output:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0
rootdir: pawpal-starter
collected 89 items

tests/test_algorithms.py ....................                            [ 22%]
tests/test_models.py ............................                        [ 53%]
tests/test_pawpal.py ............                                        [ 67%]
tests/test_scheduler.py .............................                    [100%]

============================== 89 passed in 0.05s ==============================
```

**Confidence Level: ★★★★☆ (4/5)**

The whole pipeline — sorting, picking what fits, assigning times, conflicts, recurrence — is covered by tests, most of which were written before the code they test. The process even caught a real bug (recurring tasks due tomorrow used to land in today's plan). Holding back one star for the known rough edges: two tasks with the same name can collide behind the scenes, a fixed appointment can lose its spot to the task cap, and the UI layer itself only has a basic smoke check.

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

<!-- Implemented features documented below — edit freely. -->

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, plus the strategies inside `generate()` | Sorts the task list by time, with untimed tasks at the end. Scheduling itself can run priority-first, shortest-first, or by preferred time — ties always break the same way so results are repeatable. |
| Filtering | `Pet.pending_tasks()` / `completed_tasks()`, `Owner.tasks_for()`, `Owner.tasks_by_status()` | View tasks per pet or by done/not-done. The scheduler also filters on its own — completed tasks, tasks that don't fit, and tasks not due yet all get skipped, each with a reason attached. |
| Conflict handling | `Scheduler.detect_conflicts()`, `detect_preferred_time_conflicts()`, `_resolve_conflicts()` | Collisions come back as warning messages instead of crashes. When two fixed tasks want the same time, the later one gets shifted and the plan says so; anything pushed outside the day window gets skipped instead. |
| Recurring tasks | `Task.mark_complete()`, `next_occurrence()`, `Pet.complete_task()` | Finishing a daily or weekly task creates the next one automatically (+1 or +7 days). One-time tasks don't respawn, completing twice doesn't duplicate, and tomorrow's copy stays out of today's plan. |



## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

<!-- Walkthrough below — edit freely. -->

**What you can do in the app** (`streamlit run app.py`): enter your name, set your day window and free minutes in the sidebar, add pets, add tasks to each pet (with duration, priority, and an optional fixed time), browse the task list sorted by time with a per-pet filter, and generate the day's schedule. If two tasks ever want the same time, a warning shows up right away — you don't have to hit generate to find out.

**Example workflow:**

1. Enter an owner name and set the sidebar to a day from 08:00 to 20:00 with 150 free minutes.
2. Add two pets — say Biscuit the dog and Mochi the cat. They stick around as you click through the app, so you can keep adding to them.
3. Add tasks to each pet: a high-priority morning walk, feeding, and a vet appointment locked to 15:00. The table re-sorts by time as you go, with untimed tasks at the bottom.
4. Add a grooming task also locked to 15:00 — a warning pops up immediately naming both colliding tasks, before you've even scheduled anything.
5. Hit **Generate schedule**. You get the plan as a table, a note that the later of the two 15:00 tasks was moved (with a suggestion to pick a new time if that doesn't work), any skipped tasks with their reasons, and a "Why this plan?" section with the full explanation.

**What the scheduler is doing under the hood:** packing from the start of the day in priority order, pinning fixed appointments, catching and resolving the time conflict (and being upfront about it), cutting whatever doesn't fit in 150 minutes, and keeping tomorrow's recurring tasks out of today's plan.

**Sample CLI output** from `python main.py` (same logic, just run from the terminal):

```
=== Tasks sorted by time (untimed last) =========================
  08:00  Breakfast (Biscuit)  (10 min)
  12:30  Midday play (Mochi)  (20 min)
  15:00  Vet appointment (Biscuit)  (45 min)
  15:00  Grooming (Mochi)  (30 min)
  18:00  Evening walk (Biscuit)  (30 min)
  --:--  Litter box cleanup (Mochi)  (15 min)

=== Filtering ===================================================
  Biscuit's tasks: ['Evening walk (Biscuit)', 'Breakfast (Biscuit)', 'Vet appointment (Biscuit)']
  Mochi's tasks:   ['Midday play (Mochi)', 'Litter box cleanup (Mochi)', 'Grooming (Mochi)']

=== Recurring task: complete daily breakfast ====================
  Completed 't2'; auto-created next occurrence: 'Breakfast (Biscuit)' due 2026-07-07 (id=t2~2026-07-07)
  Pending:   ['Evening walk (Biscuit)', 'Vet appointment (Biscuit)', 'Breakfast (Biscuit)', 'Midday play (Mochi)', 'Litter box cleanup (Mochi)', 'Grooming (Mochi)']
  Completed: ['Breakfast (Biscuit)']

=== Conflict detection (before scheduling) ======================
  ⚠️  'Vet appointment (Biscuit)' (15:00–15:45) overlaps 'Grooming (Mochi)' starting 15:00

=== Today's Schedule ============================================
Jordan | pets: Biscuit (dog), Mochi (cat) | 2026-07-06

Daily plan:
  08:00–08:30 — Evening walk (Biscuit) (30 min) [priority: high]
      ↳ placed at 08:00 via priority_first (priority: high)
  08:30–08:45 — Litter box cleanup (Mochi) (15 min) [priority: medium]
      ↳ placed at 08:30 via priority_first (priority: medium)
  08:45–09:05 — Midday play (Mochi) (20 min) [priority: low]
      ↳ placed at 08:45 via priority_first (priority: low)
  15:00–15:30 — Grooming (Mochi) (30 min) [priority: medium]
      ↳ fixed at 15:00 (priority: medium)
  15:30–16:15 — Vet appointment (Biscuit) (45 min) [priority: medium]
      ↳ shifted to 15:30 to avoid a conflict (wanted 15:00)
Total scheduled: 140 min.
Skipped:
  - Breakfast (Biscuit) (already completed)
  - Breakfast (Biscuit) (not due until 2026-07-07)
Warnings:
  ! 'Grooming (Mochi)' (15:00–15:30) overlaps 'Vet appointment (Biscuit)' (15:00–15:45)
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
