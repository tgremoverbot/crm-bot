from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_log import EventLog


async def log(
    session: AsyncSession,
    *,
    type: str,
    user_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> EventLog:
    event = EventLog(type=type, user_id=user_id, payload=payload or {})
    session.add(event)
    await session.flush()
    return event


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 50
) -> Sequence[EventLog]:
    stmt = (
        select(EventLog)
        .where(EventLog.user_id == user_id)
        .order_by(EventLog.created_at.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()


async def list_by_type(
    session: AsyncSession, type: str, *, limit: int = 50
) -> Sequence[EventLog]:
    stmt = (
        select(EventLog)
        .where(EventLog.type == type)
        .order_by(EventLog.created_at.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()
