"""Parser-specific exceptions."""

from __future__ import annotations


class ParserError(Exception):
    """Base error for the parser layer."""


class UnsupportedPlatformError(ParserError):
    """Raised when no parser matches the URL."""

    def __init__(self, url: str, supported: list[str] | None = None) -> None:
        self.url = url
        self.supported = supported or []
        platforms = ", ".join(self.supported) if self.supported else "none"
        super().__init__(f"Unsupported platform for URL: {url} (supported: {platforms})")


class ParserNotImplementedError(ParserError):
    """Raised by stub parsers until yt-dlp integration lands."""

    def __init__(self, platform: str, method: str) -> None:
        self.platform = platform
        self.method = method
        super().__init__(
            f"{platform} parser.{method}() is not implemented yet "
            "(stub class — wire yt-dlp in the next phase)"
        )
