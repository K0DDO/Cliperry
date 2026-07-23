"""Careful in-place Telegram progress message updates."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

from app.bot import texts
from app.bot.api_client import BackendAPIError, BackendClient

logger = logging.getLogger("cliperry.bot.progress")


class ProgressTracker:
    """
    Polls task status and edits ONE Telegram message in place.

    Rules:
    - never spam new messages
    - edit only when visible content changed
    - throttle edits (Telegram rate limits)
    - ignore "message is not modified" errors
    """

    def __init__(
        self,
        *,
        api: BackendClient,
        telegram_id: int,
        message: Message,
        quality: str,
        title: str | None = None,
        poll_interval: float = 2.0,
        min_edit_interval: float = 1.5,
        max_wait_seconds: float = 240.0,
    ) -> None:
        self.api = api
        self.telegram_id = telegram_id
        self.message = message
        self.quality = quality
        self.title = title
        self.poll_interval = poll_interval
        self.min_edit_interval = min_edit_interval
        self.max_wait_seconds = max_wait_seconds

        self._last_text: str | None = None
        self._last_edit_at = 0.0
        self._last_progress = -1

    async def start_card(self) -> None:
        """Render the initial progress card (or replace existing text carefully)."""
        await self._safe_edit(
            texts.format_download_progress(
                quality=self.quality,
                progress=0,
                title=self.title,
            ),
            force=True,
        )

    async def watch(self, task_id: str) -> dict[str, Any]:
        """
        Follow task until completed/failed/timeout.

        Returns final task payload-like dict with at least ``status``.
        """
        deadline = time.monotonic() + self.max_wait_seconds
        last_task: dict[str, Any] = {"status": "queued", "progress": 0}

        while time.monotonic() < deadline:
            await asyncio.sleep(self.poll_interval)
            try:
                task = await self.api.get_task(self.telegram_id, task_id)
            except BackendAPIError as exc:
                return {
                    "status": "failed",
                    "error_message": exc.message,
                    "progress": last_task.get("progress", 0),
                }

            last_task = task
            status = task.get("status") or "processing"
            progress = int(task.get("progress") or 0)

            # Skip noisy tiny updates (same percent + same meta)
            body = texts.format_download_progress(
                quality=self.quality,
                progress=progress,
                size=task.get("size"),
                speed=task.get("speed"),
                eta=task.get("eta"),
                title=self.title,
            )
            await self._safe_edit(body)

            if status == "completed":
                # Ensure 100% shown once before final message
                if progress < 100:
                    await self._safe_edit(
                        texts.format_download_progress(
                            quality=self.quality,
                            progress=100,
                            size=task.get("size"),
                            speed=task.get("speed"),
                            eta="0s",
                            title=self.title,
                        ),
                        force=True,
                    )
                return task
            if status == "failed":
                return task

        return {
            **last_task,
            "status": "failed",
            "error_message": last_task.get("error_message") or "Превышено время ожидания",
        }

    async def _safe_edit(self, text: str, *, force: bool = False) -> None:
        """Edit the same message if content changed and throttle allows."""
        if not force and text == self._last_text:
            return

        now = time.monotonic()
        if not force and (now - self._last_edit_at) < self.min_edit_interval:
            return

        try:
            await self.message.edit_text(text, parse_mode="HTML")
            self._last_text = text
            self._last_edit_at = time.monotonic()
        except TelegramRetryAfter as exc:
            logger.warning("telegram_retry_after seconds=%s", exc.retry_after)
            await asyncio.sleep(float(exc.retry_after) + 0.1)
            try:
                await self.message.edit_text(text, parse_mode="HTML")
                self._last_text = text
                self._last_edit_at = time.monotonic()
            except Exception:  # noqa: BLE001
                logger.debug("progress_edit_retry_failed", exc_info=True)
        except TelegramBadRequest as exc:
            # Typical: "message is not modified"
            if "not modified" in str(exc).lower():
                self._last_text = text
                return
            logger.debug("progress_edit_bad_request: %s", exc)
        except Exception:  # noqa: BLE001
            logger.debug("progress_edit_failed", exc_info=True)
