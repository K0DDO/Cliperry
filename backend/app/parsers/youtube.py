"""YouTube / YouTube Shorts / playlist parser powered by yt-dlp."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.parsers.base import BaseParser, MediaFormat, MediaInfo, PlaylistEntry
from app.parsers.exceptions import ParserError
from app.parsers import ytdlp
from app.parsers.youtube_formats import (
    build_quality_formats,
    format_duration,
    selector_for_quality,
)

logger = logging.getLogger("cliperry.parsers.youtube")


class YoutubeParser(BaseParser):
    """
    YouTube extractor.

    - ``analyze`` / ``get_formats`` never write media to disk
    - ``download`` writes only into TTL-managed temporary storage
    """

    platform = "youtube"
    domains = ("youtube.com", "youtu.be")

    def __init__(self, storage: object | None = None) -> None:
        # Lazy import avoids circular dependency: parsers ↔ services
        if storage is None:
            from app.services.storage import StorageService

            storage = StorageService()
        self.storage = storage

    async def analyze(self, url: str) -> MediaInfo:
        """Return video or playlist metadata (no file download)."""
        if self._looks_like_playlist(url):
            return await self._analyze_playlist(url)

        try:
            info = await ytdlp.extract_info(url, flat=False)
        except ytdlp.YtDlpError as exc:
            raise ParserError(str(exc)) from exc

        # Playlist disguised as a watch URL with list= — prefer single video when
        # extract returned a playlist wrapper with entries
        if info.get("_type") == "playlist":
            return self._playlist_from_info(url, info)

        return self._video_from_info(url, info)

    async def get_formats(self, url: str) -> list[MediaFormat]:
        """Return 1080p / 720p / 480p / audio options available for the URL."""
        if self._looks_like_playlist(url):
            # Formats apply to individual videos, not the playlist container
            return []

        try:
            info = await ytdlp.extract_info(url, flat=False)
        except ytdlp.YtDlpError as exc:
            raise ParserError(str(exc)) from exc

        if info.get("_type") == "playlist":
            return []

        return build_quality_formats(info.get("formats"))

    async def download(self, url: str, quality: str) -> str:
        """
        Download into temporary storage and return the file path.

        The file lives under ``TEMP_DIR/{artifact_id}/`` and is eligible for
        cleanup after ``TEMP_FILE_TTL_SECONDS``. Callers must serve it via a
        short-lived signed URL — never treat this path as permanent storage.
        """
        return await asyncio.to_thread(
            self.download_sync,
            url,
            quality,
        )

    def download_sync(
        self,
        url: str,
        quality: str,
        *,
        artifact_id: str | None = None,
        progress_hook: Any | None = None,
    ) -> str:
        """Synchronous download used by Celery workers."""
        if self._looks_like_playlist(url):
            raise ParserError("Cannot download an entire playlist in one call; pick a video")

        try:
            selector = selector_for_quality(quality)
        except ValueError as exc:
            raise ParserError(str(exc)) from exc

        artifact = self.storage.allocate(artifact_id)
        try:
            path = ytdlp.download_sync(
                url,
                output_template=artifact.output_template,
                format_selector=selector,
                progress_hook=progress_hook,
            )
        except ytdlp.YtDlpError as exc:
            self.storage.cleanup_task_dir(artifact.artifact_id)
            raise ParserError(str(exc)) from exc

        logger.info(
            "temp_download artifact_id=%s path=%s expires_at=%s quality=%s",
            artifact.artifact_id,
            path,
            artifact.expires_at,
            quality,
        )
        return path

    async def _analyze_playlist(self, url: str) -> MediaInfo:
        try:
            info = await ytdlp.extract_info(url, flat=True)
        except ytdlp.YtDlpError as exc:
            raise ParserError(str(exc)) from exc
        return self._playlist_from_info(url, info)

    def _video_from_info(self, url: str, info: dict[str, Any]) -> MediaInfo:
        formats = build_quality_formats(info.get("formats"))
        thumbnails = info.get("thumbnails") or []
        thumbnail = info.get("thumbnail")
        if not thumbnail and thumbnails:
            thumbnail = thumbnails[-1].get("url")

        return MediaInfo(
            title=info.get("title") or "Untitled",
            platform=self.platform,
            url=info.get("webpage_url") or url,
            thumbnail=thumbnail,
            duration=format_duration(info.get("duration")),
            author=info.get("uploader") or info.get("channel") or info.get("creator"),
            is_playlist=False,
            formats=formats,
        )

    def _playlist_from_info(self, url: str, info: dict[str, Any]) -> MediaInfo:
        raw_entries = info.get("entries") or []
        entries: list[PlaylistEntry] = []
        for index, entry in enumerate(raw_entries, start=1):
            if not entry:
                continue
            video_id = str(entry.get("id") or entry.get("url") or index)
            title = entry.get("title") or f"Video {index}"
            thumb = entry.get("thumbnail")
            if not thumb:
                thumbs = entry.get("thumbnails") or []
                if thumbs:
                    thumb = thumbs[-1].get("url")
            entry_url = entry.get("url") or entry.get("webpage_url")
            if entry_url and not str(entry_url).startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={video_id}"
            elif not entry_url and video_id:
                entry_url = f"https://www.youtube.com/watch?v={video_id}"

            entries.append(
                PlaylistEntry(
                    id=video_id,
                    title=title,
                    thumbnail=thumb,
                    url=entry_url,
                    duration=format_duration(entry.get("duration")),
                    index=index,
                )
            )

        count = info.get("playlist_count") or len(entries)
        return MediaInfo(
            title=info.get("title") or info.get("playlist_title") or "Playlist",
            platform=self.platform,
            url=info.get("webpage_url") or info.get("original_url") or url,
            thumbnail=info.get("thumbnails", [{}])[-1].get("url") if info.get("thumbnails") else None,
            duration=None,
            author=info.get("uploader") or info.get("channel"),
            is_playlist=True,
            playlist_count=int(count) if count is not None else len(entries),
            formats=[],
            entries=entries,
        )

    @staticmethod
    def _looks_like_playlist(url: str) -> bool:
        """Heuristic: dedicated playlist URLs (not a watch URL with &list=)."""
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        if "/playlist" in path:
            return True
        query = parse_qs(parsed.query)
        # Pure playlist id without a video id
        if "list" in query and "v" not in query:
            return True
        return False
