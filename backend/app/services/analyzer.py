"""URL analysis orchestration via ParserFactory (no platform hardcoding)."""

from __future__ import annotations

import logging

from app.errors import analyze_failed, parser_not_ready, unsupported_platform
from app.parsers.base import MediaInfo
from app.parsers.exceptions import (
    ParserError,
    ParserNotImplementedError,
    UnsupportedPlatformError,
)
from app.parsers.factory import ParserFactory, get_parser_factory
from app.schemas.analyze import AnalyzeResponse, FormatInfo, PlaylistEntryInfo
from app.services.url_validator import validate_media_url

logger = logging.getLogger("cliperry.analyzer")


class AnalyzerService:
    """
    Analyze flow:

    1. validate URL
    2. detect platform via ParserFactory
    3. select parser
    4. fetch metadata (no permanent file storage)
    """

    def __init__(self, factory: ParserFactory | None = None) -> None:
        self.factory = factory or get_parser_factory()

    async def analyze(self, url: str) -> AnalyzeResponse:
        """Validate → resolve parser → return structured metadata."""
        cleaned = validate_media_url(url)

        try:
            parser = self.factory.get_parser(cleaned)
        except UnsupportedPlatformError as exc:
            raise unsupported_platform(exc.url, exc.supported) from exc

        platform = parser.platform
        logger.info("analyze_start platform=%s url=%s", platform, cleaned)

        try:
            media: MediaInfo = await parser.analyze(cleaned)
        except ParserNotImplementedError as exc:
            raise parser_not_ready(exc.platform) from exc
        except ParserError as exc:
            logger.warning("analyze_failed platform=%s error=%s", platform, exc)
            raise analyze_failed(platform, reason="parser_error") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze_unexpected platform=%s", platform)
            raise analyze_failed(platform, reason="unexpected error") from exc

        response = AnalyzeResponse(
            platform=media.platform,
            title=media.title,
            thumbnail=media.thumbnail,
            formats=[
                FormatInfo(
                    quality=f.quality,
                    format=f.format,
                    size=f.size,
                    format_id=f.format_id,
                    has_audio=f.has_audio,
                    has_video=f.has_video,
                )
                for f in media.formats
            ],
            author=media.author,
            duration=media.duration,
            url=media.url,
            is_playlist=media.is_playlist,
            playlist_count=media.playlist_count,
            entries=[
                PlaylistEntryInfo(
                    id=e.id,
                    title=e.title,
                    thumbnail=e.thumbnail,
                    url=e.url,
                    duration=e.duration,
                    index=e.index,
                )
                for e in media.entries
            ],
        )
        logger.info(
            "analyze_ok platform=%s title=%s formats=%s playlist=%s",
            response.platform,
            response.title,
            len(response.formats),
            response.is_playlist,
        )
        return response
