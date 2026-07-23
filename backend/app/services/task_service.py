"""Task progress read service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import AppError
from app.models.device import Device
from app.models.download import Download
from app.models.task import Task
from app.schemas.task import TaskStatusResponse


class TaskService:
    """Read task progress from PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_task(
        self,
        task_id: uuid.UUID,
        device: Device,
    ) -> TaskStatusResponse:
        """Return progress for a task owned by the calling device."""
        result = await self.session.execute(
            select(Task)
            .join(Download, Task.download_id == Download.id)
            .where(Task.id == task_id, Download.device_id == device.id)
            .options(selectinload(Task.download))
        )
        task = result.scalar_one_or_none()

        if task is None:
            raise AppError(
                code="task_not_found",
                message="Задача не найдена или принадлежит другому устройству.",
                status_code=404,
                details={"task_id": str(task_id)},
            )

        download = task.download
        return TaskStatusResponse(
            task_id=task.id,
            status=task.status.value,
            progress=task.progress,
            speed=task.speed,
            eta=task.eta,
            size=task.size,
            error_message=task.error_message,
            download_url=task.download_url,
            title=download.title if download else None,
            platform=download.platform if download else None,
            quality=download.quality if download else None,
        )
