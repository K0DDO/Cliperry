"""HTTP client for the Cliperry backend API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

import httpx

logger = logging.getLogger("cliperry.bot.api")


def device_id_for_telegram(telegram_id: int) -> str:
    """Stable anonymous device UUID derived from Telegram user id."""
    return str(uuid5(NAMESPACE_URL, f"cliperry:telegram:{telegram_id}"))


class BackendClient:
    """Thin async client around Cliperry REST API."""

    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-Client-Type": "telegram"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self, telegram_id: int) -> dict[str, str]:
        return {"X-Device-Id": device_id_for_telegram(telegram_id)}

    async def analyze(self, telegram_id: int, url: str) -> dict[str, Any]:
        response = await self._client.post(
            "/api/analyze",
            json={"url": url},
            headers=self._headers(telegram_id),
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
            headers=self._headers(telegram_id),
        )
        return self._parse(response)

    async def get_task(self, telegram_id: int, task_id: str | UUID) -> dict[str, Any]:
        response = await self._client.get(
            f"/api/tasks/{task_id}",
            headers=self._headers(telegram_id),
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
            headers=self._headers(telegram_id),
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
        if isinstance(data, dict):
            message = str(data.get("message") or data.get("detail") or message)
        raise BackendAPIError(message=message, status_code=response.status_code, payload=data)


class BackendAPIError(Exception):
    def __init__(self, message: str, status_code: int, payload: Any = None) -> None:
        self.message = message
        self.status_code = status_code
        self.payload = payload
        super().__init__(message)
