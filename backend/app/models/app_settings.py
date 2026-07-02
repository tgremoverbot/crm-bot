from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin


class AppSettings(TimestampMixin, Base):
    """Singleton row (id=1) holding app-wide, admin-editable settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_sequence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("sequences.id", ondelete="SET NULL"),
        nullable=True,
    )
