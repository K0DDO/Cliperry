"""Smoke tests for URL validation."""

import pytest

from app.errors import AppError
from app.services.url_validator import is_blocked_domain, validate_media_url


def test_blocks_adult_domains() -> None:
    assert is_blocked_domain("https://www.pornhub.com/view_video.php?viewkey=x")


def test_allows_youtube() -> None:
    url = validate_media_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert "youtube.com" in url


def test_rejects_bad_scheme() -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url("ftp://example.com/video")
    assert exc.value.status_code == 422
    assert exc.value.code == "invalid_url"
    assert "http" in exc.value.message.lower() or "https" in exc.value.message


def test_blocked_platform_message() -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url("https://www.pornhub.com/video")
    assert exc.value.code == "blocked_platform"
    assert exc.value.status_code == 403
