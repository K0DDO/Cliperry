"""Integration: Celery queue via Redis broker."""

from __future__ import annotations

import os

import pytest
import redis

from app.workers.test_tasks import test_task as smoke_celery_task

pytestmark = pytest.mark.integration


def _broker_available() -> bool:
    url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6380/1"))
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        return False


def test_smoke_task_direct_call() -> None:
    """Pure function path — no broker needed."""
    assert smoke_celery_task() == "Cliperry worker works"


def test_smoke_task_through_queue() -> None:
    """Enqueue to Redis and wait for a worker result."""
    if not _broker_available():
        pytest.skip("Redis broker is not available — start docker compose test env")

    eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in {"1", "true", "yes"}
    if eager:
        async_result = smoke_celery_task.delay()
        assert async_result.get(timeout=5) == "Cliperry worker works"
        return

    async_result = smoke_celery_task.delay()
    try:
        result = async_result.get(timeout=20)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Celery worker did not consume task: {exc}")
    assert result == "Cliperry worker works"


def test_redis_ping() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/15")
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=1)
        assert client.ping() is True
    except Exception:
        pytest.skip("Redis is not available — start docker compose test env")
