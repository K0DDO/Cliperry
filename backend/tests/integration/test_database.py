"""Integration: real PostgreSQL persistence."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.models.device import Device
from app.models.download import Download, DownloadStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.history_service import HistoryService
from app.services.task_service import TaskService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_user_device_roundtrip(db_session, seeded_device: Device) -> None:
    assert seeded_device.id is not None
    loaded = await db_session.get(Device, seeded_device.id)
    assert loaded is not None
    assert loaded.device_id == seeded_device.device_id

    user = await db_session.get(User, seeded_device.user_id)
    assert user is not None
    assert user.is_active is True


@pytest.mark.asyncio
async def test_download_task_history_flow(db_session, seeded_device: Device) -> None:
    download = Download(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        platform="youtube",
        title="Integration Clip",
        quality="720p",
        status=DownloadStatus.COMPLETED,
        user_id=seeded_device.user_id,
        device_id=seeded_device.id,
    )
    db_session.add(download)
    await db_session.flush()

    task = Task(
        download_id=download.id,
        status=TaskStatus.COMPLETED,
        progress=100,
        celery_task_id="integration-celery-id",
    )
    db_session.add(task)
    await db_session.commit()

    history = HistoryService(db_session)
    page = await history.list_downloads(seeded_device, page=1, page_size=10)
    assert page.total == 1
    assert page.items[0].title == "Integration Clip"
    assert page.items[0].status == "completed"

    service = TaskService(db_session)
    status = await service.get_task(task.id, seeded_device)
    assert status.status == "completed"
    assert status.progress == 100
    assert status.title == "Integration Clip"


@pytest.mark.asyncio
async def test_task_isolation_by_device(db_session, seeded_device: Device) -> None:
    other_user = User(is_active=True)
    db_session.add(other_user)
    await db_session.flush()
    other = Device(device_id=str(uuid.uuid4()), user_id=other_user.id)
    db_session.add(other)
    await db_session.flush()

    download = Download(
        url="https://www.youtube.com/watch?v=aaaaaaaaaaa",
        platform="youtube",
        title="Secret",
        quality="1080p",
        status=DownloadStatus.QUEUED,
        user_id=other_user.id,
        device_id=other.id,
    )
    db_session.add(download)
    await db_session.flush()
    task = Task(download_id=download.id, status=TaskStatus.QUEUED, progress=0)
    db_session.add(task)
    await db_session.commit()

    service = TaskService(db_session)
    with pytest.raises(Exception) as exc:
        await service.get_task(task.id, seeded_device)
    assert getattr(exc.value, "status_code", None) == 404

    count = (
        await db_session.execute(select(func.count()).select_from(Download))
    ).scalar_one()
    assert int(count) >= 1
