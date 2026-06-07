from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu_button import MenuButton


async def list_all(session: AsyncSession) -> Sequence[MenuButton]:
    stmt = select(MenuButton).order_by(MenuButton.row, MenuButton.position)
    return (await session.execute(stmt)).scalars().all()


async def list_active(session: AsyncSession) -> Sequence[MenuButton]:
    stmt = (
        select(MenuButton)
        .where(MenuButton.is_active.is_(True))
        .order_by(MenuButton.row, MenuButton.position)
    )
    return (await session.execute(stmt)).scalars().all()


async def get_by_id(session: AsyncSession, button_id: uuid.UUID) -> MenuButton | None:
    return await session.get(MenuButton, button_id)


async def get_by_label(session: AsyncSession, label: str) -> MenuButton | None:
    stmt = select(MenuButton).where(
        MenuButton.label == label,
        MenuButton.is_active.is_(True),
    )
    return (await session.execute(stmt)).scalars().first()


async def create(
    session: AsyncSession,
    *,
    label: str,
    row: int = 0,
    position: int = 0,
    action_kind: str = "text",
    action_material_id: uuid.UUID | None = None,
    action_text: str | None = None,
    is_active: bool = True,
) -> MenuButton:
    btn = MenuButton(
        label=label,
        row=row,
        position=position,
        action_kind=action_kind,
        action_material_id=action_material_id,
        action_text=action_text,
        is_active=is_active,
    )
    session.add(btn)
    await session.flush()
    return btn
