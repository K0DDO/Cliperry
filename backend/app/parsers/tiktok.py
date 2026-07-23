"""TikTok parser stub."""

from __future__ import annotations

from app.parsers.base import BaseParser, MediaFormat, MediaInfo
from app.parsers.exceptions import ParserNotImplementedError


class TikTokParser(BaseParser):
    """Handles tiktok.com. Real extraction comes with yt-dlp."""

    platform = "tiktok"
    domains = ("tiktok.com",)

    async def analyze(self, url: str) -> MediaInfo:
        raise ParserNotImplementedError(self.platform, "analyze")

    async def get_formats(self, url: str) -> list[MediaFormat]:
        raise ParserNotImplementedError(self.platform, "get_formats")

    async def download(self, url: str, quality: str) -> str:
        raise ParserNotImplementedError(self.platform, "download")
