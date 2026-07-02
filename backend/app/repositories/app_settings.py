from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings

_SINGLETON_ID = 1


async def get(session: AsyncSession) -> AppSettings:
    settings = await session.get(AppSettings, _SINGLETON_ID)
    if settings is None:
        settings = AppSettings(id=_SINGLETON_ID)
        session.add(settings)
        await session.flush()
    return settings


async def set_default_sequence(
    session: AsyncSession, sequence_id: uuid.UUID | None
) -> AppSettings:
    settings = await get(session)
    settings.default_sequence_id = sequence_id
    await session.flush()
    return settings
