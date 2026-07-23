"""Tests for bot progress formatting / throttled updates."""

from app.bot.texts import format_download_progress, progress_bar


def test_progress_card_layout() -> None:
    text = format_download_progress(
        quality="720p",
        progress=60,
        size="850MB / 1.2GB",
        speed="8.5MB/s",
        eta="20s",
        title="Demo Video",
    )
    assert "⬇️" in text
    assert "Загрузка" in text
    assert progress_bar(60) in text
    assert "60%" in text
    assert "850MB / 1.2GB" in text
    assert "8.5MB/s" in text
    assert "ETA 20s" in text


def test_progress_bar_bounds() -> None:
    assert progress_bar(0) == "░░░░░░░░░░"
    assert progress_bar(100) == "██████████"
    assert progress_bar(150) == "██████████"
