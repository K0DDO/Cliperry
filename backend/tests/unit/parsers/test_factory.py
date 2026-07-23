"""Unit: ParserFactory routing."""

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
        ("https://www.tiktok.com/@user/video/123", "tiktok", TikTokParser),
        ("https://vm.tiktok.com/ZMabc/", "tiktok", TikTokParser),
        ("https://www.instagram.com/reel/abc/", "instagram", InstagramParser),
        ("https://www.instagram.com/p/abc/", "instagram", InstagramParser),
    ],
)
def test_factory_detects_ready_platforms(url: str, platform: str, parser_cls: type) -> None:
    factory = ParserFactory()
    parser = factory.get_parser(url)
    assert parser.platform == platform
    assert isinstance(parser, parser_cls)
    assert factory.detect_platform(url) == platform


@pytest.mark.parametrize(
    "url",
    [
        "https://twitter.com/user/status/123",
        "https://x.com/user/status/123",
        "https://example.com/video",
    ],
)
def test_factory_rejects_unknown(url: str) -> None:
    factory = ParserFactory()
    with pytest.raises(UnsupportedPlatformError):
        factory.get_parser(url)


def test_factory_lists_ready_platforms() -> None:
    factory = ParserFactory()
    assert factory.list_platforms() == ["youtube", "tiktok", "instagram"]


@pytest.mark.asyncio
async def test_twitter_stub_still_not_implemented() -> None:
    parser = TwitterParser()
    with pytest.raises(ParserNotImplementedError):
        await parser.analyze("https://x.com/user/status/1")
