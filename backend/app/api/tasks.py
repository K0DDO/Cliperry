"""GET /api/tasks/{id} — task progress."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response

from app.auth.device import DEVICE_HEADER
from app.dependencies import DeviceDep, TaskServiceDep, rate_limit_tasks
from app.schemas.task import TaskStatusResponse

router = APIRouter(tags=["tasks"])


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Статус задачи скачивания",
    description="Возвращает status, progress, speed, eta для задачи устройства.",
    dependencies=[Depends(rate_limit_tasks)],
)
async def get_task_status(
    task_id: uuid.UUID,
    device: DeviceDep,
    service: TaskServiceDep,
    response: Response,
) -> TaskStatusResponse:
    """Return progress for a task owned by the calling device."""
    response.headers[DEVICE_HEADER] = device.device_id
    return await service.get_task(task_id, device)
