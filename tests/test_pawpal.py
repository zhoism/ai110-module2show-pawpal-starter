"""Quick smoke tests for the PawPal+ domain model (assignment step 3)."""

from pawpal_system import Pet, Priority, Species, Task


def test_mark_complete_changes_status():
    task = Task(id="t1", title="Morning walk", duration_minutes=30, priority=Priority.HIGH)
    assert task.completed is False  # starts incomplete
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species=Species.DOG)
    before = len(pet.tasks)
    pet.add_task(Task(id="t2", title="Feeding", duration_minutes=10))
    assert len(pet.tasks) == before + 1
