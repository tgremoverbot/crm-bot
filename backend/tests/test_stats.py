from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import Broadcast, BroadcastStatus
from app.models.campaign import Campaign
from app.models.enums import MaterialKind, ScheduledMessageStatus, SourceKind
from app.models.material import Material
from app.models.scheduled_message import ScheduledMessage
from app.models.user import User
from app.services.stats import get_dashboard_stats


@pytest_asyncio.fixture
async def material(db_session: AsyncSession) -> Material:
    mat = Material(name="Welcome", kind=MaterialKind.TEXT, body="hi")
    db_session.add(mat)
    await db_session.commit()
    await db_session.refresh(mat)
    return mat


async def _user(
    session: AsyncSession,
    telegram_id: int,
    *,
    created_at: datetime | None = None,
    campaign_id=None,
    is_blocked: bool = False,
) -> User:
    user = User(
        telegram_id=telegram_id,
        chat_id=telegram_id,
        source_campaign_id=campaign_id,
        is_blocked=is_blocked,
    )
    session.add(user)
    await session.flush()
    if created_at is not None:
        user.created_at = created_at
    await session.commit()
    await session.refresh(user)
    return user


async def test_growth_returns_7_days_with_zero_fill(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    # one user today, one user 3 days ago
    await _user(db_session, 1, created_at=now)
    await _user(db_session, 2, created_at=now - timedelta(days=3))

    stats = await get_dashboard_stats(db_session)

    days = stats.growth.last_7_days
    assert len(days) == 7
    # ascending by date
    dates = [d.date for d in days]
    assert dates == sorted(dates)
    today_str = now.strftime("%Y-%m-%d")
    three_ago_str = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    by_date = {d.date: d.new_users for d in days}
    assert by_date[today_str] == 1
    assert by_date[three_ago_str] == 1
    # all other days are zero-filled
    assert sum(by_date.values()) == 2


async def test_users_blocked_count(db_session: AsyncSession):
    await _user(db_session, 10, is_blocked=True)
    await _user(db_session, 11, is_blocked=True)
    await _user(db_session, 12, is_blocked=False)

    stats = await get_dashboard_stats(db_session)

    assert stats.users.blocked == 2
    assert stats.users.total == 3


async def test_funnels_invite_links(db_session: AsyncSession, material: Material):
    camp = Campaign(name="Promo", slug="promo", is_active=True)
    inactive = Campaign(name="Old", slug="old", is_active=False)
    db_session.add_all([camp, inactive])
    await db_session.commit()
    await db_session.refresh(camp)
    await db_session.refresh(inactive)

    u1 = await _user(db_session, 20, campaign_id=camp.id)
    u2 = await _user(db_session, 21, campaign_id=camp.id)
    await _user(db_session, 22, campaign_id=inactive.id)

    # u1 has two sent sequence messages -> counted once (distinct user)
    for _ in range(2):
        db_session.add(
            ScheduledMessage(
                user_id=u1.id,
                material_id=material.id,
                status=ScheduledMessageStatus.SENT,
                source_kind=SourceKind.SEQUENCE,
                scheduled_at=datetime.now(timezone.utc),
            )
        )
    # u2 has a pending sequence message -> not counted
    db_session.add(
        ScheduledMessage(
            user_id=u2.id,
            material_id=material.id,
            status=ScheduledMessageStatus.PENDING,
            source_kind=SourceKind.SEQUENCE,
            scheduled_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    stats = await get_dashboard_stats(db_session)

    links = stats.funnels.invite_links
    slugs = {row.slug: row for row in links}
    assert "promo" in slugs
    assert "old" not in slugs  # inactive excluded
    assert slugs["promo"].joined == 2
    assert slugs["promo"].sequence_delivered == 1


async def test_broadcasts_recent(db_session: AsyncSession, material: Material):
    now = datetime.now(timezone.utc)
    for i in range(7):
        b = Broadcast(
            name=f"B{i}",
            material_id=material.id,
            status=BroadcastStatus.SENT,
            recipient_count=10,
            success_count=8,
            failure_count=2,
        )
        db_session.add(b)
        await db_session.flush()
        b.created_at = now - timedelta(hours=i)
    await db_session.commit()

    stats = await get_dashboard_stats(db_session)

    recent = stats.broadcasts.recent
    assert len(recent) == 5  # capped at 5
    # newest first
    assert recent[0].name == "B0"
    assert recent[0].recipient_count == 10
    assert recent[0].success_count == 8
    assert isinstance(recent[0].created_at, str)


async def test_delivery_sequence_success_rate(
    db_session: AsyncSession, material: Material
):
    u = await _user(db_session, 30)
    # 3 sent, 1 failed, plus pending/cancelled excluded from denominator
    statuses = [
        ScheduledMessageStatus.SENT,
        ScheduledMessageStatus.SENT,
        ScheduledMessageStatus.SENT,
        ScheduledMessageStatus.FAILED,
        ScheduledMessageStatus.PENDING,
        ScheduledMessageStatus.CANCELLED,
    ]
    for st in statuses:
        db_session.add(
            ScheduledMessage(
                user_id=u.id,
                material_id=material.id,
                status=st,
                source_kind=SourceKind.SEQUENCE,
                scheduled_at=datetime.now(timezone.utc),
            )
        )
    await db_session.commit()

    stats = await get_dashboard_stats(db_session)

    # 3 sent / 4 terminal (3 sent + 1 failed)
    assert stats.delivery.sequence_success_rate == pytest.approx(0.75)


async def test_delivery_rate_none_when_no_terminal(db_session: AsyncSession):
    stats = await get_dashboard_stats(db_session)
    assert stats.delivery.sequence_success_rate is None


async def test_existing_fields_preserved(db_session: AsyncSession):
    stats = await get_dashboard_stats(db_session)
    # existing structure still present
    assert stats.users.total == 0
    assert stats.campaigns.total == 0
    assert stats.materials.total == 0
    assert stats.sequences.total == 0
    assert stats.broadcasts.total == 0
    assert stats.scheduled.pending == 0
