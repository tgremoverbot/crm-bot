from __future__ import annotations

import uuid
from collections.abc import Sequence as Seq

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import Segment, UserSegment


async def get_by_id(session: AsyncSession, segment_id: uuid.UUID) -> Segment | None:
    return await session.get(Segment, segment_id)


async def list_segments(session: AsyncSession) -> Seq[Segment]:
    stmt = select(Segment).order_by(Segment.name)
    return (await session.execute(stmt)).scalars().all()


async def create(
    session: AsyncSession, *, name: str, description: str | None = None
) -> Segment:
    seg = Segment(name=name, description=description)
    session.add(seg)
    await session.flush()
    return seg


async def add_user(
    session: AsyncSession, *, user_id: uuid.UUID, segment_id: uuid.UUID
) -> UserSegment | None:
    """Idempotently add a user to a segment. Returns the row on insert, None on duplicate."""
    existing = (
        await session.execute(
            select(UserSegment).where(
                UserSegment.user_id == user_id,
                UserSegment.segment_id == segment_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None
    row = UserSegment(user_id=user_id, segment_id=segment_id)
    session.add(row)
    await session.flush()
    return row


async def list_users_in_segment(
    session: AsyncSession, segment_id: uuid.UUID
) -> Seq[UserSegment]:
    stmt = select(UserSegment).where(UserSegment.segment_id == segment_id)
    return (await session.execute(stmt)).scalars().all()
