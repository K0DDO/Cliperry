"""Global exception handlers — consistent JSON error envelope."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError

logger = logging.getLogger("cliperry.errors")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _friendly_validation_message(errors: list[dict[str, Any]]) -> str:
    """Turn Pydantic errors into a short Russian message."""
    if not errors:
        return "Некорректные данные запроса."

    first = errors[0]
    loc = first.get("loc") or ()
    field = str(loc[-1]) if loc else "поле"
    err_type = first.get("type", "")

    if field == "url" or "url" in {str(x) for x in loc}:
        if err_type in {"missing", "value_error.missing"}:
            return "Укажите поле url со ссылкой на видео."
        return "Проверьте поле url — нужна корректная ссылка на видео."

    if err_type in {"missing", "value_error.missing"}:
        return f"Отсутствует обязательное поле: {field}."

    msg = first.get("msg")
    if isinstance(msg, str) and msg:
        # Pydantic often prefixes with "Value error, "
        return msg.removeprefix("Value error, ").strip()

    return "Некорректные данные запроса."


def register_exception_handlers(app: FastAPI) -> None:
    """Register AppError, HTTP, validation, and unhandled handlers."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        headers = None
        if exc.code == "rate_limit_exceeded":
            retry = exc.details.get("retry_after")
            if retry is not None:
                headers = {"Retry-After": str(retry)}
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(request_id=_request_id(request)),
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        # Normalize legacy HTTPException(detail=dict|str) into the AppError shape
        code = "http_error"
        message: str
        details: dict[str, Any] | None = None

        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code") or code)
            message = str(
                exc.detail.get("message")
                or exc.detail.get("detail")
                or "Произошла ошибка запроса."
            )
            details = {
                k: v
                for k, v in exc.detail.items()
                if k not in {"code", "message", "detail"}
            } or None
        else:
            message = str(exc.detail)

        body: dict[str, Any] = {
            "error": True,
            "code": code,
            "message": message,
            "request_id": _request_id(request),
        }
        if details:
            body["details"] = details

        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        from app.config import get_settings

        errors = exc.errors()
        content: dict[str, Any] = {
            "error": True,
            "code": "validation_error",
            "message": _friendly_validation_message(errors),
            "request_id": _request_id(request),
        }
        # Avoid leaking internal schema details in production.
        if get_settings().debug or not get_settings().is_production:
            content["details"] = {"errors": errors}
        return JSONResponse(status_code=422, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "unhandled_error path=%s request_id=%s",
            request.url.path,
            _request_id(request),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "internal_error",
                "message": "Внутренняя ошибка сервера. Мы уже разбираемся.",
                "request_id": _request_id(request),
            },
        )
