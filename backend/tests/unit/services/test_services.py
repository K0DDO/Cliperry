"""Unit: URL validation + storage + history/task services (mocked session)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.errors import AppError
from app.models.download import DownloadStatus
from app.schemas.download import DownloadRequest
from app.services.download_service import DownloadService
from app.services.history_service import HistoryService
from app.services.storage import StorageService
from app.services.task_service import TaskService
from app.services.url_validator import validate_media_url

pytestmark = [pytest.mark.unit, pytest.mark.services]


def test_validate_youtube_url() -> None:
    url = validate_media_url(" https://www.youtube.com/watch?v=dQw4w9WgXcQ ")
    assert url.startswith("https://")


def test_validate_rejects_private_ip() -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url("http://192.168.0.10/video.mp4")
    assert exc.value.code == "invalid_url"


def test_storage_token_roundtrip(tmp_path: Path) -> None:
    settings = Settings(
        temp_dir=str(tmp_path),
        secret_key="unit-test-secret-key-32chars-min!!",
        admin_password="unit-test-admin-password",
        app_env="test",
        temp_file_ttl_seconds=600,
    )
    storage = StorageService(settings=settings)
    task_id = str(uuid.uuid4())
    token = storage.create_download_token(task_id)
    assert storage.verify_download_token(task_id, token) is True
    assert storage.verify_download_token(task_id, "0.deadbeef") is False
    assert storage.verify_download_token("other-id", token) is False


def test_storage_allocate_and_cleanup(tmp_path: Path) -> None:
    settings = Settings(
        temp_dir=str(tmp_path),
        secret_key="unit-test-secret-key-32chars-min!!",
        admin_password="unit-test-admin-password",
        app_env="test",
    )
    storage = StorageService(settings=settings)
    artifact = storage.allocate("task-abc")
    assert artifact.directory.exists()
    (artifact.directory / "file.bin").write_bytes(b"x")
    storage.cleanup_task_dir("task-abc")
    assert not (tmp_path / "task-abc").exists()


@pytest.mark.asyncio
async def test_history_service_pagination() -> None:
    device = MagicMock()
    device.id = uuid.uuid4()

    row = MagicMock()
    row.id = uuid.uuid4()
    row.title = "Demo"
    row.platform = "youtube"
    row.status = DownloadStatus.COMPLETED
    row.quality = "720p"
    row.created_at = datetime.now(timezone.utc)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[count_result, rows_result])

    service = HistoryService(session)
    result = await service.list_downloads(device, page=1, page_size=10)
    assert result.total == 1
    assert result.items[0].title == "Demo"
    assert result.has_next is False


@pytest.mark.asyncio
async def test_task_service_not_found() -> None:
    device = MagicMock()
    device.id = uuid.uuid4()
    session = AsyncMock()
    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=empty)

    service = TaskService(session)
    with pytest.raises(AppError) as exc:
        await service.get_task(uuid.uuid4(), device)
    assert exc.value.status_code == 404
    assert exc.value.code == "task_not_found"


@pytest.mark.asyncio
async def test_download_service_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    device = MagicMock()
    device.id = uuid.uuid4()
    device.user_id = uuid.uuid4()

    session = AsyncMock()
    session.add = MagicMock()

    async def fake_flush() -> None:
        for call in session.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    session.flush = AsyncMock(side_effect=fake_flush)

    celery_result = MagicMock()
    celery_result.id = "celery-123"
    monkeypatch.setattr(
        "app.services.download_service.download_media.delay",
        MagicMock(return_value=celery_result),
    )

    service = DownloadService(session)
    payload = DownloadRequest(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        quality="720p",
        title="Demo",
    )
    result = await service.create_download(device, payload)
    assert result.status == "queued"
    assert result.task_id is not None
    assert result.download_id is not None
    assert session.add.call_count >= 2
