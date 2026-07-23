"""GET /api/history — paginated download history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.auth.device import DEVICE_HEADER
from app.dependencies import DeviceDep, HistoryServiceDep, rate_limit_history
from app.schemas.history import HistoryResponse

router = APIRouter(tags=["history"])


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="История загрузок",
    description="Последние загрузки устройства с пагинацией (по умолчанию 10 на страницу).",
    dependencies=[Depends(rate_limit_history)],
)
async def get_history(
    device: DeviceDep,
    service: HistoryServiceDep,
    response: Response,
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=10, ge=1, le=50, description="Размер страницы"),
) -> HistoryResponse:
    response.headers[DEVICE_HEADER] = device.device_id
    return await service.list_downloads(device, page=page, page_size=page_size)
