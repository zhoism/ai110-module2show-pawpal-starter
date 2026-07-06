import streamlit as st

from pawpal_system import (
    Constraints,
    Owner,
    Pet,
    Preferences,
    Priority,
    Scheduler,
    Species,
    Task,
    fmt,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# --- Session state: the Owner lives in st.session_state so it survives reruns ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="", preferences=Preferences())
if "task_seq" not in st.session_state:
    st.session_state.task_seq = 0

owner: Owner = st.session_state.owner

# --- Owner info + day constraints -------------------------------------------
st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name or "Jordan")

with st.sidebar:
    st.header("Day constraints")
    day_start = st.time_input("Day starts", value=None)
    day_end = st.time_input("Day ends", value=None)
    available = st.number_input(
        "Available minutes", min_value=0, max_value=24 * 60, value=150, step=15
    )
    if day_start:
        owner.preferences.day_start = day_start.hour * 60 + day_start.minute
    if day_end:
        owner.preferences.day_end = day_end.hour * 60 + day_end.minute
    owner.preferences.available_minutes = int(available)

# --- Add a pet ---------------------------------------------------------------
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="")
    with col2:
        species = st.selectbox("Species", [s.value for s in Species])
    if st.form_submit_button("Add pet"):
        if pet_name.strip():
            owner.add_pet(Pet(name=pet_name.strip(), species=Species(species)))
            st.success(f"Added {pet_name.strip()} ({species}).")
        else:
            st.error("Give the pet a name first.")

if not owner.pets:
    st.info("No pets yet. Add one above.")
else:
    st.write(
        ", ".join(
            f"**{p.name}** ({p.species.value}, {len(p.tasks)} tasks)" for p in owner.pets
        )
    )

# --- Add a task to a pet -------------------------------------------------------
st.subheader("Tasks")
if owner.pets:
    with st.form("add_task", clear_on_submit=True):
        pet_choice = st.selectbox("For pet", [p.name for p in owner.pets])
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with col3:
            priority = st.selectbox("Priority", [p.label for p in Priority], index=2)
        fixed_time = st.time_input("Fixed time (optional)", value=None)
        if st.form_submit_button("Add task"):
            pet = next(p for p in owner.pets if p.name == pet_choice)
            st.session_state.task_seq += 1
            task = Task(
                id=f"t{st.session_state.task_seq}",
                title=task_title,
                duration_minutes=int(duration),
                priority=Priority.from_label(priority),
                preferred_time=(
                    fixed_time.hour * 60 + fixed_time.minute if fixed_time else None
                ),
                is_fixed=fixed_time is not None,
            )
            owner.add_task(pet, task)
            st.success(f"Added '{task_title}' for {pet.name}.")

    if owner.all_tasks():
        # filter by pet, then show the list sorted by time (untimed tasks last)
        pet_filter = st.selectbox("Show tasks for", ["All pets"] + [p.name for p in owner.pets])
        visible = (
            owner.all_tasks() if pet_filter == "All pets" else owner.tasks_for(pet_filter)
        )
        pet_of = {t.id: p.name for p in owner.pets for t in p.tasks}
        st.table(
            [
                {
                    "time": fmt(t.preferred_time) if t.preferred_time is not None else "—",
                    "pet": pet_of[t.id],
                    "task": t.title,
                    "minutes": t.duration_minutes,
                    "priority": t.priority.label,
                    "fixed": "yes" if t.is_fixed else "",
                }
                for t in Scheduler().sort_by_time(visible)
            ]
        )

        # live conflict check: warn the owner as soon as two fixed times collide
        conflicts = Scheduler().detect_preferred_time_conflicts(owner.all_tasks())
        for conflict in conflicts:
            st.warning(f"⚠️ Time conflict: {conflict}")
        if not conflicts:
            st.success("No time conflicts in your task list.")
else:
    st.caption("Add a pet first, then attach tasks to it.")

st.divider()

# --- Generate the schedule -----------------------------------------------------
st.subheader("Build Schedule")
if st.button("Generate schedule"):
    tasks = owner.all_tasks()
    if not tasks:
        st.warning("Add at least one task first.")
    else:
        constraints = Constraints.from_preferences(owner.preferences)
        plan = Scheduler().generate(tasks, constraints)
        if plan.items:
            st.markdown(f"### Daily plan for {owner.name}'s pets")
            st.table(
                [
                    {
                        "time": f"{item['start']}–{item['end']}",
                        "task": item["title"],
                        "minutes": item["duration_minutes"],
                        "priority": item["priority"],
                    }
                    for item in plan.to_dict()["items"]
                ]
            )
        # conflicts the scheduler had to resolve — shown per conflict so the owner
        # can see exactly which two tasks collided and reschedule one of them
        for warning in plan.warnings:
            st.warning(f"⚠️ {warning} — the later task was moved; pick a new time if that doesn't work.")
        if plan.items and not plan.warnings:
            st.success(f"Scheduled {len(plan.items)} tasks with no conflicts.")
        if plan.skipped:
            st.warning(
                "Skipped: "
                + "; ".join(
                    f"{t.title} ({plan.skipped_reasons.get(t.id, '')})"
                    for t in plan.skipped
                )
            )
        with st.expander("Why this plan?"):
            st.text(plan.explain())
