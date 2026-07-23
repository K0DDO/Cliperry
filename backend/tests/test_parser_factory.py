"""ParserFactory domain routing tests."""

import pytest

from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.factory import ParserFactory
from app.parsers.instagram import InstagramParser
from app.parsers.tiktok import TikTokParser
from app.parsers.twitter import TwitterParser
from app.parsers.youtube import YoutubeParser


@pytest.mark.parametrize(
    ("url", "platform", "parser_cls"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", YoutubeParser),
        ("https://youtu.be/abc", "youtube", YoutubeParser),
        ("https://www.youtube.com/shorts/abc", "youtube", YoutubeParser),
        ("https://www.tiktok.com/@user/video/123", "tiktok", TikTokParser),
        ("https://www.instagram.com/reel/abc/", "instagram", InstagramParser),
        ("https://twitter.com/user/status/123", "twitter", TwitterParser),
        ("https://x.com/user/status/123", "twitter", TwitterParser),
    ],
)
def test_factory_detects_platform(
    url: str,
    platform: str,
    parser_cls: type,
) -> None:
    factory = ParserFactory()
    parser = factory.get_parser(url)
    assert parser.platform == platform
    assert isinstance(parser, parser_cls)
    assert factory.detect_platform(url) == platform


def test_factory_rejects_unknown_domain() -> None:
    factory = ParserFactory()
    with pytest.raises(UnsupportedPlatformError):
        factory.get_parser("https://example.com/video")


@pytest.mark.asyncio
async def test_tiktok_stub_still_not_implemented() -> None:
    from app.parsers.exceptions import ParserNotImplementedError
    from app.parsers.tiktok import TikTokParser

    parser = TikTokParser()
    with pytest.raises(ParserNotImplementedError):
        await parser.analyze("https://www.tiktok.com/@user/video/123")
