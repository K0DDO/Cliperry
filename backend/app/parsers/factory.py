"""ParserFactory — resolve a BaseParser from a media URL."""

from __future__ import annotations

from app.parsers.base import BaseParser
from app.parsers.exceptions import UnsupportedPlatformError
from app.parsers.youtube import YoutubeParser


class ParserFactory:
    """
    Maps hostnames to parser classes.

    Adding a platform:
      1. Subclass ``BaseParser``
      2. Register it in ``_DEFAULT_PARSERS`` (or call ``register``)
    """

    _DEFAULT_PARSERS: tuple[type[BaseParser], ...] = (
        YoutubeParser,
        # TikTok / Instagram / Twitter stubs stay in codebase but are not
        # registered until implemented — soft-launch is YouTube-only.
    )

    def __init__(self, parsers: list[type[BaseParser]] | None = None) -> None:
        self._parser_classes: list[type[BaseParser]] = list(
            parsers if parsers is not None else self._DEFAULT_PARSERS
        )
        # Cache one instance per class — parsers are stateless stubs for now
        self._instances: dict[type[BaseParser], BaseParser] = {}

    def register(self, parser_cls: type[BaseParser]) -> None:
        """Register an additional parser class (e.g. VK later)."""
        if parser_cls not in self._parser_classes:
            self._parser_classes.append(parser_cls)

    def get_parser(self, url: str) -> BaseParser:
        """
        Return a parser instance for the URL.

        Raises:
            UnsupportedPlatformError: if no registered parser matches.
        """
        for parser_cls in self._parser_classes:
            parser = self._get_instance(parser_cls)
            if parser.matches(url):
                return parser

        raise UnsupportedPlatformError(url, supported=self.list_platforms())

    def detect_platform(self, url: str) -> str | None:
        """Return platform name for the URL, or None if unsupported."""
        try:
            return self.get_parser(url).platform
        except UnsupportedPlatformError:
            return None

    def list_platforms(self) -> list[str]:
        """Return registered platform identifiers."""
        return [cls.platform for cls in self._parser_classes]

    def list_domains(self) -> list[str]:
        """Return all domains handled by registered parsers."""
        domains: list[str] = []
        for cls in self._parser_classes:
            domains.extend(cls.domains)
        return domains

    def _get_instance(self, parser_cls: type[BaseParser]) -> BaseParser:
        if parser_cls not in self._instances:
            self._instances[parser_cls] = parser_cls()
        return self._instances[parser_cls]


# Process-wide factory used by services
parser_factory = ParserFactory()


def get_parser_factory() -> ParserFactory:
    """Return the shared ParserFactory singleton."""
    return parser_factory
