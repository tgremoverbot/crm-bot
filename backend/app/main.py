from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health, version
from app.config import Settings, get_settings
from app.db.session import dispose_engine, get_engine
from app.logging import configure_logging, get_logger
from app.middleware import RequestIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(level=settings.LOG_LEVEL, app_name=settings.APP_NAME)
    log = get_logger(settings.APP_NAME)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        log.info("startup", extra={"env": settings.ENV, "version": settings.APP_VERSION})
        get_engine()
        try:
            yield
        finally:
            await dispose_engine()
            log.info("shutdown")

    app = FastAPI(
        title="Arabic Contact Bot API",
        version=settings.APP_VERSION,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.include_router(health.router)
    app.include_router(version.router)

    return app


app = create_app()
