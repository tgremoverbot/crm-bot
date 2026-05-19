from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import CreatedAtMixin, UuidPkMixin


class EventLog(UuidPkMixin, CreatedAtMixin, Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index("ix_event_logs_user_created_at", "user_id", "created_at"),
        Index("ix_event_logs_type_created_at", "type", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
