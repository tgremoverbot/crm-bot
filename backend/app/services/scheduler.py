from __future__ import annotations

import uuid
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import BroadcastDeliveryStatus, BroadcastStatus
from app.repositories import broadcasts as broadcast_repo
from app.repositories import events as event_repo
from app.repositories import materials as material_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import users as user_repo
from app.services.sender import send_material


async def process_due_messages(
    session: AsyncSession,
    bot: Bot,
    *,
    limit: int = 100,
    dry_run: bool = False,
) -> dict:
    """
    Fetch due scheduled messages and send them via Telegram.

    dry_run=True returns the count of due messages without mutating any state.
    """
    due = await scheduled_repo.list_due(session, limit=limit)
    result: dict = {
        "total": len(due),
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        return result

    for msg in due:
        user = await user_repo.get_by_id(session, msg.user_id)
        if user is None or user.is_blocked:
            await scheduled_repo.cancel(session, msg)
            result["skipped"] += 1
            continue

        material = await material_repo.get_by_id(session, msg.material_id)
        if material is None:
            await scheduled_repo.mark_failed(
                session, msg, error="Material not found", terminal=True
            )
            await event_repo.log(
                session,
                type="scheduled_message_failed",
                user_id=user.id,
                payload={"message_id": str(msg.id), "reason": "material_missing"},
            )
            result["failed"] += 1
            continue

        try:
            await send_material(bot, user.chat_id, material)
            await scheduled_repo.mark_sent(session, msg)
            await event_repo.log(
                session,
                type="scheduled_message_sent",
                user_id=user.id,
                payload={"message_id": str(msg.id)},
            )
            result["sent"] += 1
        except TelegramForbiddenError:
            await user_repo.set_blocked(session, user, blocked=True)
            await scheduled_repo.mark_failed(
                session,
                msg,
                error="TelegramForbiddenError: user blocked the bot",
                terminal=True,
            )
            await event_repo.log(
                session,
                type="scheduled_message_failed",
                user_id=user.id,
                payload={"message_id": str(msg.id), "reason": "forbidden"},
            )
            result["failed"] += 1
        except TelegramBadRequest as exc:
            await scheduled_repo.mark_failed(
                session, msg, error=str(exc), terminal=True
            )
            await event_repo.log(
                session,
                type="scheduled_message_failed",
                user_id=user.id,
                payload={"message_id": str(msg.id), "reason": "bad_request"},
            )
            result["failed"] += 1
        except Exception as exc:
            # Transient error — leave retryable (FAILED, not terminal)
            await scheduled_repo.mark_failed(session, msg, error=str(exc))
            await event_repo.log(
                session,
                type="scheduled_message_failed",
                user_id=user.id,
                payload={"message_id": str(msg.id), "reason": "transient"},
            )
            result["failed"] += 1

    return result


async def flush_user(
    session: AsyncSession,
    bot: Bot,
    user_id: uuid.UUID,
) -> None:
    """Send all due messages for a single user immediately.

    Called right after sequence enrollment so 0-delay steps arrive
    without waiting for the next scheduler tick.
    """
    due = await scheduled_repo.list_due_for_user(session, user_id)
    for msg in due:
        user = await user_repo.get_by_id(session, msg.user_id)
        if user is None or user.is_blocked:
            await scheduled_repo.cancel(session, msg)
            continue
        material = await material_repo.get_by_id(session, msg.material_id)
        if material is None:
            await scheduled_repo.mark_failed(session, msg, error="Material not found", terminal=True)
            continue
        try:
            await send_material(bot, user.chat_id, material)
            await scheduled_repo.mark_sent(session, msg)
            await event_repo.log(session, type="scheduled_message_sent", user_id=user.id,
                                 payload={"message_id": str(msg.id)})
        except TelegramForbiddenError:
            await user_repo.set_blocked(session, user, blocked=True)
            await scheduled_repo.mark_failed(session, msg, error="TelegramForbiddenError", terminal=True)
        except (TelegramBadRequest, Exception) as exc:
            await scheduled_repo.mark_failed(session, msg, error=str(exc), terminal=isinstance(exc, TelegramBadRequest))


async def process_due_broadcasts(session: AsyncSession, bot: Bot) -> dict:
    """Send all SCHEDULED broadcasts whose send time has arrived."""
    now = datetime.now(timezone.utc)
    due = await broadcast_repo.list_due(session, now=now)
    result: dict = {"processed": len(due), "recipients_sent": 0, "recipients_failed": 0}

    for bc in due:
        # Mark SENDING before touching any recipients so a crash doesn't re-process
        bc.status = BroadcastStatus.SENDING
        bc.started_at = now
        await session.flush()

        material = await material_repo.get_by_id(session, bc.material_id)
        if material is None:
            bc.status = BroadcastStatus.FAILED
            bc.finished_at = datetime.now(timezone.utc)
            await session.flush()
            await session.commit()
            continue

        recipients = await broadcast_repo.get_recipients(session, bc.segment_id)
        bc.recipient_count = len(recipients)
        await session.flush()

        sent = 0
        failed = 0
        for user in recipients:
            delivery = await broadcast_repo.add_delivery(
                session, broadcast_id=bc.id, user_id=user.id
            )
            try:
                await send_material(bot, user.chat_id, material)
                delivery.status = BroadcastDeliveryStatus.SENT
                delivery.sent_at = datetime.now(timezone.utc)
                await session.flush()
                sent += 1
            except TelegramForbiddenError:
                await user_repo.set_blocked(session, user, blocked=True)
                delivery.status = BroadcastDeliveryStatus.FAILED
                delivery.error = "User blocked the bot"
                await session.flush()
                failed += 1
            except TelegramBadRequest as exc:
                delivery.status = BroadcastDeliveryStatus.FAILED
                delivery.error = str(exc)
                await session.flush()
                failed += 1
            except Exception as exc:
                delivery.status = BroadcastDeliveryStatus.FAILED
                delivery.error = str(exc)
                await session.flush()
                failed += 1

        bc.success_count = sent
        bc.failure_count = failed
        bc.status = BroadcastStatus.SENT
        bc.finished_at = datetime.now(timezone.utc)
        await session.flush()
        await session.commit()

        result["recipients_sent"] += sent
        result["recipients_failed"] += failed

    return result
