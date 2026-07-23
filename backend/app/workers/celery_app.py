"""Celery application for Cliperry background jobs."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

DEFAULT_QUEUE = "cliperry"
DOWNLOAD_QUEUE = "downloads"


def create_celery_app() -> Celery:
    """Build and configure the Celery application."""
    app = Celery(
        "cliperry",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "app.workers.test_tasks",
            "app.workers.download_tasks",
        ],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
        task_default_queue=DEFAULT_QUEUE,
        task_routes={
            "cliperry.test_task": {"queue": DEFAULT_QUEUE},
            "cliperry.download": {"queue": DOWNLOAD_QUEUE},
        },
        broker_connection_retry_on_startup=True,
    )

    return app


celery_app = create_celery_app()
