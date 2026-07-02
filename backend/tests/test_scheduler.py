from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialKind, ScheduledMessageStatus
from app.repositories import events as event_repo
from app.repositories import materials as material_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import users as user_repo
from app.services import scheduler as scheduler_service

_INTERNAL_KEY = "test-internal-key-abc123"
_PAST = datetime(2020, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_due_message(
    session: AsyncSession,
    *,
    telegram_id: int = 5001,
    body: str = "Hello!",
    scheduled_at: datetime | None = None,
):
    user = await user_repo.create(
        session, telegram_id=telegram_id, chat_id=telegram_id
    )
    mat = await material_repo.create(
        session, name="Mat", kind=MaterialKind.TEXT, body=body
    )
    msg = await scheduled_repo.create(
        session,
        user_id=user.id,
        material_id=mat.id,
        scheduled_at=scheduled_at or _PAST,
    )
    return user, mat, msg


def _mock_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
    return bot


# ---------------------------------------------------------------------------
# dry_run
# ---------------------------------------------------------------------------


async def test_dry_run_returns_count_without_mutation(db_session: AsyncSession):
    _, _, msg = await _make_due_message(db_session, telegram_id=5010)
    assert msg.status == ScheduledMessageStatus.PENDING

    result = await scheduler_service.process_due_messages(
        db_session, _mock_bot(), dry_run=True
    )

    assert result["dry_run"] is True
    assert result["total"] == 1
    assert result["sent"] == 0

    # Message must remain PENDING
    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.PENDING


# ---------------------------------------------------------------------------
# Successful send
# ---------------------------------------------------------------------------


async def test_sends_due_message_and_marks_sent(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5020)
    bot = _mock_bot()

    result = await scheduler_service.process_due_messages(db_session, bot)

    assert result["sent"] == 1
    assert result["failed"] == 0

    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.SENT
    assert refreshed.sent_at is not None

    bot.send_message.assert_awaited_once()


async def test_sent_message_logs_event(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5021)
    await scheduler_service.process_due_messages(db_session, _mock_bot())

    logs = await event_repo.list_for_user(db_session, user.id)
    assert any(e.type == "scheduled_message_sent" for e in logs)


# ---------------------------------------------------------------------------
# Blocked user
# ---------------------------------------------------------------------------


async def test_skips_blocked_user(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5030)
    await user_repo.set_blocked(db_session, user, blocked=True)

    result = await scheduler_service.process_due_messages(db_session, _mock_bot())

    assert result["skipped"] == 1
    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.CANCELLED


# ---------------------------------------------------------------------------
# TelegramForbiddenError
# ---------------------------------------------------------------------------


async def test_forbidden_marks_terminal_and_blocks_user(db_session: AsyncSession):
    from aiogram.exceptions import TelegramForbiddenError

    user, _, msg = await _make_due_message(db_session, telegram_id=5040)
    bot = _mock_bot()
    bot.send_message.side_effect = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden: bot was blocked by the user"
    )

    result = await scheduler_service.process_due_messages(db_session, bot)

    assert result["failed"] == 1
    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.FAILED_TERMINAL

    refreshed_user = await user_repo.get_by_id(db_session, user.id)
    assert refreshed_user.is_blocked is True


async def test_forbidden_logs_failed_event(db_session: AsyncSession):
    from aiogram.exceptions import TelegramForbiddenError

    user, _, msg = await _make_due_message(db_session, telegram_id=5041)
    bot = _mock_bot()
    bot.send_message.side_effect = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden"
    )

    await scheduler_service.process_due_messages(db_session, bot)

    logs = await event_repo.list_for_user(db_session, user.id)
    assert any(e.type == "scheduled_message_failed" for e in logs)


# ---------------------------------------------------------------------------
# Transient error (retryable)
# ---------------------------------------------------------------------------


async def test_transient_error_marks_failed_retryable(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5050)
    bot = _mock_bot()
    bot.send_message.side_effect = RuntimeError("network timeout")

    result = await scheduler_service.process_due_messages(db_session, bot)

    assert result["failed"] == 1
    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.FAILED
    assert "network timeout" in refreshed.last_error
    assert refreshed.attempts == 1


async def test_failed_message_retried_on_next_run(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5051)

    # First run: transient failure
    bot_fail = _mock_bot()
    bot_fail.send_message.side_effect = RuntimeError("timeout")
    await scheduler_service.process_due_messages(db_session, bot_fail)

    # Second run: success
    bot_ok = _mock_bot()
    result = await scheduler_service.process_due_messages(db_session, bot_ok)

    assert result["sent"] == 1
    refreshed = await scheduled_repo.get_by_id(db_session, msg.id)
    assert refreshed.status == ScheduledMessageStatus.SENT


# ---------------------------------------------------------------------------
# max_attempts exhaustion
# ---------------------------------------------------------------------------


async def test_exhausted_attempts_not_retried(db_session: AsyncSession):
    user, _, msg = await _make_due_message(db_session, telegram_id=5060)

    # Exhaust all 3 attempts
    for _ in range(3):
        bot = _mock_bot()
        bot.send_message.side_effect = RuntimeError("fail")
        await scheduler_service.process_due_messages(db_session, bot)

    # 4th run should not pick up the message
    bot_ok = _mock_bot()
    result = await scheduler_service.process_due_messages(db_session, bot_ok)
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# Internal endpoint
# ---------------------------------------------------------------------------


async def test_process_scheduled_endpoint_no_key(client: AsyncClient):
    resp = await client.post("/internal/process-scheduled")
    assert resp.status_code == 403


async def test_process_scheduled_endpoint_wrong_key(client: AsyncClient):
    resp = await client.post(
        "/internal/process-scheduled",
        headers={"X-Internal-Api-Key": "wrong-key"},
    )
    assert resp.status_code == 403


async def test_process_scheduled_endpoint_dry_run(client: AsyncClient, admin_user):
    resp = await client.post(
        "/internal/process-scheduled?dry_run=true",
        headers={"X-Internal-Api-Key": _INTERNAL_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["messages"]["dry_run"] is True
    assert "total" in data["messages"]
