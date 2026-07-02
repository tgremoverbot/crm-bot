from __future__ import annotations

from pydantic import BaseModel


class UserStats(BaseModel):
    total: int
    new_today: int
    new_this_week: int
    new_prev_week: int
    active_7d: int
    blocked: int = 0


class CampaignStats(BaseModel):
    total: int
    active: int


class SimpleCount(BaseModel):
    total: int


class SequenceStats(BaseModel):
    total: int
    active: int


class RecentBroadcast(BaseModel):
    id: str
    name: str
    status: str
    recipient_count: int
    success_count: int
    failure_count: int
    created_at: str


class BroadcastStats(BaseModel):
    total: int
    sent: int
    recent: list[RecentBroadcast] = []


class ScheduledStats(BaseModel):
    pending: int


class MessageStats(BaseModel):
    """All-source (auto-flow + broadcast) count of successfully delivered messages."""

    delivered_total: int
    delivered_this_week: int
    delivered_prev_week: int


class GrowthDay(BaseModel):
    date: str
    new_users: int


class GrowthStats(BaseModel):
    days: list[GrowthDay] = []
    window_days: int = 7


class InviteLinkFunnel(BaseModel):
    slug: str
    name: str
    joined: int
    sequence_delivered: int


class FunnelStats(BaseModel):
    invite_links: list[InviteLinkFunnel] = []


class DeliveryStats(BaseModel):
    sequence_success_rate: float | None = None


class StatsOut(BaseModel):
    users: UserStats
    campaigns: CampaignStats
    materials: SimpleCount
    sequences: SequenceStats
    broadcasts: BroadcastStats
    messages: MessageStats
    scheduled: ScheduledStats
    growth: GrowthStats = GrowthStats()
    funnels: FunnelStats = FunnelStats()
    delivery: DeliveryStats = DeliveryStats()
