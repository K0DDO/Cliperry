"""ParserFactory domain routing tests."""

import pytest

from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.factory import ParserFactory
from app.parsers.instagram import InstagramParser
from app.parsers.tiktok import TikTokParser
from app.parsers.youtube import YoutubeParser


@pytest.mark.parametrize(
    ("url", "platform", "parser_cls"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", YoutubeParser),
        ("https://youtu.be/abc", "youtube", YoutubeParser),
        ("https://www.tiktok.com/@user/video/123", "tiktok", TikTokParser),
        ("https://www.instagram.com/reel/abc/", "instagram", InstagramParser),
    ],
)
def test_factory_detects_platforms(
    url: str,
    platform: str,
    parser_cls: type,
) -> None:
    factory = ParserFactory()
    parser = factory.get_parser(url)
    assert parser.platform == platform
    assert isinstance(parser, parser_cls)


def test_factory_rejects_unknown() -> None:
    factory = ParserFactory()
    with pytest.raises(UnsupportedPlatformError):
        factory.get_parser("https://example.com/video")
