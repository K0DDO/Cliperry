"""Tests for GET /api/history pagination."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.device import get_or_create_device
from app.config import get_settings
from app.dependencies import get_history_service, rate_limit_history
from app.main import create_app
from app.schemas.history import HistoryItem, HistoryResponse


@pytest.fixture
def history_client():
    get_settings.cache_clear()
    device = MagicMock()
    device.device_id = "00000000-0000-0000-0000-000000000001"
    device.id = uuid.UUID("00000000-0000-0000-0000-000000000099")

    async def _device():
        return device

    service = MagicMock()

    async def _history_service():
        return service

    async def _rate_limit():
        return None

    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device
        app.dependency_overrides[get_history_service] = _history_service
        app.dependency_overrides[rate_limit_history] = _rate_limit

        with TestClient(app) as test_client:
            yield test_client, service

        app.dependency_overrides.clear()


def test_history_endpoint_returns_page(history_client) -> None:
    test_client, service = history_client
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    service.list_downloads = AsyncMock(
        return_value=HistoryResponse(
            items=[
                HistoryItem(
                    id=uuid.uuid4(),
                    title="Demo video",
                    platform="youtube",
                    status="completed",
                    quality="720p",
                    created_at=now,
                )
            ],
            page=1,
            page_size=10,
            total=1,
            total_pages=1,
            has_prev=False,
            has_next=False,
        )
    )

    response = test_client.get("/api/history", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["items"][0]["title"] == "Demo video"
    assert body["items"][0]["platform"] == "youtube"
    assert body["items"][0]["status"] == "completed"
    service.list_downloads.assert_awaited_once()


def test_format_history_fields() -> None:
    from app.bot.texts import format_history

    text = format_history(
        [
            {
                "title": "Clip <1>",
                "platform": "youtube",
                "status": "completed",
                "created_at": "2026-07-23T12:00:00+00:00",
            }
        ],
        page=1,
        total_pages=2,
        total=15,
    )
    assert "Последние 10 загрузок" in text
    assert "стр. 1/2" in text
    assert "YouTube" in text
    assert "23.07.2026" in text
    assert "Готово" in text
    assert "Clip &lt;1&gt;" in text
