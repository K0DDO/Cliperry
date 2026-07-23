"""Platform parser system — factory-based, no platform logic in API routes."""

from app.parsers.base import BaseParser, MediaFormat, MediaInfo, PlaylistEntry
from app.parsers.exceptions import (
    ParserError,
    ParserNotImplementedError,
    UnsupportedPlatformError,
)
from app.parsers.factory import ParserFactory, get_parser_factory, parser_factory
from app.parsers.instagram import InstagramParser
from app.parsers.registry import ParserRegistry, get_parser_registry, parser_registry
from app.parsers.tiktok import TikTokParser
from app.parsers.twitter import TwitterParser
from app.parsers.youtube import YoutubeParser

__all__ = [
    "BaseParser",
    "MediaFormat",
    "MediaInfo",
    "PlaylistEntry",
    "ParserError",
    "ParserNotImplementedError",
    "UnsupportedPlatformError",
    "ParserFactory",
    "parser_factory",
    "get_parser_factory",
    "ParserRegistry",
    "parser_registry",
    "get_parser_registry",
    "YoutubeParser",
    "TikTokParser",
    "InstagramParser",
    "TwitterParser",
]
