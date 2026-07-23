"""WebSocket endpoint for real-time download progress."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.redis import get_redis
from app.database.session import get_session_factory
from app.models.device import Device
from app.models.download import Download
from app.models.task import Task
from app.services.progress import progress_channel

logger = logging.getLogger("cliperry.ws")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: uuid.UUID) -> None:
    """
    Real-time progress channel for a download task.

    Connect: ``ws://host/ws/tasks/{task_id}?device_id=<X-Device-Id>``

    ``device_id`` is required — ownership is always enforced.
    """
    await websocket.accept()
    device_key = (websocket.query_params.get("device_id") or "").strip()
    if not device_key:
        await websocket.send_json(
            {
                "error": True,
                "code": "unauthorized",
                "message": "Требуется device_id",
            }
        )
        await websocket.close(code=4401)
        return

    try:
        device_key = str(uuid.UUID(device_key))
    except ValueError:
        await websocket.send_json(
            {
                "error": True,
                "code": "unauthorized",
                "message": "Некорректный device_id",
            }
        )
        await websocket.close(code=4401)
        return

    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await session.execute(
            select(Task)
            .join(Download, Task.download_id == Download.id)
            .where(Task.id == task_id)
            .options(selectinload(Task.download))
        )
        task = result.scalar_one_or_none()
        if task is None:
            await websocket.send_json(
                {"error": True, "code": "task_not_found", "message": "Задача не найдена"}
            )
            await websocket.close(code=4404)
            return

        device = (
            await session.execute(select(Device).where(Device.device_id == device_key))
        ).scalar_one_or_none()
        if (
            device is None
            or task.download is None
            or task.download.device_id != device.id
        ):
            await websocket.send_json(
                {
                    "error": True,
                    "code": "forbidden",
                    "message": "Нет доступа к этой задаче",
                }
            )
            await websocket.close(code=4403)
            return

        await websocket.send_json(_public_snapshot(task))
        if task.status.value in {"completed", "failed"}:
            await websocket.close()
            return

    redis = get_redis()
    pubsub = redis.pubsub()
    channel = progress_channel(task_id)
    await pubsub.subscribe(channel)

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    payload = json.loads(data) if isinstance(data, str) else data
                except json.JSONDecodeError:
                    payload = {"raw": data}
                if isinstance(payload, dict):
                    payload = _sanitize_progress_payload(payload)
                await websocket.send_json(payload)
                if isinstance(payload, dict) and payload.get("status") in {
                    "completed",
                    "failed",
                }:
                    break
            else:
                async with session_factory() as session:
                    current = (
                        await session.execute(
                            select(Task)
                            .where(Task.id == task_id)
                            .options(selectinload(Task.download))
                        )
                    ).scalar_one_or_none()
                    if current is None:
                        break
                    # Re-check ownership was already proven; keep snapshots public-safe.
                    await websocket.send_json(_public_snapshot(current))
                    if current.status.value in {"completed", "failed"}:
                        break

            disconnected = False
            try:
                await asyncio.wait_for(websocket.receive(), timeout=0.05)
            except TimeoutError:
                pass
            except WebSocketDisconnect:
                disconnected = True
            if disconnected:
                break

            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        logger.info("ws_disconnected task_id=%s", task_id)
    except Exception:  # noqa: BLE001
        logger.exception("ws_error task_id=%s", task_id)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


def _public_snapshot(task: Task) -> dict:
    """Client-safe task snapshot (no local file paths)."""
    return {
        "task_id": str(task.id),
        "status": task.status.value,
        "progress": task.progress,
        "speed": task.speed,
        "eta": task.eta,
        "error_message": task.error_message,
        "download_url": task.download_url,
        "size": getattr(task, "size", None),
    }


def _sanitize_progress_payload(payload: dict) -> dict:
    """Drop internal-only fields from worker pub/sub messages."""
    blocked = {"file_path", "celery_task_id", "download_token"}
    return {key: value for key, value in payload.items() if key not in blocked}
