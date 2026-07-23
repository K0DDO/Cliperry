"""Unit tests for YoutubeParser (yt-dlp mocked)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.parsers.youtube import YoutubeParser
from app.parsers.youtube_formats import build_quality_formats, format_duration
from app.services.storage import StorageService


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

SAMPLE_PLAYLIST_INFO = {
    "_type": "playlist",
    "title": "Python Course",
    "uploader": "Teacher",
    "webpage_url": "https://www.youtube.com/playlist?list=PLtest",
    "playlist_count": 2,
    "entries": [
        {
            "id": "vid1",
            "title": "Video 1",
            "thumbnail": "https://i.ytimg.com/vi/vid1/hqdefault.jpg",
            "duration": 60,
        },
        {
            "id": "vid2",
            "title": "Video 2",
            "thumbnails": [{"url": "https://i.ytimg.com/vi/vid2/hqdefault.jpg"}],
            "duration": 90,
        },
    ],
}


def test_build_quality_formats_ladder() -> None:
    formats = build_quality_formats(SAMPLE_VIDEO_INFO["formats"])
    qualities = [f.quality for f in formats]
    assert qualities == ["1080p", "720p", "480p", "audio"]
    assert formats[-1].has_video is False


def test_format_duration() -> None:
    assert format_duration(212) == "3:32"
    assert format_duration(3661) == "1:01:01"


@pytest.mark.asyncio
async def test_analyze_video(tmp_path: Path) -> None:
    parser = YoutubeParser(storage=StorageService(settings=None))
    # Override temp dir via allocate path — StorageService uses settings; patch root
    parser.storage.temp_root = tmp_path
    parser.storage.temp_root.mkdir(parents=True, exist_ok=True)

    with patch(
        "app.parsers.youtube.ytdlp.extract_info",
        new=AsyncMock(return_value=SAMPLE_VIDEO_INFO),
    ):
        media = await parser.analyze("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert media.title == "Never Gonna Give You Up"
    assert media.author == "Rick Astley"
    assert media.thumbnail is not None
    assert media.duration == "3:32"
    assert media.is_playlist is False
    assert [f.quality for f in media.formats] == ["1080p", "720p", "480p", "audio"]


@pytest.mark.asyncio
async def test_get_formats(tmp_path: Path) -> None:
    parser = YoutubeParser()
    with patch(
        "app.parsers.youtube.ytdlp.extract_info",
        new=AsyncMock(return_value=SAMPLE_VIDEO_INFO),
    ):
        formats = await parser.get_formats("https://youtu.be/dQw4w9WgXcQ")
    assert [f.quality for f in formats] == ["1080p", "720p", "480p", "audio"]


@pytest.mark.asyncio
async def test_analyze_playlist() -> None:
    parser = YoutubeParser()
    with patch(
        "app.parsers.youtube.ytdlp.extract_info",
        new=AsyncMock(return_value=SAMPLE_PLAYLIST_INFO),
    ):
        media = await parser.analyze(
            "https://www.youtube.com/playlist?list=PLtest"
        )

    assert media.is_playlist is True
    assert media.title == "Python Course"
    assert media.playlist_count == 2
    assert len(media.entries) == 2
    assert media.entries[0].id == "vid1"
    assert media.entries[0].thumbnail is not None
    assert media.entries[1].id == "vid2"
    assert media.formats == []


@pytest.mark.asyncio
async def test_download_uses_temp_storage(tmp_path: Path) -> None:
    from app.config import Settings

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
        target = out_dir / "dQw4w9WgXcQ.mp4"
        target.write_bytes(b"fake")
        return str(target)

    with patch("app.parsers.youtube.ytdlp.download_sync", new=fake_download_sync):
        path = await parser.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "720p",
        )

    assert Path(path).exists()
    assert path.startswith(str(tmp_path))
    meta = Path(path).parent / StorageService.META_NAME
    assert meta.exists()
