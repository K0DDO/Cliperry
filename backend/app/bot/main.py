"""Telegram bot entrypoint (aiogram 3)."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.api_client import BackendClient
from app.bot.handlers import setup_routers
from app.bot.store import BotStore
from app.config import get_settings
from app.logging_config import configure_logging

logger = logging.getLogger("cliperry.bot")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)

    backend_url = settings.backend_api_base_url
    api = BackendClient(backend_url, settings.redis_url)
    store = BotStore(settings.redis_url)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["api"] = api
    dp["store"] = store
    dp.include_router(setup_routers())

    # Middleware-style injection via workflow_data is enough for handlers
    # that declare `api` / `store` keyword args — aiogram resolves from workflow_data.

    logger.info("bot starting backend=%s", backend_url)
    try:
        await dp.start_polling(bot, api=api, store=store)
    finally:
        await api.aclose()
        await store.aclose()
        await bot.session.close()
        logger.info("bot stopped")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
