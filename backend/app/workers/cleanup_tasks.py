"""Periodic maintenance tasks."""

from __future__ import annotations

import logging

from app.services.storage import StorageService
from app.workers.celery_app import celery_app

logger = logging.getLogger("cliperry.workers.cleanup")


@celery_app.task(name="cliperry.cleanup_storage")
def cleanup_storage() -> dict[str, int]:
    """Remove expired temporary download artifacts."""
    removed = StorageService().cleanup_expired()
    logger.info("cleanup_storage removed=%s", removed)
    return {"removed": removed}
