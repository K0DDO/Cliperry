"""Unit: ParserFactory routing and stub parsers."""

from __future__ import annotations

import pytest

from app.parsers.exceptions import ParserNotImplementedError, UnsupportedPlatformError
from app.parsers.factory import ParserFactory
from app.parsers.instagram import InstagramParser
from app.parsers.tiktok import TikTokParser
from app.parsers.twitter import TwitterParser
from app.parsers.youtube import YoutubeParser

pytestmark = [pytest.mark.unit, pytest.mark.parsers]


@pytest.mark.parametrize(
    ("url", "platform", "parser_cls"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", YoutubeParser),
        ("https://youtu.be/abc", "youtube", YoutubeParser),
        ("https://www.youtube.com/shorts/abc", "youtube", YoutubeParser),
    ],
)
def test_factory_detects_youtube(url: str, platform: str, parser_cls: type) -> None:
    factory = ParserFactory()
    parser = factory.get_parser(url)
    assert parser.platform == platform
    assert isinstance(parser, parser_cls)
    assert factory.detect_platform(url) == platform


@pytest.mark.parametrize(
    "url",
    [
        "https://www.tiktok.com/@user/video/123",
        "https://www.instagram.com/reel/abc/",
        "https://twitter.com/user/status/123",
        "https://x.com/user/status/123",
        "https://example.com/video",
    ],
)
def test_factory_rejects_unready_or_unknown(url: str) -> None:
    factory = ParserFactory()
    with pytest.raises(UnsupportedPlatformError):
        factory.get_parser(url)


def test_factory_lists_ready_platforms_only() -> None:
    factory = ParserFactory()
    platforms = factory.list_platforms()
    assert platforms == ["youtube"]


def test_factory_can_register_stub_later() -> None:
    factory = ParserFactory()
    factory.register(TikTokParser)
    parser = factory.get_parser("https://www.tiktok.com/@user/video/123")
    assert isinstance(parser, TikTokParser)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "parser_cls",
    [TikTokParser, InstagramParser, TwitterParser],
)
async def test_stub_parsers_not_implemented(parser_cls: type) -> None:
    parser = parser_cls()
    with pytest.raises(ParserNotImplementedError):
        await parser.analyze("https://example.com/x")
