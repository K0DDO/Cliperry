"""Celery download tasks — run platform parsers and track progress."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.sync_session import sync_session
from app.models.task import Task, TaskStatus
from app.parsers.exceptions import ParserError, ParserNotImplementedError, UnsupportedPlatformError
from app.parsers.factory import ParserFactory
from app.services.progress import format_eta, format_size_label, format_speed, update_task_progress
from app.services.storage import StorageService
from app.workers.celery_app import DOWNLOAD_QUEUE, celery_app

logger = logging.getLogger("cliperry.workers.download")


@celery_app.task(name="cliperry.download", bind=True, queue=DOWNLOAD_QUEUE)
def download_media(self, task_id: str) -> dict[str, Any]:
    """
    Execute a queued download:

    1. Load Task + Download from PostgreSQL
    2. Resolve parser via ParserFactory
    3. Download into temporary storage with progress hooks
    4. Persist status / signed token metadata
    """
    logger.info("download_start task_id=%s celery_id=%s", task_id, self.request.id)
    task_uuid = UUID(task_id)

    with sync_session() as session:
        task = session.execute(
            select(Task)
            .where(Task.id == task_uuid)
            .options(selectinload(Task.download))
        ).scalar_one_or_none()

        if task is None or task.download is None:
            logger.error("download_missing task_id=%s", task_id)
            return {"task_id": task_id, "status": "failed", "error": "task_not_found"}

        download = task.download
        url = download.url
        quality = download.quality or "1080p"

        update_task_progress(
            session,
            task,
            status=TaskStatus.PROCESSING,
            progress=1,
            celery_task_id=self.request.id,
        )

    last_publish = 0.0

    def progress_hook(event: dict[str, Any]) -> None:
        nonlocal last_publish
        status = event.get("status")
        if status not in {"downloading", "finished"}:
            return

        now = time.monotonic()
        if status == "downloading" and now - last_publish < 0.5:
            return
        last_publish = now

        total = event.get("total_bytes") or event.get("total_bytes_estimate") or 0
        downloaded = event.get("downloaded_bytes") or 0
        progress = (
            100
            if status == "finished"
            else (int(downloaded * 100 / total) if total else 0)
        )
        speed = format_speed(event.get("speed"))
        eta = format_eta(event.get("eta"))
        size = format_size_label(downloaded, total)

        with sync_session() as progress_session:
            current = progress_session.get(Task, task_uuid)
            if current is None:
                return
            update_task_progress(
                progress_session,
                current,
                status=TaskStatus.PROCESSING,
                progress=max(progress, 1),
                speed=speed,
                eta=eta,
                size=size,
            )

    try:
        factory = ParserFactory()
        parser = factory.get_parser(url)
        if hasattr(parser, "download_sync"):
            file_path = parser.download_sync(  # type: ignore[attr-defined]
                url,
                quality,
                artifact_id=task_id,
                progress_hook=progress_hook,
            )
        else:
            import asyncio

            file_path = asyncio.run(parser.download(url, quality))
    except (ParserError, ParserNotImplementedError, UnsupportedPlatformError) as exc:
        logger.warning("download_failed task_id=%s error=%s", task_id, exc)
        with sync_session() as session:
            task = session.get(Task, task_uuid)
            if task is not None:
                update_task_progress(
                    session,
                    task,
                    status=TaskStatus.FAILED,
                    error_message=str(exc),
                )
        return {"task_id": task_id, "status": "failed", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("download_unexpected task_id=%s", task_id)
        with sync_session() as session:
            task = session.get(Task, task_uuid)
            if task is not None:
                update_task_progress(
                    session,
                    task,
                    status=TaskStatus.FAILED,
                    error_message="Unexpected download error",
                )
        return {"task_id": task_id, "status": "failed", "error": str(exc)}

    storage = StorageService()
    token = storage.create_download_token(task_id)
    download_url = f"/api/files/{task_id}?token={token}"

    with sync_session() as session:
        task = session.execute(
            select(Task)
            .where(Task.id == task_uuid)
            .options(selectinload(Task.download))
        ).scalar_one_or_none()
        if task is None:
            return {"task_id": task_id, "status": "failed", "error": "task_missing_after_download"}

        update_task_progress(
            session,
            task,
            status=TaskStatus.COMPLETED,
            progress=100,
            speed=None,
            eta="0s",
            file_path=file_path,
            download_token=token,
            download_url=download_url,
        )

    logger.info("download_complete task_id=%s path=%s", task_id, file_path)
    return {
        "task_id": task_id,
        "status": "completed",
        "file_path": file_path,
        "download_url": download_url,
    }
