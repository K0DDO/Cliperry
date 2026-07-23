"""Worker health / smoke endpoints (debug / explicit opt-in only)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.admin.auth import AdminUserDep
from app.config import Settings, get_settings
from app.workers.test_tasks import test_task

router = APIRouter(prefix="/worker", tags=["worker"])


class WorkerTestResponse(BaseModel):
    """Result of enqueueing and awaiting the smoke-test task."""

    task_id: str
    status: str
    result: str | None = None


def _worker_test_enabled(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.enable_worker_test or settings.is_production:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Not found"},
        )
    return settings


@router.post("/test", response_model=WorkerTestResponse)
async def trigger_test_task(
    _admin: AdminUserDep,
    _settings: Settings = Depends(_worker_test_enabled),
    timeout: float = Query(default=10.0, ge=1.0, le=60.0),
) -> WorkerTestResponse:
    """
    Enqueue ``test_task`` and wait for the Celery worker result.

    Protected: admin auth required, disabled in production.
    """
    async_result = test_task.delay()

    try:
        result = await asyncio.to_thread(async_result.get, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={
                "code": "worker_unavailable",
                "message": "Celery worker did not return a result in time",
                "task_id": async_result.id,
            },
        ) from exc

    return WorkerTestResponse(
        task_id=async_result.id,
        status="SUCCESS",
        result=str(result),
    )
