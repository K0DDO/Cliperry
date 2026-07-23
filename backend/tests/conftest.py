"""Shared pytest fixtures and markers."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure predictable settings for unit tests before app imports settings cache.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("ADMIN_PASSWORD", "unit-test-admin-password")
os.environ.setdefault("ENABLE_WORKER_TEST", "true")
os.environ.setdefault("TRUST_PROXY_HEADERS", "false")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: fast isolated unit tests")
    config.addinivalue_line(
        "markers",
        "integration: requires Postgres/Redis (Docker test env)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark non-integration tests as unit by default."""
    for item in items:
        if "integration" not in item.keywords:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def device_mock() -> MagicMock:
    device = MagicMock()
    device.device_id = "00000000-0000-0000-0000-000000000001"
    device.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    device.user_id = uuid.UUID("00000000-0000-0000-0000-000000000088")
    return device


@pytest.fixture
def api_client(device_mock: MagicMock) -> Iterator[TestClient]:
    """FastAPI TestClient with device + rate-limit overrides."""
    from app.auth.device import get_or_create_device
    from app.config import get_settings
    from app.dependencies import (
        rate_limit_analyze,
        rate_limit_download,
        rate_limit_history,
        rate_limit_tasks,
    )
    from app.main import create_app

    get_settings.cache_clear()

    async def _device():
        return device_mock

    async def _noop_rate_limit():
        return None

    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        app.dependency_overrides[get_or_create_device] = _device
        app.dependency_overrides[rate_limit_analyze] = _noop_rate_limit
        app.dependency_overrides[rate_limit_download] = _noop_rate_limit
        app.dependency_overrides[rate_limit_history] = _noop_rate_limit
        app.dependency_overrides[rate_limit_tasks] = _noop_rate_limit
        with TestClient(app) as client:
            yield client
        app.dependency_overrides.clear()
        get_settings.cache_clear()
