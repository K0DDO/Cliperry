"""Domain services.

Import concrete modules directly (``app.services.analyzer``, etc.)
to avoid circular imports with the parser layer.
"""

from __future__ import annotations

__all__ = [
    "AnalyzerService",
    "DownloadService",
    "TaskService",
    "StorageService",
    "validate_media_url",
]


def __getattr__(name: str):
    if name == "AnalyzerService":
        from app.services.analyzer import AnalyzerService

        return AnalyzerService
    if name == "DownloadService":
        from app.services.download_service import DownloadService

        return DownloadService
    if name == "TaskService":
        from app.services.task_service import TaskService

        return TaskService
    if name == "StorageService":
        from app.services.storage import StorageService

        return StorageService
    if name == "validate_media_url":
        from app.services.url_validator import validate_media_url

        return validate_media_url
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
