from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScheduledMessageStatus, SourceKind
from app.models.scheduled_message import ScheduledMessage


async def get_by_id(
    session: AsyncSession, message_id: uuid.UUID
) -> ScheduledMessage | None:
    return await session.get(ScheduledMessage, message_id)


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    material_id: uuid.UUID,
    scheduled_at: datetime,
    source_kind: SourceKind | None = None,
    source_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> ScheduledMessage:
    msg = ScheduledMessage(
        user_id=user_id,
        material_id=material_id,
        scheduled_at=scheduled_at,
        source_kind=source_kind,
        source_id=source_id,
        idempotency_key=idempotency_key,
    )
    session.add(msg)
    await session.flush()
    return msg


async def list_due_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    now: datetime | None = None,
    max_attempts: int = 3,
) -> Sequence[ScheduledMessage]:
    """Return due messages for a single user (used for immediate delivery)."""
    now = now or datetime.now(timezone.utc)
    stmt = (
        select(ScheduledMessage)
        .where(
            ScheduledMessage.user_id == user_id,
            ScheduledMessage.status.in_(
                [ScheduledMessageStatus.PENDING, ScheduledMessageStatus.FAILED]
            ),
            ScheduledMessage.scheduled_at <= now,
            ScheduledMessage.attempts < max_attempts,
        )
        .order_by(ScheduledMessage.scheduled_at.asc())
    )
    return (await session.execute(stmt)).scalars().all()


async def list_due(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
    max_attempts: int = 3,
) -> Sequence[ScheduledMessage]:
    """Return pending messages and retryable failed messages that are due."""
    now = now or datetime.now(timezone.utc)
    stmt = (
        select(ScheduledMessage)
        .where(
            ScheduledMessage.status.in_(
                [ScheduledMessageStatus.PENDING, ScheduledMessageStatus.FAILED]
            ),
            ScheduledMessage.scheduled_at <= now,
            ScheduledMessage.attempts < max_attempts,
        )
        .order_by(ScheduledMessage.scheduled_at.asc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()


async def mark_sent(
    session: AsyncSession, msg: ScheduledMessage, *, now: datetime | None = None
) -> None:
    msg.status = ScheduledMessageStatus.SENT
    msg.sent_at = now or datetime.now(timezone.utc)
    await session.flush()


async def mark_failed(
    session: AsyncSession,
    msg: ScheduledMessage,
    *,
    error: str,
    terminal: bool = False,
) -> None:
    msg.status = (
        ScheduledMessageStatus.FAILED_TERMINAL if terminal else ScheduledMessageStatus.FAILED
    )
    msg.last_error = error
    msg.attempts += 1
    await session.flush()


async def cancel(session: AsyncSession, msg: ScheduledMessage) -> None:
    msg.status = ScheduledMessageStatus.CANCELLED
    await session.flush()
