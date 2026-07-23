"""Async wrappers around yt-dlp (runs sync extract/download in a thread)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import yt_dlp

from app.config import get_settings

logger = logging.getLogger("cliperry.ytdlp")


class YtDlpError(Exception):
    """Raised when yt-dlp extraction or download fails."""


def _auth_opts() -> dict[str, Any]:
    """Optional cookies / proxy from settings (helps with YouTube bot checks)."""
    settings = get_settings()
    opts: dict[str, Any] = {}
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = settings.ytdlp_cookies_file
    elif settings.ytdlp_cookies_from_browser:
        # e.g. "chrome", "firefox", "edge"
        opts["cookiesfrombrowser"] = (settings.ytdlp_cookies_from_browser,)
    if settings.ytdlp_proxy:
        opts["proxy"] = settings.ytdlp_proxy
    return opts


def _default_opts(**extra: Any) -> dict[str, Any]:
    settings = get_settings()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
        "noplaylist": True,
        "cachedir": False,
        "retries": 3,
        "max_filesize": settings.download_max_filesize_bytes,
    }
    opts.update(_auth_opts())
    opts.update(extra)
    return opts


def extract_info_sync(url: str, *, flat: bool = False) -> dict[str, Any]:
    """
    Extract metadata without downloading media.

    Args:
        url: Media or playlist URL.
        flat: If True, use extract_flat for playlist entries (fast, no per-video formats).
    """
    opts = _default_opts(
        skip_download=True,
        extract_flat="in_playlist" if flat else False,
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise YtDlpError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise YtDlpError(f"yt-dlp extract failed: {exc}") from exc

    if not info:
        raise YtDlpError("yt-dlp returned empty metadata")
    return info


def download_sync(
    url: str,
    *,
    output_template: str,
    format_selector: str,
    progress_hook: Any | None = None,
) -> str:
    """
    Download a single media file into a temporary path template.

    Returns:
        Absolute path of the downloaded file.
    """
    from pathlib import Path

    settings = get_settings()
    max_bytes = settings.download_max_filesize_bytes

    # Preflight: reject huge files before writing to disk.
    try:
        meta = extract_info_sync(url, flat=False)
    except YtDlpError:
        meta = None
    if isinstance(meta, dict):
        filesize = meta.get("filesize") or meta.get("filesize_approx")
        if filesize and int(filesize) > max_bytes:
            raise YtDlpError(
                f"File too large ({int(filesize)} bytes > {max_bytes} limit)"
            )

    opts = _default_opts(
        format=format_selector,
        outtmpl=output_template,
        noplaylist=True,
        merge_output_format="mp4",
        max_filesize=max_bytes,
    )
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise YtDlpError("yt-dlp download returned empty info")
            path = ydl.prepare_filename(info)
            candidate = Path(path)
            if not candidate.exists():
                stem = candidate.with_suffix("")
                for ext in (".mp4", ".mkv", ".webm", ".m4a", ".opus"):
                    alt = Path(str(stem) + ext)
                    if alt.exists():
                        return str(alt.resolve())
                raise YtDlpError(f"Downloaded file not found near {path}")
            # Post-check in case approx was missing
            size = candidate.stat().st_size
            if size > max_bytes:
                candidate.unlink(missing_ok=True)
                raise YtDlpError(f"Downloaded file exceeds size limit ({max_bytes})")
            return str(candidate.resolve())
    except YtDlpError:
        raise
    except yt_dlp.utils.DownloadError as exc:
        raise YtDlpError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise YtDlpError(f"yt-dlp download failed: {exc}") from exc


async def extract_info(url: str, *, flat: bool = False) -> dict[str, Any]:
    """Async extract_info (thread offload)."""
    return await asyncio.to_thread(extract_info_sync, url, flat=flat)


async def download(
    url: str,
    *,
    output_template: str,
    format_selector: str,
    progress_hook: Any | None = None,
) -> str:
    """Async download (thread offload)."""
    return await asyncio.to_thread(
        download_sync,
        url,
        output_template=output_template,
        format_selector=format_selector,
        progress_hook=progress_hook,
    )
