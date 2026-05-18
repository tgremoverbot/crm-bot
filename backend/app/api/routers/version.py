from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/version", summary="Application version metadata")
async def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENV,
    }
