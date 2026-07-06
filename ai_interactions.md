# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

Two rounds. First: implement the algorithmic layer beyond the base requirements — conflict detection and recurring tasks on top of the required sorting and filtering. I had a fresh planning session propose the approach first, then had the agent build it across multiple files. Second: a testing round where a separate fresh session was asked what edge cases were worth testing for a scheduler with sorting and recurring tasks, then the agent built out the tests and fixed whatever they caught.

**What did the agent do?**

- `pawpal_system.py` — added a due date to tasks, made completing a daily/weekly task auto-create the next occurrence, added conflict detection (returns warnings, never crashes), a sort-by-time method, and per-pet/per-status filters. Also made the scheduler skip completed and not-yet-due tasks with reasons.
- `main.py` — rewrote the demo to add tasks out of order, complete a recurring task, and trigger a deliberate 15:00 conflict so all four features show up in the terminal output.
- `tests/` — grew the suite to 89 tests, including tests written *before* fixes to prove bugs were real.
- `app.py` — surfaced everything in the UI: sorted task table, per-pet filter, and live conflict warnings.
- Ran pytest after every change and the demo script to verify end to end.

**What did you have to verify or fix manually?**

The important part was deciding what to accept. The agent's review claimed my conflict checker missed long tasks spanning several later ones — I required that as a failing test before letting it change the code (it was real; the test failed, then passed after the fix). It also suggested replacing greedy scheduling with strict priority order, which I rejected and documented as a tradeoff instead. And one of its early demo runs revealed a bug the agent itself had introduced conceptually: a completed daily task's "tomorrow" copy showed up in today's plan, which we caught with a test and fixed by making the scheduler respect due dates.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
