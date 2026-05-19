from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.user import User
from app.repositories import campaigns as campaign_repo
from app.repositories import events as event_repo
from app.repositories import users as user_repo


async def handle_start(
    session: AsyncSession,
    *,
    telegram_id: int,
    chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
    campaign_slug: str | None = None,
) -> tuple[User, bool, Campaign | None]:
    """
    Register or update a user from a /start command.

    Returns (user, is_new, campaign_if_found).
    Idempotent: calling twice with the same telegram_id updates last_seen_at
    but does not create a duplicate user or overwrite source_campaign_id.
    """
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    is_new = user is None

    if is_new:
        user = await user_repo.create(
            session,
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
    else:
        await user_repo.touch_last_seen(session, user)

    await event_repo.log(
        session,
        type="bot_started",
        user_id=user.id,
        payload={"telegram_id": telegram_id, "is_new": is_new},
    )

    campaign: Campaign | None = None
    if campaign_slug:
        found = await campaign_repo.get_by_slug(session, campaign_slug)
        if found and found.is_active:
            campaign = found
            if user.source_campaign_id is None:
                user.source_campaign_id = campaign.id
        await event_repo.log(
            session,
            type="campaign_detected",
            user_id=user.id,
            payload={
                "slug": campaign_slug,
                "found": campaign is not None,
                "campaign_id": str(campaign.id) if campaign else None,
            },
        )

    return user, is_new, campaign


async def handle_stop(
    session: AsyncSession,
    *,
    telegram_id: int,
) -> User | None:
    """Mark a user as having opted out via /stop."""
    user = await user_repo.get_by_telegram_id(session, telegram_id)
    if user:
        await event_repo.log(session, type="user_stopped", user_id=user.id, payload={})
    return user
