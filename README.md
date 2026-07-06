# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

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

- `tests/test_models.py` — domain model units: time helpers (`"HH:MM"` ↔ minutes), `Priority` ordering and labels, `Task.fits_in`/`score`/`from_dict`, `ScheduledTask` duration/overlap, `Constraints` capacity, and `Owner`/`Pet` task management.
- `tests/test_scheduler.py` — scheduling behavior: priority/shortest-first ordering with deterministic tie-breaks, capacity filtering with recorded skip reasons, back-to-back non-overlapping slots inside the day window, fixed-time placement, `explain()`/`to_dict()` output, and degenerate inputs (empty list, zero minutes, inverted windows, oversized tasks).
- `tests/test_algorithms.py` — the algorithmic features: `sort_by_time`, filtering by pet/status, recurring-task respawn (+1/+7 days), and conflict detection (including the long-task-spans-several-slots regression).
- `tests/test_pawpal.py` — core verification and edge cases: sorting is chronological, completing a daily task creates tomorrow's instance (chained ids stay unique), duplicate times are flagged, zero-duration windows don't conflict, pets with no tasks, all-tasks-done inputs, and future-due tasks are deferred to their own day.

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

The core scheduling pipeline (sorting, capacity selection, time assignment, conflict handling, recurrence) is covered by behavior-level tests that were written before the implementation, and the test process caught a real bug (recurring tasks due tomorrow used to land in today's plan). One star held back because a few known rough edges remain untested or undecided: `Task.from_dict` can produce duplicate ids for same-titled tasks, fixed appointments can lose to `max_tasks` ordering, and the Streamlit UI layer itself has no automated tests.

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
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler._sort_tasks()` | `sort_by_time` orders tasks by `preferred_time` (untimed tasks sink to the end, stable). `_sort_tasks` powers `generate()` with three strategies: `PRIORITY_FIRST` (priority ↓, duration ↑, input order), `SHORTEST_FIRST`, `PREFERRED_TIME`. |
| Filtering | `Pet.pending_tasks()` / `Pet.completed_tasks()`, `Owner.tasks_for(pet_name)`, `Owner.tasks_by_status(completed)` | Filter by completion status per pet or across all pets, and by pet name (case-insensitive; unknown pet returns `[]`). `generate()` also skips completed tasks and anything that doesn't fit, each with a recorded reason (`"already completed"`, `"no time left"`, `"max_tasks reached"`, …). |
| Conflict handling | `Scheduler.detect_conflicts()`, `Scheduler.detect_preferred_time_conflicts()`, `Scheduler._resolve_conflicts()` | Detection returns warning strings (never crashes): overlapping scheduled slots, or fixed tasks whose requested windows collide. Resolution shifts the flexible/later slot after the collision and rewrites its reason (`"shifted to 15:30 … (wanted 15:00)"`); slots pushed outside the day window are re-skipped. Warnings surface in `DailyPlan.warnings` and `explain()`. |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Pet.complete_task(task_id)` | Completing a `DAILY`/`WEEKLY` task auto-creates the next occurrence (`due_date + 1 day` or `+ 7 days` via `timedelta`); `Pet.complete_task` appends it to the pet's list. `ONCE` tasks spawn nothing, and double-completion is a guarded no-op. |



## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
