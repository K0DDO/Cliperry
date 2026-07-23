"""Bot handler package."""

from aiogram import Router

from app.bot.handlers import callbacks, commands, links


def setup_routers() -> Router:
    root = Router(name="cliperry_bot")
    root.include_router(commands.router)
    root.include_router(callbacks.router)
    root.include_router(links.router)
    return root
