"""Normalize yt-dlp format lists into Cliperry quality ladder."""

from __future__ import annotations

from typing import Any

from app.parsers.base import MediaFormat

QUALITY_LADDER: tuple[str, ...] = ("1080p", "720p", "480p", "audio")

_HEIGHT_TARGETS: dict[str, int] = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
}

FORMAT_SELECTORS: dict[str, str] = {
    "1080p": (
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
    ),
    "720p": (
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    ),
    "480p": (
        "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
    ),
    "audio": "bestaudio[ext=m4a]/bestaudio/best",
}


def format_duration(seconds: int | float | None) -> str | None:
    """Format seconds as H:MM:SS or M:SS."""
    if seconds is None:
        return None
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return None
    if total < 0:
        return None
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_filesize(num_bytes: int | float | None) -> str | None:
    """Human-readable size string."""
    if num_bytes is None:
        return None
    try:
        size = float(num_bytes)
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None
    units = ("B", "KB", "MB", "GB")
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    if idx == 0:
        return f"{int(size)}{units[idx]}"
    return f"{size:.1f}{units[idx]}"


def _is_audio_only(fmt: dict[str, Any]) -> bool:
    vcodec = (fmt.get("vcodec") or "none").lower()
    acodec = (fmt.get("acodec") or "none").lower()
    return vcodec in {"none", ""} and acodec not in {"none", ""}


def _is_video(fmt: dict[str, Any]) -> bool:
    vcodec = (fmt.get("vcodec") or "none").lower()
    return vcodec not in {"none", ""}


def _pick_size(fmt: dict[str, Any] | None) -> str | None:
    if not fmt:
        return None
    return format_filesize(fmt.get("filesize") or fmt.get("filesize_approx"))


def build_quality_formats(raw_formats: list[dict[str, Any]] | None) -> list[MediaFormat]:
    """
    Always expose the Cliperry ladder: 1080p, 720p, 480p, audio.

    Sizes are best-effort estimates from the closest matching yt-dlp format.
    """
    formats = raw_formats or []
    best_under_cap: dict[str, dict[str, Any]] = {}
    best_audio: dict[str, Any] | None = None

    for fmt in formats:
        if _is_audio_only(fmt):
            if best_audio is None or (fmt.get("abr") or 0) > (best_audio.get("abr") or 0):
                best_audio = fmt
            continue
        if not _is_video(fmt):
            continue
        height = fmt.get("height")
        if not isinstance(height, int):
            continue
        for label, cap in _HEIGHT_TARGETS.items():
            if height <= cap:
                current = best_under_cap.get(label)
                cur_h = (current or {}).get("height") or 0
                if current is None or height > cur_h:
                    best_under_cap[label] = fmt

    result: list[MediaFormat] = []
    for label in ("1080p", "720p", "480p"):
        source = best_under_cap.get(label)
        ext = (source or {}).get("ext") or "mp4"
        result.append(
            MediaFormat(
                quality=label,
                format="mp4" if ext in {"mp4", "m4v", "webm", "mkv"} else ext,
                size=_pick_size(source),
                format_id=FORMAT_SELECTORS[label],
                has_audio=True,
                has_video=True,
            )
        )

    audio_ext = (best_audio or {}).get("ext") or "m4a"
    result.append(
        MediaFormat(
            quality="audio",
            format=audio_ext,
            size=_pick_size(best_audio),
            format_id=FORMAT_SELECTORS["audio"],
            has_audio=True,
            has_video=False,
        )
    )
    return result


def selector_for_quality(quality: str) -> str:
    """Map Cliperry quality label to a yt-dlp format selector."""
    key = quality.strip().lower()
    aliases = {
        "1080": "1080p",
        "720": "720p",
        "480": "480p",
        "best": "1080p",
        "mp3": "audio",
        "m4a": "audio",
    }
    key = aliases.get(key, key)
    if key not in FORMAT_SELECTORS:
        raise ValueError(f"Unsupported quality: {quality}")
    return FORMAT_SELECTORS[key]
