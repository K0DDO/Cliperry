"""Inline callback handlers — quality selection and download progress."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from app.bot import texts
from app.bot.api_client import BackendAPIError, BackendClient
from app.bot.progress import ProgressTracker
from app.config import get_settings

logger = logging.getLogger("cliperry.bot.callbacks")

router = Router(name="callbacks")


@router.callback_query(F.data.startswith("cancel:"))
async def on_cancel(callback: CallbackQuery, store) -> None:
    if not callback.data:
        await callback.answer()
        return
    pending_id = callback.data.split(":", 1)[1]
    await store.delete_pending(pending_id)
    await callback.answer("Отменено")
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass


@router.callback_query(F.data.startswith("dl:"))
async def on_download(
    callback: CallbackQuery,
    api: BackendClient,
    store,
    bot: Bot,
) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        await callback.answer("Ошибка", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    _, pending_id, quality = parts
    pending = await store.get_pending(pending_id)
    if not pending:
        await callback.answer("Сессия устарела — пришлите ссылку снова", show_alert=True)
        return

    if pending.get("user_id") != callback.from_user.id:
        await callback.answer("Это не ваша кнопка", show_alert=True)
        return

    await callback.answer(f"Скачиваю {quality}…")

    progress_msg = await callback.message.answer(
        texts.format_download_progress(
            quality=quality,
            progress=0,
            title=pending.get("title"),
        ),
        parse_mode="HTML",
    )

    tracker = ProgressTracker(
        api=api,
        telegram_id=callback.from_user.id,
        message=progress_msg,
        quality=quality,
        title=pending.get("title"),
    )

    try:
        created = await api.download(
            callback.from_user.id,
            url=pending["url"],
            quality=quality,
            title=pending.get("title"),
            platform=pending.get("platform"),
        )
    except BackendAPIError as exc:
        await progress_msg.edit_text(
            texts.DOWNLOAD_FAILED.format(reason=exc.message),
            parse_mode="HTML",
        )
        return
    except Exception:  # noqa: BLE001
        logger.exception("download_enqueue_failed")
        await progress_msg.edit_text(
            texts.DOWNLOAD_FAILED.format(reason="Сервер недоступен"),
            parse_mode="HTML",
        )
        return

    task_id = str(created.get("task_id"))
    await store.push_history(
        callback.from_user.id,
        {
            "title": pending.get("title") or "Видео",
            "quality": quality,
            "status": "queued",
            "task_id": task_id,
        },
    )

    result = await tracker.watch(task_id)
    final_status = result.get("status") or "failed"

    await store.push_history(
        callback.from_user.id,
        {
            "title": pending.get("title") or "Видео",
            "quality": quality,
            "status": final_status,
            "task_id": task_id,
        },
    )
    await store.delete_pending(pending_id)

    if final_status == "completed":
        download_url = result.get("download_url")
        link = "Файл на сервере подготовлен."
        href = None
        if download_url:
            href = str(download_url)
            if href.startswith("/"):
                href = f"{get_settings().backend_public_url.rstrip('/')}{href}"
            safe_href = href.replace('"', "%22")
            link = f'<a href="{safe_href}">Скачать файл</a>'
        await progress_msg.edit_text(
            texts.DOWNLOAD_DONE.format(quality=quality, link=link),
            parse_mode="HTML",
        )
        if href:
            try:
                await _send_file_to_chat(
                    bot,
                    chat_id=callback.message.chat.id,
                    href=href,
                    title=pending.get("title") or "video",
                )
            except Exception:  # noqa: BLE001
                logger.exception("telegram_send_document_failed task_id=%s", task_id)
    else:
        reason = result.get("error_message") or "Ошибка загрузки"
        await progress_msg.edit_text(
            texts.DOWNLOAD_FAILED.format(reason=reason),
            parse_mode="HTML",
        )


async def _send_file_to_chat(bot: Bot, *, chat_id: int, href: str, title: str) -> None:
    """Fetch completed artifact via internal API and upload to Telegram."""
    settings = get_settings()
    fetch_url = href
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    token = (qs.get("token") or [None])[0]
    path = parsed.path or ""
    if token and "/api/files/" in path:
        task_part = path.rstrip("/").split("/")[-1]
        internal = settings.backend_api_base_url.rstrip("/")
        fetch_url = f"{internal}/api/files/{task_part}?token={token}"

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(fetch_url)
        response.raise_for_status()
        data = response.content

    if not data:
        raise RuntimeError("empty file")

    if len(data) > 48 * 1024 * 1024:
        logger.warning("file_too_large_for_telegram bytes=%s", len(data))
        return

    suffix = Path(path).suffix or ".mp4"
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)[:80]
    filename = f"{safe_name or 'video'}{suffix if suffix.startswith('.') else '.mp4'}"
    await bot.send_document(
        chat_id=chat_id,
        document=BufferedInputFile(data, filename=filename),
        caption=f"🍓 {title}"[:1024],
    )
