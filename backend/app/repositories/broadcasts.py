from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import (
    Broadcast,
    BroadcastDelivery,
    BroadcastDeliveryStatus,
    BroadcastStatus,
)

_DELETABLE_STATUSES = (
    BroadcastStatus.SENT,
    BroadcastStatus.FAILED,
    BroadcastStatus.CANCELLED,
)


async def get_by_id(session: AsyncSession, broadcast_id: uuid.UUID) -> Broadcast | None:
    return await session.get(Broadcast, broadcast_id)


async def count_recipients(
    session: AsyncSession, segment_id: uuid.UUID | None
) -> int:
    from sqlalchemy import func

    from app.models.segment import UserSegment
    from app.models.user import User

    if segment_id is None:
        return (
            await session.scalar(
                select(func.count()).select_from(User).where(User.is_blocked.is_(False))
            )
        ) or 0
    return (
        await session.scalar(
            select(func.count())
            .select_from(UserSegment)
            .join(User, User.id == UserSegment.user_id)
            .where(
                UserSegment.segment_id == segment_id,
                User.is_blocked.is_(False),
            )
        )
    ) or 0


async def create(
    session: AsyncSession,
    *,
    name: str,
    material_id: uuid.UUID,
    segment_id: uuid.UUID | None = None,
    scheduled_at: datetime | None = None,
    created_by: uuid.UUID | None = None,
) -> Broadcast:
    bc = Broadcast(
        name=name,
        material_id=material_id,
        segment_id=segment_id,
        scheduled_at=scheduled_at,
        created_by=created_by,
    )
    session.add(bc)
    await session.flush()
    return bc


async def set_status(
    session: AsyncSession, bc: Broadcast, status: BroadcastStatus
) -> None:
    bc.status = status
    await session.flush()


async def list_broadcasts(
    session: AsyncSession, *, status: BroadcastStatus | None = None
) -> Sequence[Broadcast]:
    stmt = select(Broadcast).order_by(Broadcast.created_at.desc())
    if status is not None:
        stmt = stmt.where(Broadcast.status == status)
    return (await session.execute(stmt)).scalars().all()


async def add_delivery(
    session: AsyncSession,
    *,
    broadcast_id: uuid.UUID,
    user_id: uuid.UUID,
    status: BroadcastDeliveryStatus = BroadcastDeliveryStatus.PENDING,
) -> BroadcastDelivery:
    delivery = BroadcastDelivery(
        broadcast_id=broadcast_id, user_id=user_id, status=status
    )
    session.add(delivery)
    await session.flush()
    return delivery


async def list_deliveries(
    session: AsyncSession, broadcast_id: uuid.UUID
) -> Sequence[BroadcastDelivery]:
    stmt = select(BroadcastDelivery).where(
        BroadcastDelivery.broadcast_id == broadcast_id
    )
    return (await session.execute(stmt)).scalars().all()


async def list_due(
    session: AsyncSession, *, now: datetime | None = None
) -> Sequence[Broadcast]:
    """Return SCHEDULED broadcasts whose send time has arrived."""
    from datetime import timezone

    now = now or datetime.now(timezone.utc)
    stmt = select(Broadcast).where(
        Broadcast.status == BroadcastStatus.SCHEDULED,
        (Broadcast.scheduled_at.is_(None)) | (Broadcast.scheduled_at <= now),
    )
    return (await session.execute(stmt)).scalars().all()


async def delete_old(
    session: AsyncSession, *, cutoff: datetime, dry_run: bool = False
) -> int:
    """Delete finished broadcasts (sent/failed/cancelled) older than `cutoff`.

    Age is measured from `finished_at`, falling back to `created_at` for
    broadcasts that never recorded a finish time. Deliveries are deleted
    explicitly rather than relying on ON DELETE CASCADE, since SQLite (used
    in tests) does not enforce FK cascades by default.

    Returns the number of broadcasts deleted (or eligible, if `dry_run`).
    """
    age_expr = func.coalesce(Broadcast.finished_at, Broadcast.created_at)
    stmt = select(Broadcast.id).where(
        Broadcast.status.in_(_DELETABLE_STATUSES),
        age_expr < cutoff,
    )
    ids = (await session.execute(stmt)).scalars().all()
    if not ids or dry_run:
        return len(ids)

    await session.execute(
        delete(BroadcastDelivery).where(BroadcastDelivery.broadcast_id.in_(ids))
    )
    await session.execute(delete(Broadcast).where(Broadcast.id.in_(ids)))
    await session.flush()
    return len(ids)


async def get_recipients(
    session: AsyncSession, segment_id: uuid.UUID | None
):
    """Return all non-blocked User objects for this broadcast's audience."""
    from app.models.segment import UserSegment
    from app.models.user import User

    if segment_id is None:
        return (
            await session.execute(
                select(User).where(User.is_blocked.is_(False))
            )
        ).scalars().all()
    return (
        await session.execute(
            select(User)
            .join(UserSegment, User.id == UserSegment.user_id)
            .where(
                UserSegment.segment_id == segment_id,
                User.is_blocked.is_(False),
            )
        )
    ).scalars().all()
