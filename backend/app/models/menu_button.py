from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UuidPkMixin


class MenuButton(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "menu_buttons"

    label: Mapped[str] = mapped_column(String(128), nullable=False)
    row: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # action_kind: "material" → send a saved message; "text" → reply with plain text
    action_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="text", server_default="text")
    action_material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
