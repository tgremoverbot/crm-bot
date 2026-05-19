from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign


async def get_by_id(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def get_by_slug(session: AsyncSession, slug: str) -> Campaign | None:
    stmt = select(Campaign).where(Campaign.slug == slug)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_campaigns(
    session: AsyncSession, *, is_active: bool | None = None
) -> Sequence[Campaign]:
    stmt = select(Campaign).order_by(Campaign.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(Campaign.is_active == is_active)
    return (await session.execute(stmt)).scalars().all()


async def create(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    description: str | None = None,
    is_active: bool = True,
    default_sequence_id: uuid.UUID | None = None,
) -> Campaign:
    campaign = Campaign(
        name=name,
        slug=slug,
        description=description,
        is_active=is_active,
        default_sequence_id=default_sequence_id,
    )
    session.add(campaign)
    await session.flush()
    return campaign
