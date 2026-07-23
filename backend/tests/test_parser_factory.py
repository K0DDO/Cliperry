"""ParserFactory domain routing tests."""

import pytest

from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.factory import ParserFactory
from app.parsers.youtube import YoutubeParser


@pytest.mark.parametrize(
    ("url", "platform", "parser_cls"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", YoutubeParser),
        ("https://youtu.be/abc", "youtube", YoutubeParser),
        ("https://www.youtube.com/shorts/abc", "youtube", YoutubeParser),
    ],
)
def test_factory_detects_youtube(
    url: str,
    platform: str,
    parser_cls: type,
) -> None:
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
        "https://example.com/video",
    ],
)
def test_factory_rejects_unready_platforms(url: str) -> None:
    factory = ParserFactory()
    with pytest.raises(UnsupportedPlatformError):
        factory.get_parser(url)


@pytest.mark.asyncio
async def test_tiktok_stub_still_not_implemented() -> None:
    from app.parsers.exceptions import ParserNotImplementedError
    from app.parsers.tiktok import TikTokParser

    parser = TikTokParser()
    with pytest.raises(ParserNotImplementedError):
        await parser.analyze("https://www.tiktok.com/@user/video/123")
