"""HTTP client for the Cliperry backend API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
import redis.asyncio as redis

logger = logging.getLogger("cliperry.bot.api")


class BackendClient:
    """Thin async client around Cliperry REST API."""

    def __init__(self, base_url: str, redis_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-Client-Type": "telegram"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._redis.aclose()

    async def device_id_for_telegram(self, telegram_id: int) -> str:
        """
        Random persistent device id for a Telegram user.

        Stored in Redis so it is not derivable from the public telegram_id
        (avoids predictable UUID5 IDOR on history/tasks).
        """
        key = f"bot:device:{telegram_id}"
        existing = await self._redis.get(key)
        if existing:
            return existing
        new_id = str(uuid4())
        created = await self._redis.set(key, new_id, nx=True)
        if not created:
            again = await self._redis.get(key)
            return again or new_id
        return new_id

    async def _headers(self, telegram_id: int) -> dict[str, str]:
        return {"X-Device-Id": await self.device_id_for_telegram(telegram_id)}

    async def analyze(self, telegram_id: int, url: str) -> dict[str, Any]:
        response = await self._client.post(
            "/api/analyze",
            json={"url": url},
            headers=await self._headers(telegram_id),
        )
        return self._parse(response)

    async def download(
        self,
        telegram_id: int,
        *,
        url: str,
        quality: str,
        title: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url, "quality": quality}
        if title:
            payload["title"] = title
        if platform:
            payload["platform"] = platform
        response = await self._client.post(
            "/api/download",
            json=payload,
            headers=await self._headers(telegram_id),
        )
        return self._parse(response)

    async def get_task(self, telegram_id: int, task_id: str | UUID) -> dict[str, Any]:
        response = await self._client.get(
            f"/api/tasks/{task_id}",
            headers=await self._headers(telegram_id),
        )
        return self._parse(response)

    async def get_history(
        self,
        telegram_id: int,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        response = await self._client.get(
            "/api/history",
            params={"page": page, "page_size": page_size},
            headers=await self._headers(telegram_id),
        )
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except Exception:
            data = {"message": response.text}

        if response.is_success:
            return data if isinstance(data, dict) else {"data": data}

        message = "Ошибка сервера"
        code = None
        if isinstance(data, dict):
            message = str(data.get("message") or data.get("detail") or message)
            code = data.get("code")
        raise BackendAPIError(
            message=message,
            status_code=response.status_code,
            payload=data,
            code=str(code) if code else None,
        )


class BackendAPIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int,
        payload: Any = None,
        code: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.payload = payload
        self.code = code
        super().__init__(message)
