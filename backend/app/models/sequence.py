from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UuidPkMixin
from app.models.enums import SequenceTriggerKind


class Sequence(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "sequences"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    trigger_kind: Mapped[SequenceTriggerKind] = mapped_column(
        Enum(
            SequenceTriggerKind,
            name="sequence_trigger_kind",
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=SequenceTriggerKind.MANUAL,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class SequenceStep(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "sequence_steps"
    __table_args__ = (
        UniqueConstraint(
            "sequence_id", "position", name="uq_sequence_steps_sequence_position"
        ),
    )

    sequence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
