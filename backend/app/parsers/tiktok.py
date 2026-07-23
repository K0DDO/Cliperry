"""TikTok parser powered by yt-dlp."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.parsers import ytdlp
from app.parsers.base import BaseParser, MediaFormat, MediaInfo
from app.parsers.exceptions import ParserError
from app.parsers.youtube_formats import (
    build_quality_formats,
    format_duration,
    selector_for_quality,
)

logger = logging.getLogger("cliperry.parsers.tiktok")


class TikTokParser(BaseParser):
    """TikTok / vm.tiktok.com extractor (single videos)."""

    platform = "tiktok"
    domains = ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com")

    def __init__(self, storage: object | None = None) -> None:
        if storage is None:
            from app.services.storage import StorageService

            storage = StorageService()
        self.storage = storage

    async def analyze(self, url: str) -> MediaInfo:
        try:
            info = await ytdlp.extract_info(url, flat=False)
        except ytdlp.YtDlpError as exc:
            raise ParserError(str(exc)) from exc
        return self._video_from_info(url, info)

    async def get_formats(self, url: str) -> list[MediaFormat]:
        try:
            info = await ytdlp.extract_info(url, flat=False)
        except ytdlp.YtDlpError as exc:
            raise ParserError(str(exc)) from exc
        return build_quality_formats(info.get("formats"))

    async def download(self, url: str, quality: str) -> str:
        return await asyncio.to_thread(self.download_sync, url, quality)

    def download_sync(
        self,
        url: str,
        quality: str,
        *,
        artifact_id: str | None = None,
        progress_hook: Any | None = None,
    ) -> str:
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
            "temp_download platform=tiktok artifact_id=%s path=%s quality=%s",
            artifact.artifact_id,
            path,
            quality,
        )
        return path

    def _video_from_info(self, url: str, info: dict[str, Any]) -> MediaInfo:
        formats = build_quality_formats(info.get("formats"))
        thumbnails = info.get("thumbnails") or []
        thumbnail = info.get("thumbnail")
        if not thumbnail and thumbnails:
            thumbnail = thumbnails[-1].get("url")

        return MediaInfo(
            title=info.get("title") or info.get("description") or "TikTok video",
            platform=self.platform,
            url=info.get("webpage_url") or url,
            thumbnail=thumbnail,
            duration=format_duration(info.get("duration")),
            author=info.get("uploader") or info.get("creator") or info.get("channel"),
            is_playlist=False,
            formats=formats,
        )
