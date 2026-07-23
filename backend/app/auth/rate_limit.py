"""Redis-backed fixed-window rate limiting."""

from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis

from app.config import Settings
from app.errors import rate_limited

# Atomic INCR + EXPIRE (fixed window). Prevents orphan keys without TTL.
_INCR_EXPIRE_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
else
  local ttl = redis.call('TTL', KEYS[1])
  if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
  end
end
return current
"""


class RateLimiter:
    """Fixed-window counter in Redis."""

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int | None = None,
    ) -> None:
        """Increment counter and raise 429 when over limit."""
        window = window_seconds or self.settings.rate_limit_window_seconds
        redis_key = f"rl:{key}"
        current = int(
            await self.redis.eval(_INCR_EXPIRE_LUA, 1, redis_key, str(window))
        )
        if current > limit:
            ttl = await self.redis.ttl(redis_key)
            raise rate_limited(retry_after=max(int(ttl), 1))


def client_ip(request: Request, *, trust_proxy: bool = False) -> str:
    """
    Extract client IP.

    ``X-Forwarded-For`` is only trusted when ``trust_proxy`` is enabled
    (reverse proxy / load balancer deployments). Prefer the rightmost
    untrusted hop — leftmost values are client-spoofable.
    """
    if trust_proxy:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                # Rightmost entry is typically added by the nearest proxy.
                return parts[-1]
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit_key(request: Request, action: str, *, trust_proxy: bool = False) -> str:
    """Compose a rate-limit key from device + IP + action."""
    device_id = getattr(request.state, "device_id", None) or "anon"
    return f"{action}:{device_id}:{client_ip(request, trust_proxy=trust_proxy)}"


async def check_rate_limit(
    redis: Redis,
    settings: Settings,
    request: Request,
    *,
    action: str,
    limit: int,
) -> None:
    """
    Enforce per-action and global-per-IP limits.

    Global IP limit reduces anonymous UUID bucket churn abuse.
    """
    limiter = RateLimiter(redis, settings)
    trust = settings.trust_proxy_headers
    ip = client_ip(request, trust_proxy=trust)

    await limiter.check(
        key=f"ip:{ip}",
        limit=settings.rate_limit_ip_global,
    )
    await limiter.check(
        key=rate_limit_key(request, action, trust_proxy=trust),
        limit=limit,
    )
