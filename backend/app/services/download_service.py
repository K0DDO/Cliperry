"""Download task creation service."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError, unsupported_platform
from app.models.device import Device
from app.models.download import Download, DownloadStatus
from app.models.task import Task, TaskStatus
from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.factory import get_parser_factory
from app.schemas.download import DownloadCreateResponse, DownloadRequest
from app.services.url_validator import validate_media_url
from app.workers.download_tasks import download_media

logger = logging.getLogger("cliperry.download_service")


class DownloadService:
    """Creates Download + Task records and enqueues Celery work."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_download(
        self,
        device: Device,
        payload: DownloadRequest,
    ) -> DownloadCreateResponse:
        """Persist a queued download, enqueue Celery, return task id."""
        cleaned = validate_media_url(str(payload.url))

        try:
            parser = get_parser_factory().get_parser(cleaned)
            platform = payload.platform or parser.platform
        except UnsupportedPlatformError as exc:
            raise unsupported_platform(exc.url, exc.supported) from exc

        download = Download(
            url=cleaned,
            platform=platform,
            title=payload.title,
            quality=payload.quality,
            status=DownloadStatus.QUEUED,
            user_id=device.user_id,
            device_id=device.id,
        )
        self.session.add(download)
        await self.session.flush()

        task = Task(
            download_id=download.id,
            status=TaskStatus.QUEUED,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()

        try:
            async_result = await asyncio.to_thread(download_media.delay, str(task.id))
            task.celery_task_id = async_result.id
            await self.session.flush()
        except Exception as exc:  # noqa: BLE001
            logger.exception("celery_enqueue_failed task_id=%s", task.id)
            task.status = TaskStatus.FAILED
            task.error_message = "Не удалось поставить задачу в очередь"
            download.status = DownloadStatus.FAILED
            raise AppError(
                code="queue_unavailable",
                message="Очередь загрузок временно недоступна. Попробуйте позже.",
                status_code=503,
                details={"task_id": str(task.id), "error": str(exc)},
            ) from exc

        logger.info(
            "download_queued task_id=%s celery_id=%s platform=%s quality=%s",
            task.id,
            task.celery_task_id,
            platform,
            payload.quality,
        )

        return DownloadCreateResponse(
            task_id=task.id,
            status=task.status.value,
            download_id=download.id,
        )
