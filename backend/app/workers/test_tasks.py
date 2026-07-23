"""Smoke-test Celery tasks."""

from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="cliperry.test_task", bind=False)
def test_task() -> str:
    """
    Minimal task used to verify Redis + worker connectivity.

    Returns:
        Confirmation string when the worker executes successfully.
    """
    return "Cliperry worker works"
