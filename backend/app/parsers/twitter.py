"""Twitter / X parser stub."""

from __future__ import annotations

from app.parsers.base import BaseParser, MediaFormat, MediaInfo
from app.parsers.exceptions import ParserNotImplementedError


class TwitterParser(BaseParser):
    """
    Handles twitter.com (and x.com as the same platform).

    Real extraction comes with yt-dlp.
    """

    platform = "twitter"
    domains = ("twitter.com", "x.com")

    async def analyze(self, url: str) -> MediaInfo:
        raise ParserNotImplementedError(self.platform, "analyze")

    async def get_formats(self, url: str) -> list[MediaFormat]:
        raise ParserNotImplementedError(self.platform, "get_formats")

    async def download(self, url: str, quality: str) -> str:
        raise ParserNotImplementedError(self.platform, "download")
