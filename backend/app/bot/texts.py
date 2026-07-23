"""User-facing Russian copy for the Telegram bot."""

from __future__ import annotations

WELCOME = (
    "<b>🍓 Cliperry</b>\n"
    "\n"
    "Универсальный загрузчик видео.\n"
    "\n"
    "Отправьте ссылку на YouTube / Shorts.\n"
    "\n"
    "TikTok, Instagram и X — скоро.\n"
    "\n"
    "Я покажу превью и доступные качества."
)

HELP = (
    "<b>📖 Помощь</b>\n"
    "\n"
    "<b>Как скачать</b>\n"
    "1. Пришлите ссылку на видео\n"
    "2. Выберите качество на кнопках\n"
    "3. Дождитесь готовности файла\n"
    "\n"
    "<b>Команды</b>\n"
    "/start — начать\n"
    "/help — эта справка\n"
    "/history — история загрузок\n"
    "/settings — качество по умолчанию\n"
    "\n"
    "Cliperry не хранит видео навсегда — только временная выдача."
)

ASK_LINK = "🍓 Пришлите ссылку на видео — я всё разберу."

ANALYZING = "🔎 Смотрю ссылку…"

HISTORY_EMPTY = (
    "<b>📜 История</b>\n"
    "\n"
    "Пока пусто.\n"
    "Скачайте первое видео — оно появится здесь."
)

SETTINGS_TITLE = (
    "<b>⚙️ Настройки</b>\n"
    "\n"
    "Качество по умолчанию: <b>{quality}</b>\n"
    "\n"
    "Выберите новое значение:"
)

DOWNLOAD_QUEUED = (
    "⬇️ <b>Загрузка</b>\n"
    "Качество: <b>{quality}</b>\n"
    "\n"
    "<code>{bar}</code>\n"
    "<b>{progress}%</b>"
)

DOWNLOAD_DONE = (
    "✅ <b>Готово</b>\n"
    "Качество: <b>{quality}</b>\n"
    "\n"
    "Файл подготовлен.\n"
    "{link}"
)

DOWNLOAD_FAILED = (
    "❌ <b>Не удалось скачать</b>\n"
    "\n"
    "{reason}"
)


def progress_bar(progress: int, width: int = 10) -> str:
    """Render a simple unicode progress bar."""
    filled = max(0, min(width, round(progress / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def format_download_progress(
    *,
    quality: str,
    progress: int,
    size: str | None = None,
    speed: str | None = None,
    eta: str | None = None,
    title: str | None = None,
) -> str:
    """
    Beautiful single-message progress card.

    ⬇️ Загрузка
    ███████░░░
    60%
    Размер / Скорость / ETA
    """
    lines = ["⬇️ <b>Загрузка</b>"]
    if title:
        lines.append(_escape(title[:80]))
    lines.append(f"Качество: <b>{_escape(quality)}</b>")
    lines.append("")
    lines.append(f"<code>{progress_bar(progress)}</code>")
    lines.append(f"<b>{max(0, min(100, int(progress)))}%</b>")

    details: list[str] = []
    if size:
        details.append(f"📦 { _escape(size) }")
    if speed:
        details.append(f"🚀 {_escape(speed)}")
    if eta:
        details.append(f"⏱ ETA {_escape(eta)}")
    if details:
        lines.append("")
        lines.extend(details)

    return "\n".join(lines)


def format_analyze_caption(
    *,
    title: str,
    platform: str,
    author: str | None,
    duration: str | None,
    is_playlist: bool,
    playlist_count: int | None,
) -> str:
    """Pretty HTML caption under thumbnail."""
    platform_label = {
        "youtube": "YouTube",
        "tiktok": "TikTok",
        "instagram": "Instagram",
        "twitter": "Twitter / X",
    }.get(platform, platform.capitalize())

    lines = [
        f"<b>🎬 { _escape(title) }</b>",
        "",
        f"📺 {platform_label}",
    ]
    if author:
        lines.append(f"👤 {_escape(author)}")
    if duration:
        lines.append(f"⏱ {duration}")
    if is_playlist:
        count = playlist_count or "—"
        lines.append(f"📂 Плейлист · {count} видео")
    lines.append("")
    lines.append("Выберите качество:")
    return "\n".join(lines)


_PLATFORM_LABELS = {
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "twitter": "Twitter / X",
}

_STATUS_LABELS = {
    "completed": ("✅", "Готово"),
    "failed": ("❌", "Ошибка"),
    "processing": ("⏳", "В работе"),
    "queued": ("📥", "В очереди"),
}


def format_history(
    items: list[dict],
    *,
    page: int = 1,
    total_pages: int = 1,
    total: int = 0,
) -> str:
    """Format paginated download history for Telegram HTML."""
    if not items and page <= 1:
        return HISTORY_EMPTY

    header = "<b>📜 Последние 10 загрузок</b>"
    if total_pages > 1:
        header = f"<b>📜 Последние 10 загрузок</b>\nстр. {page}/{total_pages}"

    lines = [header, ""]
    offset = (page - 1) * 10
    for idx, item in enumerate(items, start=1):
        platform = str(item.get("platform") or "?").lower()
        platform_label = _PLATFORM_LABELS.get(platform, platform.capitalize())
        status = str(item.get("status") or "?").lower()
        status_icon, status_label = _STATUS_LABELS.get(status, ("•", status))
        date_str = _format_history_date(item.get("created_at"))
        title = _escape(str(item.get("title") or "Без названия"))

        n = offset + idx
        lines.append(f"<b>{n}. {title}</b>")
        lines.append(f"Платформа: {platform_label}")
        lines.append(f"Дата: {date_str}")
        lines.append(f"Статус: {status_icon} {status_label}")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _format_history_date(value: object) -> str:
    """Render ISO / datetime as DD.MM.YYYY HH:MM."""
    if value is None:
        return "—"
    text = str(value).strip()
    if not text:
        return "—"
    # "2026-07-23T13:05:00+00:00" / "2026-07-23T13:05:00Z"
    try:
        from datetime import datetime

        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return _escape(text[:16])


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
