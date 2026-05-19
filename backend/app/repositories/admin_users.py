from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser


async def get_by_id(session: AsyncSession, admin_id: uuid.UUID) -> AdminUser | None:
    return await session.get(AdminUser, admin_id)


async def get_by_email(session: AsyncSession, email: str) -> AdminUser | None:
    stmt = select(AdminUser).where(AdminUser.email == email.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    is_active: bool = True,
) -> AdminUser:
    admin = AdminUser(
        email=email.lower(), password_hash=password_hash, is_active=is_active
    )
    session.add(admin)
    await session.flush()
    return admin
