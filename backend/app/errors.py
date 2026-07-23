"""Structured API errors with human-readable messages."""

from __future__ import annotations

from typing import Any

from fastapi import status


class AppError(Exception):
    """
    Application error that maps cleanly to an HTTP JSON response.

    Example client payload:
    {
      "error": true,
      "code": "unsupported_platform",
      "message": "Платформа не поддерживается.",
      "request_id": "..."
    }
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": True,
            "code": self.code,
            "message": self.message,
            "request_id": request_id,
        }
        if self.details:
            payload["details"] = self.details
        return payload


# --- Analyze / URL domain errors -------------------------------------------


def invalid_url(message: str, **details: Any) -> AppError:
    return AppError(
        code="invalid_url",
        message=message,
        status_code=422,
        details=details or None,
    )


def blocked_platform() -> AppError:
    return AppError(
        code="blocked_platform",
        message="Эта площадка не поддерживается Cliperry по соображениям политики.",
        status_code=403,
    )


def unsupported_platform(url: str, supported: list[str]) -> AppError:
    platforms = ", ".join(supported) if supported else "пока нет доступных"
    return AppError(
        code="unsupported_platform",
        message=(
            "Не удалось определить платформу по ссылке. "
            f"Сейчас поддерживаются: {platforms}."
        ),
        status_code=422,
        details={"url": url, "supported_platforms": supported},
    )


def parser_not_ready(platform: str) -> AppError:
    return AppError(
        code="parser_not_ready",
        message=(
            f"Платформа «{platform}» уже распознана, "
            "но парсер ещё не готов. Попробуйте позже."
        ),
        status_code=501,
        details={"platform": platform},
    )


def analyze_failed(platform: str, reason: str | None = None) -> AppError:
    hint = " Проверьте ссылку и повторите попытку."
    # Keep yt-dlp internals out of client responses; only map known cases.
    safe_reason = None
    if reason and ("bot" in reason.lower() or "sign in" in reason.lower()):
        hint = (
            " YouTube временно требует авторизацию (cookies). "
            "Настройте YTDLP_COOKIES_FILE или YTDLP_COOKIES_FROM_BROWSER."
        )
        safe_reason = "auth_required"
    elif reason == "parser_error":
        safe_reason = "parser_error"
    elif reason == "unexpected error":
        safe_reason = "unexpected_error"

    details: dict = {"platform": platform}
    if safe_reason:
        details["reason"] = safe_reason
    return AppError(
        code="analyze_failed",
        message=f"Не удалось получить информацию о видео ({platform}).{hint}",
        status_code=502,
        details=details,
    )


def rate_limited(retry_after: int) -> AppError:
    return AppError(
        code="rate_limit_exceeded",
        message="Слишком много запросов. Подождите немного и попробуйте снова.",
        status_code=429,
        details={"retry_after": retry_after},
    )
