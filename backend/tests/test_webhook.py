from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import campaigns as campaign_repo
from app.repositories import events as event_repo
from app.repositories import users as user_repo
from app.telegram import service as svc
from app.telegram.bot import reset as reset_bot


@pytest_asyncio.fixture(autouse=True)
async def _reset_bot_singletons():
    reset_bot()
    yield
    reset_bot()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_update(telegram_id: int = 111, args: str | None = None) -> dict:
    text = "/start" if not args else f"/start {args}"
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1700000000,
            "chat": {"id": telegram_id, "type": "private"},
            "from": {
                "id": telegram_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "uz",
            },
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": len("/start")}],
        },
    }


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


async def test_webhook_returns_200(client: AsyncClient):
    payload = _start_update()
    resp = await client.post("/webhook/telegram", content=json.dumps(payload),
                             headers={"Content-Type": "application/json"})
    assert resp.status_code == 200


async def test_webhook_invalid_secret_returns_403(client: AsyncClient):
    from app.config import get_settings
    settings = get_settings()
    original = settings.TELEGRAM_WEBHOOK_SECRET
    settings.TELEGRAM_WEBHOOK_SECRET = "correct-secret"
    try:
        resp = await client.post(
            "/webhook/telegram",
            content=json.dumps(_start_update()),
            headers={
                "Content-Type": "application/json",
                "X-Telegram-Bot-Api-Secret-Token": "wrong-secret",
            },
        )
        assert resp.status_code == 403
    finally:
        settings.TELEGRAM_WEBHOOK_SECRET = original


# ---------------------------------------------------------------------------
# Service-level tests (db_session fixture — no HTTP layer)
# ---------------------------------------------------------------------------


async def test_start_creates_new_user(db_session: AsyncSession):
    user, is_new, campaign = await svc.handle_start(
        db_session,
        telegram_id=42,
        chat_id=42,
        username="alice",
        first_name="Alice",
    )
    assert is_new is True
    assert user.telegram_id == 42
    assert campaign is None


async def test_start_idempotent(db_session: AsyncSession):
    await svc.handle_start(db_session, telegram_id=99, chat_id=99)
    user2, is_new2, _ = await svc.handle_start(db_session, telegram_id=99, chat_id=99)
    assert is_new2 is False
    assert user2.telegram_id == 99

    # Still only one user row
    fetched = await user_repo.get_by_telegram_id(db_session, 99)
    assert fetched is not None
    assert fetched.id == user2.id


async def test_start_without_campaign(db_session: AsyncSession):
    user, is_new, campaign = await svc.handle_start(
        db_session, telegram_id=10, chat_id=10
    )
    assert campaign is None
    assert user.source_campaign_id is None


async def test_start_with_valid_campaign(db_session: AsyncSession):
    camp = await campaign_repo.create(
        db_session, name="Ramadan Promo", slug="ramadan", is_active=True
    )

    user, is_new, detected = await svc.handle_start(
        db_session, telegram_id=20, chat_id=20, campaign_slug="ramadan"
    )
    assert detected is not None
    assert detected.id == camp.id
    assert user.source_campaign_id == camp.id


async def test_start_with_inactive_campaign(db_session: AsyncSession):
    await campaign_repo.create(
        db_session, name="Old Promo", slug="old-promo", is_active=False
    )
    _, _, detected = await svc.handle_start(
        db_session, telegram_id=21, chat_id=21, campaign_slug="old-promo"
    )
    assert detected is None


async def test_start_with_unknown_campaign_slug(db_session: AsyncSession):
    _, _, detected = await svc.handle_start(
        db_session, telegram_id=22, chat_id=22, campaign_slug="nonexistent"
    )
    assert detected is None


async def test_start_campaign_not_overwritten_on_repeat(db_session: AsyncSession):
    camp = await campaign_repo.create(
        db_session, name="First", slug="first", is_active=True
    )
    await campaign_repo.create(db_session, name="Second", slug="second", is_active=True)

    user, _, _ = await svc.handle_start(
        db_session, telegram_id=30, chat_id=30, campaign_slug="first"
    )
    assert user.source_campaign_id == camp.id

    # Second /start with different campaign must not overwrite source_campaign_id
    user2, _, _ = await svc.handle_start(
        db_session, telegram_id=30, chat_id=30, campaign_slug="second"
    )
    assert user2.source_campaign_id == camp.id


async def test_stop_logs_event(db_session: AsyncSession):
    await svc.handle_start(db_session, telegram_id=50, chat_id=50)
    user = await svc.handle_stop(db_session, telegram_id=50)
    assert user is not None

    logs = await event_repo.list_for_user(db_session, user.id)
    types = [e.type for e in logs]
    assert "user_stopped" in types


async def test_stop_unknown_user_returns_none(db_session: AsyncSession):
    result = await svc.handle_stop(db_session, telegram_id=9999)
    assert result is None
