from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.broadcast import Broadcast, BroadcastDeliveryStatus, BroadcastStatus
from app.repositories import broadcasts as broadcast_repo
from app.repositories import materials as material_repo
from app.repositories import users as user_repo
from app.services.sender import send_material

log = get_logger(__name__)

# Telegram allows roughly 30 messages/second to different chats. Pace sends a
# little under that so a large broadcast doesn't trip the rate limiter.
_SEND_INTERVAL_SECONDS = 0.05

# Broadcasts with at most this many recipients are sent inline, in the request
# that created them, so the admin gets the result straight away. Anything
# larger is left SCHEDULED for the every-minute scheduler tick — a webhook
# request that runs too long gets retried by Telegram, which would send the
# broadcast twice.
INLINE_SEND_LIMIT = 50


async def send_broadcast(session: AsyncSession, bot: Bot, bc: Broadcast) -> dict:
    """Deliver one broadcast to its audience and record per-user results.

    Moves the broadcast to SENDING before the first recipient is touched, so a
    crash (or a concurrent scheduler tick) can't pick it up a second time.
    Returns {"sent": int, "failed": int, "status": BroadcastStatus}.
    """
    bc.status = BroadcastStatus.SENDING
    bc.started_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()

    material = (
        None
        if bc.material_id is None
        else await material_repo.get_by_id(session, bc.material_id)
    )
    if material is None:
        bc.status = BroadcastStatus.FAILED
        bc.finished_at = datetime.now(timezone.utc)
        await session.flush()
        await session.commit()
        return {"sent": 0, "failed": 0, "status": BroadcastStatus.FAILED}

    recipients = await broadcast_repo.get_recipients(session, bc.segment_id)
    bc.recipient_count = len(recipients)
    await session.flush()

    sent = 0
    failed = 0
    for index, user in enumerate(recipients):
        delivery = await broadcast_repo.add_delivery(
            session, broadcast_id=bc.id, user_id=user.id
        )
        try:
            await send_material(bot, user.chat_id, material)
            delivery.status = BroadcastDeliveryStatus.SENT
            delivery.sent_at = datetime.now(timezone.utc)
            sent += 1
        except TelegramForbiddenError:
            # User blocked the bot — mark them so future sends skip them.
            await user_repo.set_blocked(session, user, blocked=True)
            delivery.status = BroadcastDeliveryStatus.FAILED
            delivery.error = "User blocked the bot"
            failed += 1
        except TelegramRetryAfter as exc:
            # Rate limited: wait out the cooldown and retry this one recipient.
            await asyncio.sleep(exc.retry_after)
            try:
                await send_material(bot, user.chat_id, material)
                delivery.status = BroadcastDeliveryStatus.SENT
                delivery.sent_at = datetime.now(timezone.utc)
                sent += 1
            except Exception as retry_exc:
                delivery.status = BroadcastDeliveryStatus.FAILED
                delivery.error = str(retry_exc)
                failed += 1
        except (TelegramBadRequest, Exception) as exc:
            delivery.status = BroadcastDeliveryStatus.FAILED
            delivery.error = str(exc)
            failed += 1

        await session.flush()
        if index + 1 < len(recipients):
            await asyncio.sleep(_SEND_INTERVAL_SECONDS)

    bc.success_count = sent
    bc.failure_count = failed
    bc.status = BroadcastStatus.SENT
    bc.finished_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()

    return {"sent": sent, "failed": failed, "status": BroadcastStatus.SENT}


def format_report(result: dict) -> str:
    """Human-readable delivery summary for the admin who sent the broadcast."""
    if result["status"] == BroadcastStatus.FAILED:
        return (
            "❌ Broadcast failed — the message it was built from is no longer "
            "available. Nothing was sent."
        )

    sent = result["sent"]
    failed = result["failed"]
    total = sent + failed

    if total == 0:
        return "⚠️ No one to send to — there are no active subscribers yet."
    if failed == 0:
        return f"✅ Sent to all {sent} subscribers."
    if sent == 0:
        return (
            f"❌ Failed to send to all {failed} subscribers. "
            f"They may have blocked the bot."
        )
    return (
        f"⚠️ Sent to {sent} of {total} subscribers.\n"
        f"❌ {failed} failed — those users have most likely blocked the bot."
    )


async def notify_result(bot: Bot, chat_id: int, result: dict) -> None:
    """Send the delivery summary back to the admin. Never raises."""
    try:
        await bot.send_message(chat_id, format_report(result))
    except Exception:
        log.exception("Failed to deliver broadcast report to chat %s", chat_id)
