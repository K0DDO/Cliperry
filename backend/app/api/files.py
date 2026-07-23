"""Temporary file delivery with HMAC-signed tokens."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import DbDep
from app.errors import AppError
from app.models.task import Task, TaskStatus
from app.services.storage import StorageService

logger = logging.getLogger("cliperry.api.files")

router = APIRouter(tags=["files"])


@router.get(
    "/files/{task_id}",
    summary="Download completed file",
    response_class=FileResponse,
)
async def download_file(
    task_id: UUID,
    session: DbDep,
    token: str = Query(..., min_length=10),
) -> FileResponse:
    """
    Stream a completed download artifact.

    Requires a valid HMAC ``token`` from the completed task payload.
    """
    storage = StorageService()
    tid = str(task_id)
    if not storage.verify_download_token(tid, token):
        raise AppError(
            code="invalid_download_token",
            message="Invalid or expired download token",
            status_code=403,
        )

    task = (
        await session.execute(
            select(Task).where(Task.id == task_id).options(selectinload(Task.download))
        )
    ).scalar_one_or_none()

    if task is None:
        raise AppError(code="task_not_found", message="Task not found", status_code=404)

    if task.status != TaskStatus.COMPLETED:
        raise AppError(
            code="file_not_ready",
            message="File is not ready yet",
            status_code=409,
        )

    # Prefer DB path; fall back to scanning the task temp directory.
    path: Path | None = None
    if task.file_path:
        candidate = Path(task.file_path)
        if candidate.is_file():
            path = candidate

    if path is None:
        task_dir = storage.temp_root / tid
        if task_dir.is_dir():
            files = [
                p
                for p in task_dir.iterdir()
                if p.is_file() and p.name != StorageService.META_NAME
            ]
            if files:
                path = max(files, key=lambda p: p.stat().st_size)

    if path is None or not path.is_file():
        raise AppError(code="file_gone", message="File expired or missing", status_code=410)

    # Prevent path traversal outside temp root
    try:
        path.resolve().relative_to(storage.temp_root.resolve())
    except ValueError:
        logger.error("file_path_outside_temp task_id=%s path=%s", tid, path)
        raise AppError(code="file_gone", message="File expired or missing", status_code=410)

    filename = path.name
    if task.download and task.download.title:
        safe = "".join(c for c in task.download.title if c.isalnum() or c in " ._-" ).strip()
        if safe:
            filename = f"{safe[:80]}{path.suffix}"

    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )
