"""Bot unit tests (no Telegram network)."""

from app.bot.api_client import device_id_for_telegram
from app.bot.handlers.links import extract_url
from app.bot.keyboards import quality_keyboard
from app.bot.texts import format_analyze_caption, progress_bar


def test_extract_url() -> None:
    assert extract_url("смотри https://youtu.be/abc123 hello") == "https://youtu.be/abc123"
    assert extract_url("нет ссылки") is None


def test_device_id_stable() -> None:
    a = device_id_for_telegram(123)
    b = device_id_for_telegram(123)
    assert a == b
    assert len(a) == 36


def test_progress_bar() -> None:
    assert progress_bar(0).startswith("░")
    assert "█" in progress_bar(50)
    assert progress_bar(100) == "██████████"


def test_caption_and_keyboard() -> None:
    caption = format_analyze_caption(
        title="Test <Video>",
        platform="youtube",
        author="Author",
        duration="1:00",
        is_playlist=False,
        playlist_count=None,
    )
    assert "Test &lt;Video&gt;" in caption
    assert "YouTube" in caption

    kb = quality_keyboard(
        "abc123",
        [
            {"quality": "1080p", "format": "mp4", "size": "10MB"},
            {"quality": "720p", "format": "mp4"},
            {"quality": "audio", "format": "m4a"},
        ],
        default_quality="720p",
    )
    assert len(kb.inline_keyboard) >= 2
