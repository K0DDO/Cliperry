"""FastAPI dependency injection wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device import get_or_create_device
from app.auth.rate_limit import check_rate_limit
from app.config import Settings, get_settings
from app.database.redis import get_redis
from app.database.session import get_db
from app.models.device import Device
from app.services.analyzer import AnalyzerService
from app.services.download_service import DownloadService
from app.services.history_service import HistoryService
from app.services.storage import StorageService
from app.services.task_service import TaskService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
DeviceDep = Annotated[Device, Depends(get_or_create_device)]


async def get_analyzer() -> AnalyzerService:
    """Provide AnalyzerService."""
    return AnalyzerService()


async def get_download_service(session: DbDep) -> DownloadService:
    """Provide DownloadService bound to the request session."""
    return DownloadService(session)


async def get_task_service(session: DbDep) -> TaskService:
    """Provide TaskService bound to the request session."""
    return TaskService(session)


async def get_storage(settings: SettingsDep) -> StorageService:
    """Provide StorageService."""
    return StorageService(settings)


async def get_history_service(session: DbDep) -> HistoryService:
    """Provide HistoryService bound to the request session."""
    return HistoryService(session)


async def rate_limit_analyze(
    request: Request,
    redis: RedisDep,
    settings: SettingsDep,
    _device: DeviceDep,
) -> None:
    """Rate-limit analyze endpoint (runs after device resolution)."""
    await check_rate_limit(
        redis,
        settings,
        request,
        action="analyze",
        limit=settings.rate_limit_analyze,
    )


async def rate_limit_download(
    request: Request,
    redis: RedisDep,
    settings: SettingsDep,
    _device: DeviceDep,
) -> None:
    """Rate-limit download endpoint (runs after device resolution)."""
    await check_rate_limit(
        redis,
        settings,
        request,
        action="download",
        limit=settings.rate_limit_download,
    )


async def rate_limit_history(
    request: Request,
    redis: RedisDep,
    settings: SettingsDep,
    _device: DeviceDep,
) -> None:
    """Rate-limit history endpoint."""
    await check_rate_limit(
        redis,
        settings,
        request,
        action="history",
        limit=settings.rate_limit_history,
    )


async def rate_limit_tasks(
    request: Request,
    redis: RedisDep,
    settings: SettingsDep,
    _device: DeviceDep,
) -> None:
    """Rate-limit task status endpoint."""
    await check_rate_limit(
        redis,
        settings,
        request,
        action="tasks",
        limit=settings.rate_limit_tasks,
    )


AnalyzerDep = Annotated[AnalyzerService, Depends(get_analyzer)]
DownloadServiceDep = Annotated[DownloadService, Depends(get_download_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
HistoryServiceDep = Annotated[HistoryService, Depends(get_history_service)]
StorageDep = Annotated[StorageService, Depends(get_storage)]
