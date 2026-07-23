"""Shared DTOs and abstract parser contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class MediaFormat:
    """Normalized format option returned by parsers."""

    quality: str
    format: str
    size: str | None = None
    format_id: str | None = None
    has_audio: bool = True
    has_video: bool = True


@dataclass(slots=True)
class PlaylistEntry:
    """Single item inside a playlist analysis result."""

    id: str
    title: str
    thumbnail: str | None = None
    url: str | None = None
    duration: str | None = None
    index: int | None = None


@dataclass(slots=True)
class MediaInfo:
    """Normalized metadata returned by ``analyze``."""

    title: str
    platform: str
    url: str
    thumbnail: str | None = None
    duration: str | None = None
    author: str | None = None
    is_playlist: bool = False
    playlist_count: int | None = None
    formats: list[MediaFormat] = field(default_factory=list)
    entries: list[PlaylistEntry] = field(default_factory=list)


class BaseParser(ABC):
    """
    Platform parser contract.

    Concrete parsers declare ``platform`` + ``domains`` and implement
    ``analyze`` / ``get_formats`` / ``download``. The API never imports
    platform classes directly — it goes through ``ParserFactory``.
    """

    platform: str = "unknown"
    domains: tuple[str, ...] = ()

    def matches(self, url: str) -> bool:
        """Return True if this parser handles the given URL."""
        host = _extract_host(url)
        if not host:
            return False
        return any(host == domain or host.endswith(f".{domain}") for domain in self.domains)

    @abstractmethod
    async def analyze(self, url: str) -> MediaInfo:
        """Fetch metadata and available formats for a URL."""

    @abstractmethod
    async def get_formats(self, url: str) -> list[MediaFormat]:
        """Return available download formats for a URL."""

    @abstractmethod
    async def download(self, url: str, quality: str) -> str:
        """
        Download media at the requested quality into temporary storage.

        Returns:
            Absolute path to the temporary file (TTL-managed, not permanent).
        """


def _extract_host(url: str) -> str:
    """Return lowercase hostname without port."""
    from urllib.parse import urlparse

    return (urlparse(url).hostname or "").lower()
