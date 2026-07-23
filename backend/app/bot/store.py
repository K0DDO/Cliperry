"""Redis-backed pending analyzes + lightweight bot preferences/history."""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as redis


class BotStore:
    """Short-lived pending downloads and per-user preferences."""

    def __init__(self, redis_url: str) -> None:
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    async def aclose(self) -> None:
        await self._redis.aclose()

    async def save_pending(self, payload: dict[str, Any], ttl: int = 1800) -> str:
        pending_id = uuid.uuid4().hex
        key = f"bot:pending:{pending_id}"
        await self._redis.set(key, json.dumps(payload, ensure_ascii=False), ex=ttl)
        return pending_id

    async def get_pending(self, pending_id: str) -> dict[str, Any] | None:
        raw = await self._redis.get(f"bot:pending:{pending_id}")
        if not raw:
            return None
        return json.loads(raw)

    async def delete_pending(self, pending_id: str) -> None:
        await self._redis.delete(f"bot:pending:{pending_id}")

    async def get_default_quality(self, telegram_id: int) -> str:
        value = await self._redis.get(f"bot:settings:{telegram_id}:quality")
        return value or "1080p"

    async def set_default_quality(self, telegram_id: int, quality: str) -> None:
        await self._redis.set(f"bot:settings:{telegram_id}:quality", quality)

    async def push_history(self, telegram_id: int, item: dict[str, Any]) -> None:
        key = f"bot:history:{telegram_id}"
        await self._redis.lpush(key, json.dumps(item, ensure_ascii=False))
        await self._redis.ltrim(key, 0, 19)
        await self._redis.expire(key, 60 * 60 * 24 * 30)

    async def get_history(self, telegram_id: int) -> list[dict[str, Any]]:
        key = f"bot:history:{telegram_id}"
        rows = await self._redis.lrange(key, 0, 9)
        return [json.loads(row) for row in rows]
