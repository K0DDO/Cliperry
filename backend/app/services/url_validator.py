"""URL validation, adult-site blocklist, and SSRF hardening."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from app.errors import blocked_platform, invalid_url

# Explicit deny-list — never support adult platforms
ADULT_DOMAIN_BLOCKLIST: frozenset[str] = frozenset(
    {
        "pornhub.com",
        "www.pornhub.com",
        "xvideos.com",
        "www.xvideos.com",
        "xnxx.com",
        "www.xnxx.com",
        "xhamster.com",
        "www.xhamster.com",
        "onlyfans.com",
        "www.onlyfans.com",
        "redtube.com",
        "www.redtube.com",
        "youporn.com",
        "www.youporn.com",
        "spankbang.com",
        "www.spankbang.com",
    }
)

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
    }
)

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    """Strip whitespace from the URL."""
    return url.strip()


def extract_host(url: str) -> str:
    """Return lowercase hostname without port."""
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def is_blocked_domain(url: str) -> bool:
    """Check whether the URL belongs to a blocked adult domain."""
    host = extract_host(url)
    if not host:
        return False
    if host in ADULT_DOMAIN_BLOCKLIST:
        return True
    return any(host.endswith(f".{blocked}") for blocked in ADULT_DOMAIN_BLOCKLIST)


def is_unsafe_host(hostname: str) -> bool:
    """
    Reject hosts that are likely SSRF / local network targets.

    Blocks loopback, private, link-local, multicast, and metadata-style names.
    """
    host = (hostname or "").strip().lower().rstrip(".")
    if not host:
        return True
    if host in _BLOCKED_HOSTNAMES:
        return True
    if host.endswith(".local") or host.endswith(".internal") or host.endswith(".localhost"):
        return True

    # IPv4 / IPv6 literals
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        return bool(
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or ip.packed[:2] == b"\xa9\xfe"  # 169.254/16 already link-local
            or str(ip) == "169.254.169.254"
        )

    # Hostname must look like a public DNS name (has a dot, valid labels).
    if not _HOSTNAME_RE.match(host):
        return True

    return False


def validate_media_url(url: str) -> str:
    """
    Validate and normalize a media URL.

    Raises:
        AppError: on invalid / blocked URLs.
    """
    cleaned = normalize_url(url)

    if not cleaned:
        raise invalid_url("Укажите ссылку на видео.")

    if len(cleaned) > MAX_URL_LENGTH:
        raise invalid_url(
            f"Ссылка слишком длинная (максимум {MAX_URL_LENGTH} символов).",
            max_length=MAX_URL_LENGTH,
        )

    if any(ch.isspace() for ch in cleaned):
        raise invalid_url("Ссылка не должна содержать пробелы.")

    parsed = urlparse(cleaned)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise invalid_url(
            "Ссылка должна начинаться с http:// или https://.",
            scheme=parsed.scheme or None,
        )

    if parsed.username or parsed.password:
        raise invalid_url("Ссылка не должна содержать логин или пароль.")

    if not parsed.hostname:
        raise invalid_url("В ссылке должен быть корректный домен (например youtube.com).")

    if is_unsafe_host(parsed.hostname):
        raise invalid_url("Этот адрес нельзя использовать для загрузки.")

    if is_blocked_domain(cleaned):
        raise blocked_platform()

    return cleaned
