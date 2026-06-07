from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.admin_user import AdminUser
from app.repositories import menu_buttons as repo
from app.schemas.menu_button import MenuButtonCreate, MenuButtonOut, MenuButtonUpdate

router = APIRouter()


@router.get("", response_model=list[MenuButtonOut])
async def list_menu_buttons(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[MenuButtonOut]:
    items = await repo.list_all(session)
    return [MenuButtonOut.model_validate(b) for b in items]


@router.post("", response_model=MenuButtonOut, status_code=status.HTTP_201_CREATED)
async def create_menu_button(
    body: MenuButtonCreate,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> MenuButtonOut:
    btn = await repo.create(session, **body.model_dump())
    await session.refresh(btn)
    return MenuButtonOut.model_validate(btn)


@router.patch("/{button_id}", response_model=MenuButtonOut)
async def update_menu_button(
    button_id: UUID,
    body: MenuButtonUpdate,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> MenuButtonOut:
    btn = await repo.get_by_id(session, button_id)
    if not btn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Button not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(btn, field, value)
    await session.flush()
    await session.refresh(btn)
    return MenuButtonOut.model_validate(btn)


@router.delete("/{button_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_button(
    button_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> None:
    btn = await repo.get_by_id(session, button_id)
    if not btn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Button not found")
    await session.delete(btn)
