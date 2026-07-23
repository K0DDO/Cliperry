"""Task progress updates (DB + Redis pub/sub for WebSocket clients)."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.download import Download, DownloadStatus
from app.models.task import Task, TaskStatus

logger = logging.getLogger("cliperry.progress")

PROGRESS_CHANNEL_PREFIX = "cliperry:task:"
_sync_redis_pool: redis.ConnectionPool | None = None


def progress_channel(task_id: str | UUID) -> str:
    return f"{PROGRESS_CHANNEL_PREFIX}{task_id}"


def _sync_redis() -> redis.Redis:
    global _sync_redis_pool
    settings = get_settings()
    if _sync_redis_pool is None:
        _sync_redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=32,
        )
    return redis.Redis(connection_pool=_sync_redis_pool)


def publish_progress(task_id: str | UUID, payload: dict[str, Any]) -> None:
    """Publish a progress event for WebSocket subscribers."""
    try:
        client = _sync_redis()
        client.publish(progress_channel(task_id), json.dumps(payload, default=str))
    except Exception:  # noqa: BLE001
        logger.exception("progress_publish_failed task_id=%s", task_id)


def format_speed(speed_bps: float | int | None) -> str | None:
    if not speed_bps:
        return None
    try:
        speed = float(speed_bps)
    except (TypeError, ValueError):
        return None
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    idx = 0
    while speed >= 1024 and idx < len(units) - 1:
        speed /= 1024
        idx += 1
    return f"{speed:.1f}{units[idx]}"


def format_eta(seconds: float | int | None) -> str | None:
    if seconds is None:
        return None
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return None
    if total < 0:
        return None
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def format_bytes(num_bytes: float | int | None) -> str | None:
    if num_bytes is None:
        return None
    try:
        size = float(num_bytes)
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None
    units = ["B", "KB", "MB", "GB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    if idx == 0:
        return f"{int(size)}{units[idx]}"
    return f"{size:.1f}{units[idx]}"


def format_size_label(
    downloaded: float | int | None,
    total: float | int | None,
) -> str | None:
    """Human size line like ``850MB / 1.2GB``."""
    left = format_bytes(downloaded)
    right = format_bytes(total)
    if left and right:
        return f"{left} / {right}"
    if right:
        return right
    if left:
        return left
    return None


def update_task_progress(
    session: Session,
    task: Task,
    *,
    status: TaskStatus | None = None,
    progress: int | None = None,
    speed: str | None = None,
    eta: str | None = None,
    size: str | None = None,
    error_message: str | None = None,
    file_path: str | None = None,
    download_url: str | None = None,
    download_token: str | None = None,
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """
    Persist task progress and mirror status onto the related Download row.

    Returns the payload published to Redis (for WebSocket clients).
    """
    if status is not None:
        task.status = status
    if progress is not None:
        task.progress = max(0, min(100, int(progress)))
    if speed is not None:
        task.speed = speed
    if eta is not None:
        task.eta = eta
    if size is not None:
        task.size = size
    if error_message is not None:
        task.error_message = error_message
    if file_path is not None:
        task.file_path = file_path
    if download_url is not None:
        task.download_url = download_url
    if download_token is not None:
        task.download_token = download_token
    if celery_task_id is not None:
        task.celery_task_id = celery_task_id

    # Ensure related download is loaded for status mirroring
    download = task.download
    if download is None and task.download_id is not None:
        download = session.get(Download, task.download_id)
    if download is not None and status is not None:
        download.status = DownloadStatus(status.value)

    session.flush()

    payload = {
        "task_id": str(task.id),
        "status": task.status.value,
        "progress": task.progress,
        "speed": task.speed,
        "eta": task.eta,
        "size": task.size,
        "error_message": task.error_message,
        "download_url": task.download_url,
    }
    publish_progress(task.id, payload)
    return payload
