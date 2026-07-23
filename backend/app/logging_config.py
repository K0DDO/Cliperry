"""Logging configuration for the Cliperry backend."""

from __future__ import annotations

import logging
import sys

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Configure root logging once at application startup.

    Uses a structured, parseable format suitable for container log collectors.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    if root.handlers:
        # Avoid duplicate handlers under uvicorn reload / repeated create_app()
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
