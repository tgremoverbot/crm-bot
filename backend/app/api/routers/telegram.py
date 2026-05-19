from __future__ import annotations

import hashlib
import hmac

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.logging import get_logger
from app.telegram.bot import get_bot, get_dispatcher

router = APIRouter(prefix="/webhook", tags=["webhook"])
log = get_logger(__name__)


@router.post("/telegram", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    settings = get_settings()

    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")

    body = await request.json()
    update = Update.model_validate(body)

    bot = get_bot()
    dp = get_dispatcher()
    try:
        await dp.feed_update(bot=bot, update=update)
    except Exception:
        log.exception("Unhandled error while processing Telegram update")

    return {}
