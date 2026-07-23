"""POST /api/download — enqueue a download task."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.device import DEVICE_HEADER
from app.dependencies import DeviceDep, DownloadServiceDep, rate_limit_download
from app.schemas.download import DownloadCreateResponse, DownloadRequest

router = APIRouter(tags=["download"])


@router.post(
    "/download",
    response_model=DownloadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать задачу скачивания",
    description=(
        "Создаёт записи Download + Task и ставит задачу в Celery очередь `downloads`."
    ),
    responses={
        201: {"description": "Задача поставлена в очередь"},
        422: {"description": "Невалидный URL / платформа"},
        429: {"description": "Rate limit"},
        503: {"description": "Очередь Celery недоступна"},
    },
    dependencies=[Depends(rate_limit_download)],
)
async def create_download(
    payload: DownloadRequest,
    device: DeviceDep,
    service: DownloadServiceDep,
    response: Response,
) -> DownloadCreateResponse:
    """Create Download + Task and enqueue Celery worker."""
    response.headers[DEVICE_HEADER] = device.device_id
    return await service.create_download(device, payload)
