"""Cliperry FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.admin import router as admin_router
from app.api.health import router as health_router
from app.api.router import api_router
from app.api.ws import router as ws_router
from app.config import Settings, get_settings
from app.database.redis import close_redis, init_redis
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.security.env import cors_extension_origin_regex, validate_settings
from app.security.headers import SecurityHeadersMiddleware

logger = logging.getLogger("cliperry")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup and graceful shutdown."""
    settings = get_settings()
    validate_settings(settings)
    logger.info(
        "starting service=%s env=%s version=%s",
        settings.app_name,
        settings.app_env,
        settings.api_version,
    )
    await init_redis()
    logger.info("redis connected")
    try:
        yield
    finally:
        await close_redis()
        logger.info("shutdown complete")


def _register_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach middleware in reverse execution order (last added = first run)."""
    extension_regex = cors_extension_origin_regex(settings)
    cors_kwargs: dict = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Accept",
            "Content-Type",
            "X-Device-Id",
            "X-Client-Type",
            "X-Request-Id",
            "Authorization",
        ],
        "expose_headers": ["X-Device-Id", "X-Request-Id"],
        "max_age": 600,
    }
    if extension_regex:
        cors_kwargs["allow_origin_regex"] = extension_regex

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    if settings.trusted_host_list != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_host_list,
        )

    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(RequestLoggingMiddleware)


def _register_routes(app: FastAPI, settings: Settings) -> None:
    """Mount public, API, admin, and websocket routers."""
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(admin_router)
    app.include_router(ws_router)


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Application factory.

    Prefer ``create_app()`` in tests so settings can be injected / cache cleared.
    """
    settings = settings or get_settings()
    configure_logging(settings)
    # Validate early for production fail-fast (also runs again in lifespan).
    validate_settings(settings, strict=settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        description="Cliperry — universal video downloader API",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    _register_middleware(app, settings)
    register_exception_handlers(app)
    _register_routes(app, settings)

    return app


app = create_app()
