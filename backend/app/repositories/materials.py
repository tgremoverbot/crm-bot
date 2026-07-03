from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialKind, ParseMode
from app.models.material import Material
from app.models.sequence import Sequence, SequenceStep


async def get_by_id(session: AsyncSession, material_id: uuid.UUID) -> Material | None:
    return await session.get(Material, material_id)


async def active_flow_names_using(
    session: AsyncSession, material_id: uuid.UUID
) -> list[str]:
    """Names of *active* auto-flows (sequences) that reference this material.

    A material is only undeletable when it's used by a step belonging to an
    active sequence. Steps of inactive sequences, broadcasts, and scheduled
    messages are historical usage and do not block deletion.
    """
    stmt = (
        select(Sequence.name)
        .join(SequenceStep, SequenceStep.sequence_id == Sequence.id)
        .where(
            SequenceStep.material_id == material_id,
            Sequence.is_active.is_(True),
        )
        .distinct()
    )
    return list((await session.execute(stmt)).scalars().all())


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
