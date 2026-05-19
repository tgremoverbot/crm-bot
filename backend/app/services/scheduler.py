from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

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
