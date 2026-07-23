"""Startup environment / configuration validation."""

from __future__ import annotations

import logging
import warnings

from app.config import Settings

logger = logging.getLogger("cliperry.security")

_INSECURE_SECRET_DEFAULTS = frozenset(
    {
        "change-me-in-production",
        "change-me",
        "secret",
        "password",
        "changeme",
    }
)

_INSECURE_ADMIN_PASSWORDS = frozenset(
    {
        "change-me",
        "admin",
        "password",
        "123456",
        "changeme",
    }
)


class InsecureConfigurationError(RuntimeError):
    """Raised when production settings are unsafe."""


def validate_settings(settings: Settings, *, strict: bool | None = None) -> list[str]:
    """
    Validate security-sensitive settings.

    Returns a list of warning messages. Raises ``InsecureConfigurationError``
    when ``strict`` is true (defaults to production).
    """
    if strict is None:
        strict = settings.is_production

    problems: list[str] = []

    secret = settings.secret_key.strip()
    if len(secret) < 32:
        problems.append("SECRET_KEY must be at least 32 characters")
    if secret.lower() in _INSECURE_SECRET_DEFAULTS:
        problems.append("SECRET_KEY is a known insecure default")

    if settings.admin_password.strip().lower() in _INSECURE_ADMIN_PASSWORDS:
        problems.append("ADMIN_PASSWORD is a known insecure default")
    if len(settings.admin_password) < 12 and settings.is_production:
        problems.append("ADMIN_PASSWORD must be at least 12 characters in production")

    if settings.is_production and settings.debug:
        problems.append("DEBUG must be false in production")

    if settings.is_production and settings.trusted_host_list == ["*"]:
        problems.append("TRUSTED_HOSTS must not be '*' in production")

    if settings.is_production and settings.enable_worker_test:
        problems.append("ENABLE_WORKER_TEST must be false in production")

    if strict and problems:
        joined = "; ".join(problems)
        raise InsecureConfigurationError(
            f"Refusing to start with insecure configuration: {joined}"
        )

    for item in problems:
        if settings.is_production:
            logger.error("insecure_config %s", item)
        else:
            logger.warning("insecure_config %s", item)
            warnings.warn(item, stacklevel=2)

    return problems


def cors_extension_origin_regex(settings: Settings) -> str | None:
    """
    Build CORS regex for Chrome extensions.

    If ``CORS_EXTENSION_IDS`` is set, only those origins are allowed.
    Otherwise development keeps a broad chrome-extension regex.
    """
    ids = [item.strip() for item in settings.cors_extension_ids.split(",") if item.strip()]
    if ids:
        escaped = [item.replace(".", r"\.").replace("-", r"\-") for item in ids]
        # Accept full origins or bare extension ids.
        parts: list[str] = []
        for value in escaped:
            if value.startswith(r"chrome\-extension://"):
                parts.append(f"^{value}$")
            else:
                parts.append(f"^chrome\\-extension://{value}$")
        return "(?:" + "|".join(parts) + ")"

    if settings.is_production:
        # Fail closed: no wildcard extension CORS in production without explicit IDs.
        return None

    return r"^chrome-extension://.*$"
