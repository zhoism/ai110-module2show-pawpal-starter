# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_scheduler.py

# Run with coverage
pytest --cov
```

## Architecture

This is a starter project — the backend logic does not exist yet and must be built. The intended architecture is:

- **`app.py`** — Streamlit UI shell. Currently collects owner name, pet name, species, and a task list (title, duration, priority) via `st.session_state`. The "Generate schedule" button is a stub that must be wired to the scheduler once implemented.
- **Backend module (to be created)** — Python classes representing `Owner`, `Pet`, and `Task`, plus a `Scheduler` that takes a list of tasks and constraints and returns an ordered daily plan. The README suggests keeping this separate from `app.py` so it can be tested independently.
- **`diagrams/uml.mmd`** — Mermaid class diagram; update this to reflect the actual classes once implemented.
- **`tests/` (to be created)** — pytest test files targeting the scheduling logic, not the Streamlit UI.

The key design constraint: scheduling logic must live outside `app.py` so it can be unit-tested. `app.py` should only import and call the scheduler, then render results.
