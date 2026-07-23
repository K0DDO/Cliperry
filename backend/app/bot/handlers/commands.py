"""Command handlers: /start /help /history /settings."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.api_client import BackendAPIError, BackendClient
from app.bot.keyboards import history_keyboard, main_menu_keyboard, settings_keyboard
from app.bot import texts

router = Router(name="commands")

HISTORY_PAGE_SIZE = 10


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        texts.WELCOME,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(F.text == "📖 Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def cmd_history(message: Message, api: BackendClient) -> None:
    assert message.from_user
    await _send_history(message, api, message.from_user.id, page=1)


@router.callback_query(F.data.startswith("history:"))
async def on_history_page(callback: CallbackQuery, api: BackendClient) -> None:
    assert callback.from_user and callback.data
    try:
        page = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректная страница")
        return

    if page < 1:
        await callback.answer()
        return

    try:
        data = await api.get_history(
            callback.from_user.id,
            page=page,
            page_size=HISTORY_PAGE_SIZE,
        )
    except BackendAPIError as exc:
        await callback.answer(exc.message[:180], show_alert=True)
        return

    text = texts.format_history(
        data.get("items") or [],
        page=int(data.get("page") or page),
        total_pages=int(data.get("total_pages") or 0),
        total=int(data.get("total") or 0),
    )
    kb = history_keyboard(
        page=int(data.get("page") or page),
        has_prev=bool(data.get("has_prev")),
        has_next=bool(data.get("has_next")),
    )
    if callback.message:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, store) -> None:
    assert message.from_user
    quality = await store.get_default_quality(message.from_user.id)
    await message.answer(
        texts.SETTINGS_TITLE.format(quality=quality),
        reply_markup=settings_keyboard(quality),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_quality:"))
async def on_set_quality(callback: CallbackQuery, store) -> None:
    if not callback.from_user or not callback.data:
        await callback.answer()
        return
    quality = callback.data.split(":", 1)[1]
    allowed = {"1080p", "720p", "480p", "360p", "audio", "best"}
    if quality not in allowed:
        await callback.answer("Некорректное качество", show_alert=True)
        return
    await store.set_default_quality(callback.from_user.id, quality)
    await callback.answer(f"Сохранено: {quality}")
    if callback.message:
        await callback.message.edit_text(
            texts.SETTINGS_TITLE.format(quality=quality),
            reply_markup=settings_keyboard(quality),
            parse_mode="HTML",
        )


async def _send_history(
    message: Message,
    api: BackendClient,
    telegram_id: int,
    *,
    page: int,
) -> None:
    try:
        data = await api.get_history(
            telegram_id,
            page=page,
            page_size=HISTORY_PAGE_SIZE,
        )
    except BackendAPIError as exc:
        await message.answer(f"❌ Не удалось загрузить историю.\n{exc.message}")
        return

    text = texts.format_history(
        data.get("items") or [],
        page=int(data.get("page") or page),
        total_pages=int(data.get("total_pages") or 0),
        total=int(data.get("total") or 0),
    )
    kb = history_keyboard(
        page=int(data.get("page") or page),
        has_prev=bool(data.get("has_prev")),
        has_next=bool(data.get("has_next")),
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb)
