"""Unit: YoutubeParser with yt-dlp mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.parsers.youtube import YoutubeParser
from app.parsers.youtube_formats import build_quality_formats, format_duration
from app.services.storage import StorageService

pytestmark = [pytest.mark.unit, pytest.mark.parsers]

SAMPLE_VIDEO_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "uploader": "Rick Astley",
    "channel": "Rick Astley",
    "duration": 212,
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    "formats": [
        {
            "format_id": "137",
            "height": 1080,
            "ext": "mp4",
            "vcodec": "avc1",
            "acodec": "none",
            "filesize": 50_000_000,
        },
        {
            "format_id": "136",
            "height": 720,
            "ext": "mp4",
            "vcodec": "avc1",
            "acodec": "none",
            "filesize": 25_000_000,
        },
        {
            "format_id": "135",
            "height": 480,
            "ext": "mp4",
            "vcodec": "avc1",
            "acodec": "none",
            "filesize": 12_000_000,
        },
        {
            "format_id": "140",
            "height": None,
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a",
            "abr": 128,
            "filesize": 3_000_000,
        },
    ],
}


def test_build_quality_formats_ladder() -> None:
    formats = build_quality_formats(SAMPLE_VIDEO_INFO["formats"])
    assert [f.quality for f in formats] == ["1080p", "720p", "480p", "audio"]


def test_format_duration() -> None:
    assert format_duration(212) == "3:32"
    assert format_duration(3661) == "1:01:01"


@pytest.mark.asyncio
async def test_analyze_video() -> None:
    parser = YoutubeParser()
    with patch(
        "app.parsers.youtube.ytdlp.extract_info",
        new=AsyncMock(return_value=SAMPLE_VIDEO_INFO),
    ):
        media = await parser.analyze("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert media.title == "Never Gonna Give You Up"
    assert media.platform == "youtube"
    assert [f.quality for f in media.formats] == ["1080p", "720p", "480p", "audio"]


@pytest.mark.asyncio
async def test_download_writes_temp_file(tmp_path: Path) -> None:
    settings = Settings(
        temp_dir=str(tmp_path),
        secret_key="unit-test-secret-key-32chars-min!!",
        admin_password="unit-test-admin-password",
        app_env="test",
    )
    storage = StorageService(settings=settings)
    parser = YoutubeParser(storage=storage)

    def fake_download_sync(
        url: str,
        *,
        output_template: str,
        format_selector: str,
        progress_hook=None,
    ) -> str:
        out_dir = Path(output_template).parent
        target = out_dir / "clip.mp4"
        target.write_bytes(b"fake-bytes")
        return str(target)

    with patch("app.parsers.youtube.ytdlp.download_sync", new=fake_download_sync):
        path = await parser.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "720p",
        )
    assert Path(path).exists()
    assert path.startswith(str(tmp_path))
