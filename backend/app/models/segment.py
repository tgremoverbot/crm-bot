from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import CreatedAtMixin, TimestampMixin, UuidPkMixin


class Segment(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "segments"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class UserSegment(UuidPkMixin, CreatedAtMixin, Base):
    __tablename__ = "user_segments"
    __table_args__ = (
        UniqueConstraint("user_id", "segment_id", name="uq_user_segments_user_segment"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
