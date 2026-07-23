"""Tests for FastAPI application foundation."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_health_returns_ok() -> None:
    """GET /health must return exactly {\"status\": \"ok\"}."""
    get_settings.cache_clear()

    with (
        patch("app.main.init_redis", new_callable=AsyncMock) as init_redis,
        patch("app.main.close_redis", new_callable=AsyncMock) as close_redis,
    ):
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/health")

        init_redis.assert_awaited()
        close_redis.assert_awaited()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-Id" in response.headers
