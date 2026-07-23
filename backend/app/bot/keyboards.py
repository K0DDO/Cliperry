"""Inline and reply keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# Qualities shown as primary CTA buttons
PRIMARY_QUALITIES = ("1080p", "720p", "audio")


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 История"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="📖 Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вставьте ссылку на видео…",
    )


def quality_keyboard(
    pending_id: str,
    formats: list[dict],
    *,
    default_quality: str | None = None,
) -> InlineKeyboardMarkup:
    """
    Build quality buttons from analyze formats.

    Prefer 1080p / 720p / Audio; also show 480p if present.
    """
    available = {str(f.get("quality", "")).lower(): f for f in formats}
    order = ["1080p", "720p", "480p", "audio"]
    buttons: list[InlineKeyboardButton] = []

    for quality in order:
        fmt = available.get(quality.lower())
        if not fmt and quality == "audio":
            # accept "Audio" label variants
            fmt = available.get("audio")
        if not fmt:
            continue

        size = fmt.get("size")
        label = quality.upper() if quality != "audio" else "🎧 Audio"
        if quality.endswith("p"):
            label = quality
        if size:
            label = f"{label} · {size}"
        if default_quality and quality.lower() == default_quality.lower():
            label = f"⭐ {label}"

        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"dl:{pending_id}:{quality}",
            )
        )

    # Fallback if API returned odd qualities
    if not buttons:
        for fmt in formats[:4]:
            q = str(fmt.get("quality") or "best")
            buttons.append(
                InlineKeyboardButton(
                    text=q,
                    callback_data=f"dl:{pending_id}:{q}",
                )
            )

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for btn in buttons:
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append(
        [InlineKeyboardButton(text="✖️ Закрыть", callback_data=f"cancel:{pending_id}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_keyboard(current: str) -> InlineKeyboardMarkup:
    options = ["1080p", "720p", "480p", "audio"]
    rows = []
    for quality in options:
        mark = "✓ " if quality == current else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{quality}",
                    callback_data=f"set_quality:{quality}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_keyboard(*, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup | None:
    """Pagination controls for /history. Returns None when only one page."""
    if not has_prev and not has_next:
        return None

    row: list[InlineKeyboardButton] = []
    if has_prev:
        row.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"history:{page - 1}",
            )
        )
    row.append(
        InlineKeyboardButton(
            text=f"· {page} ·",
            callback_data=f"history:{page}",
        )
    )
    if has_next:
        row.append(
            InlineKeyboardButton(
                text="Вперёд ▶️",
                callback_data=f"history:{page + 1}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])
