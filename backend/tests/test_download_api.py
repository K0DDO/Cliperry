"""Unit tests for download enqueue + task status (Celery mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.device import get_or_create_device
from app.config import get_settings
from app.dependencies import get_db, rate_limit_download
from app.main import create_app
from app.models.download import Download, DownloadStatus
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskStatusResponse


@pytest.fixture
def client():
    get_settings.cache_clear()
    device = MagicMock()
    device.device_id = "00000000-0000-0000-0000-000000000001"
    device.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    device.user_id = uuid.UUID("00000000-0000-0000-0000-000000000088")

    async def _device():
        return device

    async def _rate_limit():
        return None

    # Fake async session that collects added objects
    class FakeSession:
        def __init__(self):
            self.added = []

        def add(self, obj):
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.added.append(obj)

        async def flush(self):
            return None

        async def commit(self):
            return None

        async def rollback(self):
            return None

    fake_session = FakeSession()

    async def _db():
        yield fake_session

    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
        patch("app.workers.download_tasks.download_media.delay") as delay,
    ):
        celery_result = MagicMock()
        celery_result.id = "celery-test-id"
        delay.return_value = celery_result

        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device
        app.dependency_overrides[rate_limit_download] = _rate_limit
        app.dependency_overrides[get_db] = _db

        with TestClient(app) as test_client:
            yield test_client, fake_session, delay

        app.dependency_overrides.clear()


def test_download_enqueues_celery(client) -> None:
    test_client, fake_session, delay = client
    response = test_client.post(
        "/api/download",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "quality": "720p",
            "title": "Demo",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert "task_id" in body
    assert "download_id" in body
    delay.assert_called_once()
    assert any(isinstance(obj, Download) for obj in fake_session.added)
    assert any(isinstance(obj, Task) for obj in fake_session.added)


def test_task_status_schema() -> None:
    payload = TaskStatusResponse(
        task_id=uuid.uuid4(),
        status="processing",
        progress=75,
        speed="8.5MB/s",
        eta="20s",
    )
    data = payload.model_dump()
    assert data["status"] == "processing"
    assert data["progress"] == 75
    assert data["speed"] == "8.5MB/s"
    assert data["eta"] == "20s"


def test_progress_helpers() -> None:
    from app.services.progress import format_eta, format_speed, progress_channel

    assert format_speed(1024) == "1.0KB/s"
    assert format_eta(65) == "1m 5s"
    assert progress_channel("abc").endswith("abc")
