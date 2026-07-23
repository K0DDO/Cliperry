"""Celery smoke-test task unit checks (no broker required)."""

from app.workers import test_tasks


def test_smoke_task_returns_expected_string() -> None:
    assert test_tasks.test_task() == "Cliperry worker works"


def test_smoke_task_registered_name() -> None:
    assert test_tasks.test_task.name == "cliperry.test_task"
