from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import Broadcast, BroadcastStatus
from app.models.campaign import Campaign
from app.models.enums import ScheduledMessageStatus, SourceKind
from app.models.material import Material
from app.models.scheduled_message import ScheduledMessage
from app.models.sequence import Sequence
from app.models.user import User
from app.schemas.stats import (
    BroadcastStats,
    CampaignStats,
    DeliveryStats,
    FunnelStats,
    GrowthDay,
    GrowthStats,
    InviteLinkFunnel,
    RecentBroadcast,
    ScheduledStats,
    SequenceStats,
    SimpleCount,
    StatsOut,
    UserStats,
)


async def get_dashboard_stats(session: AsyncSession) -> StatsOut:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    async def _count(stmt) -> int:
        return (await session.scalar(stmt)) or 0

    total_users = await _count(select(func.count()).select_from(User))
    new_today = await _count(
        select(func.count()).select_from(User).where(User.created_at >= today)
    )
    active_7d = await _count(
        select(func.count()).select_from(User).where(User.last_seen_at >= week_ago)
    )
    blocked_users = await _count(
        select(func.count()).select_from(User).where(User.is_blocked.is_(True))
    )
    total_campaigns = await _count(select(func.count()).select_from(Campaign))
    active_campaigns = await _count(
        select(func.count()).select_from(Campaign).where(Campaign.is_active.is_(True))
    )
    total_materials = await _count(select(func.count()).select_from(Material))
    total_sequences = await _count(select(func.count()).select_from(Sequence))
    active_sequences = await _count(
        select(func.count()).select_from(Sequence).where(Sequence.is_active.is_(True))
    )
    total_broadcasts = await _count(select(func.count()).select_from(Broadcast))
    sent_broadcasts = await _count(
        select(func.count())
        .select_from(Broadcast)
        .where(Broadcast.status == BroadcastStatus.SENT)
    )
    pending_scheduled = await _count(
        select(func.count())
        .select_from(ScheduledMessage)
        .where(ScheduledMessage.status == ScheduledMessageStatus.PENDING)
    )

    growth = await _build_growth(session, today)
    funnels = await _build_funnels(session)
    recent_broadcasts = await _build_recent_broadcasts(session)
    delivery = await _build_delivery(session)

    return StatsOut(
        users=UserStats(
            total=total_users,
            new_today=new_today,
            active_7d=active_7d,
            blocked=blocked_users,
        ),
        campaigns=CampaignStats(total=total_campaigns, active=active_campaigns),
        materials=SimpleCount(total=total_materials),
        sequences=SequenceStats(total=total_sequences, active=active_sequences),
        broadcasts=BroadcastStats(
            total=total_broadcasts,
            sent=sent_broadcasts,
            recent=recent_broadcasts,
        ),
        scheduled=ScheduledStats(pending=pending_scheduled),
        growth=growth,
        funnels=funnels,
        delivery=delivery,
    )


async def _build_growth(session: AsyncSession, today: datetime) -> GrowthStats:
    """New users per day for the past 7 calendar days (UTC), zero-filled."""
    start = today - timedelta(days=6)
    day_expr = func.date(User.created_at)
    stmt = (
        select(day_expr.label("day"), func.count().label("count"))
        .where(User.created_at >= start)
        .group_by(day_expr)
    )
    rows = (await session.execute(stmt)).all()
    counts: dict[str, int] = {}
    for day, count in rows:
        # func.date may return a date object (Postgres) or a string (SQLite).
        key = day.isoformat() if hasattr(day, "isoformat") else str(day)
        counts[key] = int(count or 0)

    days: list[GrowthDay] = []
    for offset in range(7):
        d = start + timedelta(days=offset)
        key = d.strftime("%Y-%m-%d")
        days.append(GrowthDay(date=key, new_users=counts.get(key, 0)))
    return GrowthStats(last_7_days=days)


async def _build_funnels(session: AsyncSession) -> FunnelStats:
    """Per active-campaign join and sequence-delivery counts, top 10 by joined."""
    active_campaigns = (
        (
            await session.execute(
                select(Campaign).where(Campaign.is_active.is_(True))
            )
        )
        .scalars()
        .all()
    )

    links: list[InviteLinkFunnel] = []
    for campaign in active_campaigns:
        joined = (
            await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.source_campaign_id == campaign.id)
            )
        ) or 0

        sequence_delivered = (
            await session.scalar(
                select(func.count(distinct(ScheduledMessage.user_id)))
                .where(ScheduledMessage.source_kind == SourceKind.SEQUENCE)
                .where(ScheduledMessage.status == ScheduledMessageStatus.SENT)
                .where(
                    ScheduledMessage.user_id.in_(
                        select(User.id).where(
                            User.source_campaign_id == campaign.id
                        )
                    )
                )
            )
        ) or 0

        links.append(
            InviteLinkFunnel(
                slug=campaign.slug,
                name=campaign.name,
                joined=int(joined),
                sequence_delivered=int(sequence_delivered),
            )
        )

    links.sort(key=lambda link: link.joined, reverse=True)
    return FunnelStats(invite_links=links[:10])


async def _build_recent_broadcasts(session: AsyncSession) -> list[RecentBroadcast]:
    stmt = select(Broadcast).order_by(Broadcast.created_at.desc()).limit(5)
    broadcasts = (await session.execute(stmt)).scalars().all()
    return [
        RecentBroadcast(
            id=str(b.id),
            name=b.name,
            status=b.status.value if hasattr(b.status, "value") else str(b.status),
            recipient_count=b.recipient_count,
            success_count=b.success_count,
            failure_count=b.failure_count,
            created_at=b.created_at.isoformat(),
        )
        for b in broadcasts
    ]


async def _build_delivery(session: AsyncSession) -> DeliveryStats:
    sent = (
        await session.scalar(
            select(func.count())
            .select_from(ScheduledMessage)
            .where(ScheduledMessage.status == ScheduledMessageStatus.SENT)
        )
    ) or 0
    terminal = (
        await session.scalar(
            select(func.count())
            .select_from(ScheduledMessage)
            .where(
                ScheduledMessage.status.notin_(
                    [
                        ScheduledMessageStatus.PENDING,
                        ScheduledMessageStatus.PROCESSING,
                        ScheduledMessageStatus.CANCELLED,
                    ]
                )
            )
        )
    ) or 0

    rate = (sent / terminal) if terminal else None
    return DeliveryStats(sequence_success_rate=rate)
