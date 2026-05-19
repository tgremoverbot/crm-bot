from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UuidPkMixin
from app.models.enums import ScheduledMessageStatus, SourceKind


class ScheduledMessage(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "scheduled_messages"
    __table_args__ = (
        Index(
            "ix_scheduled_messages_status_scheduled_at",
            "status",
            "scheduled_at",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ScheduledMessageStatus] = mapped_column(
        Enum(
            ScheduledMessageStatus,
            name="scheduled_message_status",
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ScheduledMessageStatus.PENDING,
        server_default=ScheduledMessageStatus.PENDING.value,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_kind: Mapped[SourceKind | None] = mapped_column(
        Enum(SourceKind, name="source_kind", native_enum=False, length=16),
        nullable=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
