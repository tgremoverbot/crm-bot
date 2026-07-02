from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.admin_user import AdminUser
from app.repositories import app_settings as settings_repo
from app.schemas.app_settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter()


@router.get("", response_model=AppSettingsOut)
async def get_settings(
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> AppSettingsOut:
    settings = await settings_repo.get(session)
    return AppSettingsOut.model_validate(settings)


@router.patch("", response_model=AppSettingsOut)
async def update_settings(
    body: AppSettingsUpdate,
    session: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> AppSettingsOut:
    settings = await settings_repo.set_default_sequence(session, body.default_sequence_id)
    return AppSettingsOut.model_validate(settings)
