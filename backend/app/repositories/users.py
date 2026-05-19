from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_users(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> Sequence[User]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    return (await session.execute(stmt)).scalars().all()


async def create(
    session: AsyncSession,
    *,
    telegram_id: int,
    chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
    source_campaign_id: uuid.UUID | None = None,
) -> User:
    user = User(
        telegram_id=telegram_id,
        chat_id=chat_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code,
        source_campaign_id=source_campaign_id,
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    return user


async def touch_last_seen(session: AsyncSession, user: User) -> None:
    user.last_seen_at = datetime.now(timezone.utc)
    await session.flush()


async def set_blocked(session: AsyncSession, user: User, blocked: bool) -> None:
    user.is_blocked = blocked
    await session.flush()
