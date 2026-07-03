from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UuidPkMixin
from app.models.enums import MaterialKind, ParseMode


class Material(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "materials"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[MaterialKind] = mapped_column(
        Enum(MaterialKind, name="material_kind", native_enum=False, length=32),
        nullable=False,
    )
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Origin of a message captured via the bot's /admin mode. When set, the
    # message is resent with copy_message so it always matches the original
    # byte-for-byte (formatting, captions, media) regardless of MaterialKind.
    source_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    parse_mode: Mapped[ParseMode] = mapped_column(
        Enum(ParseMode, name="parse_mode", native_enum=False, length=16),
        nullable=False,
        default=ParseMode.MARKDOWN_V2,
        server_default=ParseMode.MARKDOWN_V2.value,
    )
    disable_web_page_preview: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
