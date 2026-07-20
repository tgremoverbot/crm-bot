from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db.session import get_session_factory
from app.logging import get_logger
from app.telegram.handlers import router
from app.telegram.middlewares import DbSessionMiddleware

log = get_logger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        token = get_settings().TELEGRAM_BOT_TOKEN
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
        _bot = Bot(token=token)
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher(storage=MemoryStorage())
        _dp.update.middleware(DbSessionMiddleware(get_session_factory()))
        _dp.include_router(router)
    return _dp


async def close_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


def reset() -> None:
    """Reset singletons — used in tests to pick up overridden settings."""
    global _bot, _dp
    _bot = None
    _dp = None
    # `router` is a module-level singleton that remembers the Dispatcher it was
    # attached to, and aiogram refuses to attach it twice. Detach it so the
    # next get_dispatcher() can include it again.
    router._parent_router = None
