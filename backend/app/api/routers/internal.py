from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings
from app.services import scheduler as scheduler_service
from app.telegram.bot import get_bot

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    key = get_settings().INTERNAL_API_KEY
    if not key or x_internal_api_key != key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API key"
        )


@router.post("/process-scheduled")
async def process_scheduled(
    dry_run: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_key),
) -> dict:
    bot = get_bot()
    return await scheduler_service.process_due_messages(
        session,
        bot,
        limit=get_settings().SCHEDULER_MAX_MESSAGES,
        dry_run=dry_run,
    )
