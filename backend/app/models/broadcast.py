from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import CreatedAtMixin, TimestampMixin, UuidPkMixin


class BroadcastStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BroadcastDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class Broadcast(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "broadcasts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, name="broadcast_status", native_enum=False, length=16),
        nullable=False,
        default=BroadcastStatus.DRAFT,
        server_default=BroadcastStatus.DRAFT.value,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recipient_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )


class BroadcastDelivery(UuidPkMixin, CreatedAtMixin, Base):
    __tablename__ = "broadcast_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "broadcast_id", "user_id", name="uq_broadcast_deliveries_broadcast_user"
        ),
    )

    broadcast_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("broadcasts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[BroadcastDeliveryStatus] = mapped_column(
        Enum(
            BroadcastDeliveryStatus,
            name="broadcast_delivery_status",
            native_enum=False,
            length=16,
        ),
        nullable=False,
        default=BroadcastDeliveryStatus.PENDING,
        server_default=BroadcastDeliveryStatus.PENDING.value,
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
