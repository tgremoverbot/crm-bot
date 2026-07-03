from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialKind, ParseMode
from app.models.material import Material


async def get_by_id(session: AsyncSession, material_id: uuid.UUID) -> Material | None:
    return await session.get(Material, material_id)


async def list_materials(session: AsyncSession) -> Sequence[Material]:
    stmt = select(Material).order_by(Material.created_at.desc())
    return (await session.execute(stmt)).scalars().all()


async def create(
    session: AsyncSession,
    *,
    name: str,
    kind: MaterialKind,
    body: str | None = None,
    file_id: str | None = None,
    file_url: str | None = None,
    link_url: str | None = None,
    parse_mode: ParseMode = ParseMode.MARKDOWN_V2,
    disable_web_page_preview: bool = False,
    source_chat_id: int | None = None,
    source_message_id: int | None = None,
) -> Material:
    material = Material(
        name=name,
        kind=kind,
        body=body,
        file_id=file_id,
        file_url=file_url,
        link_url=link_url,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
    )
    session.add(material)
    await session.flush()
    return material
