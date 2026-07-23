"""Unit: FastAPI analyze / download / history / health endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.parsers.base import MediaFormat, MediaInfo
from app.parsers.youtube import YoutubeParser
from app.schemas.history import HistoryItem, HistoryResponse

pytestmark = [pytest.mark.unit, pytest.mark.api]


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_validation_error(api_client: TestClient) -> None:
    response = api_client.post("/api/analyze", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_analyze_success(api_client: TestClient) -> None:
    media = MediaInfo(
        title="Test Video",
        platform="youtube",
        url="https://www.youtube.com/watch?v=abc12345678",
        thumbnail="https://i.ytimg.com/vi/abc/hqdefault.jpg",
        author="Author",
        duration="1:00",
        formats=[
            MediaFormat(quality="1080p", format="mp4"),
            MediaFormat(quality="720p", format="mp4"),
            MediaFormat(quality="480p", format="mp4"),
            MediaFormat(quality="audio", format="m4a", has_video=False),
        ],
    )
    with patch.object(YoutubeParser, "analyze", new=AsyncMock(return_value=media)):
        response = api_client.post(
            "/api/analyze",
            json={"url": "https://www.youtube.com/watch?v=abc12345678"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == "youtube"
    assert body["title"] == "Test Video"
    assert "X-Device-Id" in response.headers


def test_download_enqueues(api_client: TestClient, device_mock: MagicMock) -> None:
    from app.dependencies import get_db
    from app.main import create_app
    from app.config import get_settings
    from app.auth.device import get_or_create_device
    from app.dependencies import rate_limit_download

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, obj: object) -> None:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()  # type: ignore[attr-defined]
            self.added.append(obj)

        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    fake = FakeSession()

    async def _db():
        yield fake

    async def _device():
        return device_mock

    async def _rl():
        return None

    get_settings.cache_clear()
    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
        patch("app.workers.download_tasks.download_media.delay") as delay,
    ):
        delay.return_value = MagicMock(id="celery-id")
        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device
        app.dependency_overrides[rate_limit_download] = _rl
        app.dependency_overrides[get_db] = _db
        with TestClient(app) as client:
            response = client.post(
                "/api/download",
                json={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "quality": "720p",
                    "title": "Demo",
                },
            )
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert "task_id" in body
    delay.assert_called_once()


def test_history_endpoint(api_client: TestClient) -> None:
    from app.dependencies import get_history_service
    from app.main import create_app
    from app.config import get_settings
    from app.auth.device import get_or_create_device
    from app.dependencies import rate_limit_history

    service = MagicMock()
    now = HistoryItem(
        id=uuid4(),
        title="Clip",
        platform="youtube",
        status="completed",
        quality="720p",
        created_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
    )
    service.list_downloads = AsyncMock(
        return_value=HistoryResponse(
            items=[now],
            page=1,
            page_size=10,
            total=1,
            total_pages=1,
            has_prev=False,
            has_next=False,
        )
    )

    async def _svc():
        return service

    async def _device():
        device = MagicMock()
        device.device_id = "00000000-0000-0000-0000-000000000001"
        return device

    async def _rl():
        return None

    get_settings.cache_clear()
    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device
        app.dependency_overrides[get_history_service] = _svc
        app.dependency_overrides[rate_limit_history] = _rl
        with TestClient(app) as client:
            response = client.get("/api/history")
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Clip"
