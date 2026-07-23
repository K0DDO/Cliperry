"""API tests for POST /api/analyze."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.device import get_or_create_device
from app.config import get_settings
from app.dependencies import rate_limit_analyze
from app.main import create_app
from app.parsers.base import MediaFormat, MediaInfo
from app.parsers.youtube import YoutubeParser


@pytest.fixture
def client():
    get_settings.cache_clear()

    device = MagicMock()
    device.device_id = "00000000-0000-0000-0000-000000000001"
    device.id = device.device_id
    device.user_id = None

    async def _device_override():
        return device

    async def _rate_limit_override():
        return None

    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device_override
        app.dependency_overrides[rate_limit_analyze] = _rate_limit_override
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()


def test_analyze_validation_missing_url(client: TestClient) -> None:
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] is True
    assert body["code"] == "validation_error"
    assert "message" in body


def test_analyze_invalid_scheme(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"url": "ftp://example.com/x"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_url"
    assert body["error"] is True
    assert "message" in body


def test_analyze_unsupported_platform(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"url": "https://example.com/video"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "unsupported_platform"
    assert "платформ" in body["message"].lower()


def test_analyze_success(client: TestClient) -> None:
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
        response = client.post(
            "/api/analyze",
            json={"url": "https://www.youtube.com/watch?v=abc12345678"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == "youtube"
    assert body["title"] == "Test Video"
    assert body["thumbnail"] is not None
    assert [f["quality"] for f in body["formats"]] == ["1080p", "720p", "480p", "audio"]
    assert "X-Device-Id" in response.headers
