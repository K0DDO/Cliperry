"""Security hardening unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.errors import AppError
from app.main import create_app
from app.security.env import InsecureConfigurationError, validate_settings
from app.services.url_validator import is_unsafe_host, validate_media_url


def test_rejects_private_and_metadata_hosts() -> None:
    assert is_unsafe_host("127.0.0.1")
    assert is_unsafe_host("10.0.0.5")
    assert is_unsafe_host("192.168.1.1")
    assert is_unsafe_host("169.254.169.254")
    assert is_unsafe_host("localhost")
    assert not is_unsafe_host("youtube.com")


def test_validate_media_url_blocks_ssrf_targets() -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url("http://127.0.0.1/video.mp4")
    assert exc.value.code == "invalid_url"

    with pytest.raises(AppError):
        validate_media_url("https://user:pass@youtube.com/watch?v=1")


def test_production_rejects_insecure_defaults() -> None:
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="change-me-in-production",
        admin_password="change-me",
        trusted_hosts="*",
        enable_worker_test=True,
    )
    with pytest.raises(InsecureConfigurationError):
        validate_settings(settings, strict=True)


def test_security_headers_present() -> None:
    get_settings.cache_clear()
    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app(
            Settings(
                app_env="test",
                debug=True,
                secret_key="unit-test-secret-key-32chars-min!!",
                admin_password="unit-test-admin-pass",
            )
        )
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"
            assert response.headers.get("Referrer-Policy") == "no-referrer"
        get_settings.cache_clear()


def test_worker_test_requires_auth() -> None:
    get_settings.cache_clear()
    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app(
            Settings(
                app_env="test",
                debug=True,
                secret_key="unit-test-secret-key-32chars-min!!",
                admin_password="unit-test-admin-pass",
                enable_worker_test=True,
            )
        )
        with TestClient(app) as client:
            response = client.post("/api/worker/test")
            assert response.status_code == 401
        get_settings.cache_clear()
