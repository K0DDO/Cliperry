"""Compatibility registry wrapping ParserFactory."""

from __future__ import annotations

from app.parsers.base import BaseParser
from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.factory import ParserFactory, get_parser_factory


class ParserRegistry:
    """
    Thin adapter over ``ParserFactory`` for callers that resolve by URL.

    Prefer ``ParserFactory`` for new code.
    """

    def __init__(self, factory: ParserFactory | None = None) -> None:
        self._factory = factory or get_parser_factory()

    def register(self, parser: BaseParser) -> None:
        """Register a parser instance's class with the underlying factory."""
        self._factory.register(type(parser))

    def resolve(self, url: str) -> BaseParser | None:
        """Return a matching parser, or None if unsupported."""
        try:
            return self._factory.get_parser(url)
        except UnsupportedPlatformError:
            return None

    def list_platforms(self) -> list[str]:
        return self._factory.list_platforms()

    def clear(self) -> None:
        """Reset factory to an empty parser list (tests only)."""
        self._factory._parser_classes.clear()
        self._factory._instances.clear()


parser_registry = ParserRegistry()


def get_parser_registry() -> ParserRegistry:
    """Return the shared registry adapter."""
    return parser_registry
