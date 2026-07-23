"""POST /api/analyze — inspect a media URL."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.device import DEVICE_HEADER
from app.dependencies import AnalyzerDep, DeviceDep, rate_limit_analyze
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Анализ ссылки на видео",
    description=(
        "Проверяет URL, определяет платформу через ParserFactory, "
        "запускает соответствующий parser и возвращает метаданные + форматы. "
        "Файлы на сервер не сохраняются."
    ),
    responses={
        200: {"description": "Метаданные видео / плейлиста"},
        403: {"description": "Площадка запрещена политикой"},
        422: {"description": "Невалидный URL или неизвестная платформа"},
        429: {"description": "Превышен rate limit"},
        501: {"description": "Парсер платформы ещё не реализован"},
        502: {"description": "Парсер не смог получить данные"},
    },
    dependencies=[Depends(rate_limit_analyze)],
)
async def analyze_url(
    payload: AnalyzeRequest,
    device: DeviceDep,
    analyzer: AnalyzerDep,
    response: Response,
) -> AnalyzeResponse:
    """
    Analyze a media URL.

    Flow:
    1. validate URL
    2. detect platform
    3. select parser
    4. return title / thumbnail / formats / ...
    """
    response.headers[DEVICE_HEADER] = device.device_id
    return await analyzer.analyze(payload.url)
