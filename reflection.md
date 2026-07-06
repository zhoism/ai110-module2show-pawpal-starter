# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I designed the system UML-first, then turned it into dataclass skeletons before
writing any logic. The guiding principle (from CLAUDE.md) was that all scheduling
logic must live outside `app.py` so it can be unit-tested; `app.py` only builds
inputs, calls the scheduler, and renders the result.

The classes fall into three groups:

*Domain model — "what exists"*
- **`Owner`** — the user. Holds their `Preferences` and a list of `Pet`s;
  `all_tasks()` flattens every pet's tasks into one list for the scheduler.
- **`Pet`** — a pet (name + `Species`) that owns its care `Task`s (`add_task` /
  `remove_task`).
- **`Task`** — one care item: `title`, `duration_minutes`, `priority`, plus
  optional `preferred_time`, `recurrence`, and `is_fixed`. It owns its own
  small decisions: `score()` (ranking) and `fits_in()` (capacity check), and a
  `from_dict()` mapper from the app's session-state dicts.
- **`Preferences`** — the owner's persistent UI settings (day window, time budget).

*Scheduling — "what happens"*
- **`Constraints`** — the resolved, UI-agnostic contract a single run consumes
  (day window, `available_minutes`, `max_tasks`, `strategy`). Built from
  `Preferences` via `from_preferences()` so the scheduler never imports `Owner`.
- **`Scheduler`** — the stateless engine. `generate(tasks, constraints)` runs a
  pipeline: sort → select-within-capacity → assign-times → resolve-conflicts.
- **`DailyPlan`** — the output: ordered `ScheduledTask` slots, a `skipped` list
  with reasons, and `explain()` / `to_dict()` for rendering.
- **`ScheduledTask`** — a `Task` pinned to a `start`/`end` time with the `reason`
  it was placed there; knows its own `duration()` and `overlaps()`.

*Enums* — `Priority`, `Species`, `Recurrence`, `SortStrategy` — replace
stringly-typed values with controlled vocabularies.

**b. Design changes**

Yes — the design changed both during implementation and again after an AI code
review of the finished module.

*Changes made while implementing:*
- **Time became `int` minutes-from-midnight** (not `datetime.time`). `time` has no
  arithmetic, so adding a duration was painful; integers make slot math and test
  assertions trivial, with `to_minutes`/`fmt` converting only at the UI edge.
- **`Priority` became an `IntEnum`** so sorting is a one-line key instead of a
  lookup table.
- **The `Scheduler` was made stateless.** The first UML had it *store* a
  `Constraints`; passing constraints to `generate()` instead removed ambiguous
  state across Streamlit reruns and made tests setup-free.
- **Split `Preferences` (UI) from `Constraints` (engine)** to kill the duplicated
  day-window fields and keep the scheduler UI-agnostic.
- **Added `DailyPlan.skipped_reasons` + `skip()`** so a dropped task carries *why*
  it was dropped — needed for a real explanation.

*Changes made in response to the AI review:* I asked the assistant to look for
missing relationships and logic bottlenecks. The useful findings I acted on:
- **Dead model methods.** `score()` and `fits_in()` were defined and tested but the
  scheduler bypassed them with inline checks. I wired them in, so `Task` is the
  single source of truth for ranking and fit.
- **The explanation threw away its own reasoning.** `_assign_times` computed a
  per-slot `reason`, but `explain()` ignored it. It now surfaces each reason.
- **Half-wired fixed scheduling.** `is_fixed`, `preferred_time`, the
  `PREFERRED_TIME` strategy, and `_resolve_conflicts` were all modeled but inert —
  every task was packed back-to-back from `day_start`. I implemented real
  placement: fixed tasks are pinned at their `preferred_time`, floating tasks fill
  the earliest free gaps around them, and any slot that runs past `day_end` is
  re-skipped. This brought four dead elements to life and added conflict handling
  (a stated README goal).
- **Silent bad-input handling.** An inverted window (`day_end <= day_start`) used to
  yield negative capacity; I clamp capacity at 0 and reordered the skip checks so
  the reason label reflects the most fundamental problem. The plan now also stamps
  the `day` it was built for (it was always `None`).

Every change is covered by a new test (57 passing, up from 51).

*Feedback I deliberately did NOT act on (and why):*
- **A full recurrence engine (daily vs. weekly).** Meaningful weekly logic needs a
  per-task weekday and a real calendar; for a single-day plan it would be
  speculative scope. I kept `Recurrence` as a tagged field and added the `day`
  parameter so it can be built cleanly later.
- **Wiring `Preferences.avoid_times`.** Useful, but it needs windowed placement;
  deferred rather than half-built.
- **Strict-priority selection.** The review flagged that greedy backfill can
  schedule a short LOW task in a gap a long HIGH task can't fit. I kept the greedy
  behavior on purpose — it maximizes tasks completed for a busy owner and is
  predictable — and treat it as a documented tradeoff (see section 2b) rather than
  switching to an optimal knapsack solver.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

**Tradeoff 1 — sweep-based conflict detection reports one warning per later
task, not every colliding pair.** My first version compared only *adjacent*
tasks after sorting by start time. When I asked the AI to review it, it found a
real false negative: a 2-hour task starting at 09:00 overlaps tasks at both
09:30 and 10:00, but the adjacent-pair check only reported the first. I adopted
its fix — an O(n log n) sweep that tracks the window reaching furthest so far —
because it was a correctness bug, not a style preference, and the replacement
was no harder to read. The remaining (deliberate) tradeoff: in a pile-up the
sweep reports each later task against the *longest* earlier window rather than
enumerating every O(n²) pair. For a warning message meant to prompt a human to
fix their day, one clear warning per affected task is more useful than an
exhaustive pair list.

**Tradeoff 2 — greedy selection over optimal packing.** When time is tight, the
scheduler fills leftover gaps with whatever still fits, so a short low-priority
task can make the plan while a long high-priority one is skipped. A knapsack
solver would pack "optimally," but greedy maximizes tasks completed, runs
instantly, and its behavior is predictable enough to explain to the user — which
matters more in a care app than squeezing out optimal minutes.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
