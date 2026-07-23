"""Admin auth unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.admin.auth import (
    COOKIE_NAME,
    credentials_valid,
    issue_session_token,
    verify_session_token,
)
from app.config import Settings, get_settings
from app.main import create_app


def test_credentials_and_token_roundtrip() -> None:
    settings = Settings(
        admin_username="admin",
        admin_password="secret-pass",
        secret_key="test-secret-key-123456",
    )
    assert credentials_valid("admin", "secret-pass", settings)
    assert not credentials_valid("admin", "wrong", settings)
    token = issue_session_token("admin", settings)
    assert verify_session_token(token, settings) == "admin"
    assert verify_session_token("bad", settings) is None


@pytest.fixture
def admin_client():
    get_settings.cache_clear()
    with (
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
        patch.dict(
            "os.environ",
            {
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD": "secret-pass",
                "SECRET_KEY": "test-secret-key-123456",
            },
            clear=False,
        ),
    ):
        get_settings.cache_clear()
        app = create_app(
            Settings(
                admin_username="admin",
                admin_password="secret-pass",
                secret_key="test-secret-key-123456",
                app_env="test",
                debug=True,
            )
        )
        with TestClient(app) as client:
            yield client
        get_settings.cache_clear()


def test_admin_api_requires_auth(admin_client: TestClient) -> None:
    response = admin_client.get("/admin/api/dashboard")
    assert response.status_code == 401


def test_admin_login_page_ok(admin_client: TestClient) -> None:
    response = admin_client.get("/admin/login")
    assert response.status_code == 200
    assert "Admin access" in response.text


def test_admin_login_sets_cookie(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass", "next": "/admin"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert COOKIE_NAME in response.cookies
