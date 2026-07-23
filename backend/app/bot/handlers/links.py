"""URL message handler — analyze via backend and show quality buttons."""

from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.types import Message, URLInputFile

from app.bot import texts
from app.bot.api_client import BackendAPIError, BackendClient
from app.bot.keyboards import main_menu_keyboard, quality_keyboard

logger = logging.getLogger("cliperry.bot.links")

router = Router(name="links")

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def extract_url(text: str) -> str | None:
    match = URL_RE.search(text or "")
    return match.group(0).rstrip(").,]}>") if match else None


@router.message(F.text.func(lambda t: bool(t and extract_url(t))))
async def on_link(message: Message, api: BackendClient, store) -> None:
    assert message.from_user and message.text
    url = extract_url(message.text)
    if not url:
        await message.answer(texts.ASK_LINK)
        return

    status = await message.answer(texts.ANALYZING)

    try:
        data = await api.analyze(message.from_user.id, url)
    except BackendAPIError as exc:
        await status.edit_text(f"❌ {exc.message}")
        return
    except Exception:  # noqa: BLE001
        logger.exception("analyze_failed")
        await status.edit_text("❌ Не удалось связаться с сервером. Попробуйте позже.")
        return

    if data.get("is_playlist"):
        count = data.get("playlist_count") or len(data.get("entries") or [])
        title = texts._escape(data.get("title") or "Плейлист")
        await status.edit_text(
            f"📂 <b>{title}</b>\n"
            f"Видео: <b>{count}</b>\n\n"
            "Пока скачивание плейлистов целиком в боте ограничено.\n"
            "Пришлите ссылку на одно видео из списка.",
            parse_mode="HTML",
        )
        return

    formats = data.get("formats") or []
    default_quality = await store.get_default_quality(message.from_user.id)
    pending_id = await store.save_pending(
        {
            "url": data.get("url") or url,
            "title": data.get("title"),
            "platform": data.get("platform"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats,
            "user_id": message.from_user.id,
        }
    )

    caption = texts.format_analyze_caption(
        title=data.get("title") or "Без названия",
        platform=data.get("platform") or "unknown",
        author=data.get("author"),
        duration=data.get("duration"),
        is_playlist=False,
        playlist_count=None,
    )
    keyboard = quality_keyboard(
        pending_id,
        formats,
        default_quality=default_quality,
    )

    thumbnail = data.get("thumbnail")
    try:
        if thumbnail:
            await message.answer_photo(
                photo=URLInputFile(thumbnail),
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            await status.delete()
        else:
            await status.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception:  # noqa: BLE001
        logger.exception("send_preview_failed")
        await status.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text)
async def on_plain_text(message: Message) -> None:
    """Gentle nudge when user sends text without a URL."""
    if message.text and message.text.startswith("/"):
        return
    await message.answer(texts.ASK_LINK, reply_markup=main_menu_keyboard())
