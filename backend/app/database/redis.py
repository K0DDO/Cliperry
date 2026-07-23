"""Redis client lifecycle helpers."""

from __future__ import annotations

from redis.asyncio import Redis

from app.config import get_settings

_redis: Redis | None = None


async def init_redis() -> Redis:
    """Create the global async Redis client."""
    global _redis
    settings = get_settings()
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    return _redis


async def close_redis() -> None:
    """Close the global Redis client."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    """Return the initialized Redis client."""
    if _redis is None:
        raise RuntimeError("Redis is not initialized")
    return _redis


async def redis_ping() -> bool:
    """Health-check Redis connectivity."""
    try:
        client = get_redis()
        return bool(await client.ping())
    except Exception:
        return False
