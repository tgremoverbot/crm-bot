from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import BroadcastDeliveryStatus, BroadcastStatus
from app.models.enums import MaterialKind
from app.repositories import broadcasts as broadcast_repo
from app.repositories import materials as material_repo
from app.repositories import users as user_repo
from app.services import broadcast as broadcast_service


def _mock_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
    bot.copy_message = AsyncMock(return_value=MagicMock(message_id=99))
    return bot


async def _make_broadcast(
    session: AsyncSession,
    *,
    recipients: int,
    first_telegram_id: int,
    notify_chat_id: int | None = None,
):
    users = [
        await user_repo.create(
            session, telegram_id=first_telegram_id + i, chat_id=first_telegram_id + i
        )
        for i in range(recipients)
    ]
    material = await material_repo.create(
        session, name="Post", kind=MaterialKind.TEXT, body="Hello everyone"
    )
    bc = await broadcast_repo.create(
        session,
        name="Test broadcast",
        material_id=material.id,
        notify_chat_id=notify_chat_id,
    )
    return users, material, bc


# ---------------------------------------------------------------------------
# send_broadcast
# ---------------------------------------------------------------------------


async def test_send_broadcast_delivers_to_every_subscriber(db_session: AsyncSession):
    users, _, bc = await _make_broadcast(
        db_session, recipients=3, first_telegram_id=7100
    )
    bot = _mock_bot()

    result = await broadcast_service.send_broadcast(db_session, bot, bc)

    assert result == {"sent": 3, "failed": 0, "status": BroadcastStatus.SENT}
    assert bot.send_message.await_count == 3
    assert {call.args[0] for call in bot.send_message.await_args_list} == {
        u.chat_id for u in users
    }
    assert bc.status == BroadcastStatus.SENT
    assert bc.recipient_count == 3
    assert bc.success_count == 3
    assert bc.failure_count == 0
    assert bc.finished_at is not None


async def test_send_broadcast_records_per_user_delivery_rows(db_session: AsyncSession):
    _, _, bc = await _make_broadcast(db_session, recipients=2, first_telegram_id=7200)

    await broadcast_service.send_broadcast(db_session, _mock_bot(), bc)

    deliveries = await broadcast_repo.list_deliveries(db_session, bc.id)
    assert len(deliveries) == 2
    assert all(d.status == BroadcastDeliveryStatus.SENT for d in deliveries)
    assert all(d.sent_at is not None for d in deliveries)


async def test_send_broadcast_marks_blocking_user_and_keeps_going(
    db_session: AsyncSession,
):
    """One user blocking the bot must not stop delivery to everyone else."""
    users, _, bc = await _make_broadcast(
        db_session, recipients=3, first_telegram_id=7300
    )
    blocker = users[1]

    bot = _mock_bot()

    async def send(chat_id, *args, **kwargs):
        if chat_id == blocker.chat_id:
            raise TelegramForbiddenError(method=MagicMock(), message="blocked")
        return MagicMock(message_id=99)

    bot.send_message = AsyncMock(side_effect=send)

    result = await broadcast_service.send_broadcast(db_session, bot, bc)

    assert result["sent"] == 2
    assert result["failed"] == 1
    await db_session.refresh(blocker)
    assert blocker.is_blocked is True

    deliveries = await broadcast_repo.list_deliveries(db_session, bc.id)
    failed = [d for d in deliveries if d.status == BroadcastDeliveryStatus.FAILED]
    assert len(failed) == 1
    assert failed[0].error == "User blocked the bot"


async def test_send_broadcast_records_bad_request_as_failure(db_session: AsyncSession):
    _, _, bc = await _make_broadcast(db_session, recipients=1, first_telegram_id=7400)
    bot = _mock_bot()
    bot.send_message = AsyncMock(
        side_effect=TelegramBadRequest(method=MagicMock(), message="wrong file id")
    )

    result = await broadcast_service.send_broadcast(db_session, bot, bc)

    assert result["sent"] == 0
    assert result["failed"] == 1
    assert bc.status == BroadcastStatus.SENT  # the run completed; the send didn't
    deliveries = await broadcast_repo.list_deliveries(db_session, bc.id)
    assert deliveries[0].status == BroadcastDeliveryStatus.FAILED
    assert "wrong file id" in deliveries[0].error


async def test_send_broadcast_skips_blocked_users(db_session: AsyncSession):
    users, _, bc = await _make_broadcast(
        db_session, recipients=2, first_telegram_id=7500
    )
    await user_repo.set_blocked(db_session, users[0], blocked=True)
    bot = _mock_bot()

    result = await broadcast_service.send_broadcast(db_session, bot, bc)

    assert result["sent"] == 1
    assert bc.recipient_count == 1
    assert bot.send_message.await_args_list[0].args[0] == users[1].chat_id


async def test_send_broadcast_fails_when_material_is_gone(db_session: AsyncSession):
    _, _, bc = await _make_broadcast(db_session, recipients=1, first_telegram_id=7600)
    bc.material_id = None
    bot = _mock_bot()

    result = await broadcast_service.send_broadcast(db_session, bot, bc)

    assert result["status"] == BroadcastStatus.FAILED
    assert bc.status == BroadcastStatus.FAILED
    bot.send_message.assert_not_awaited()


async def test_send_broadcast_marks_sending_before_delivering(db_session: AsyncSession):
    """Status must flip to SENDING before the first send, so a concurrent
    scheduler tick can't pick the same broadcast up a second time."""
    _, _, bc = await _make_broadcast(db_session, recipients=1, first_telegram_id=7700)

    seen: list[BroadcastStatus] = []
    bot = _mock_bot()

    async def send(chat_id, *args, **kwargs):
        seen.append(bc.status)
        return MagicMock(message_id=99)

    bot.send_message = AsyncMock(side_effect=send)

    await broadcast_service.send_broadcast(db_session, bot, bc)

    assert seen == [BroadcastStatus.SENDING]


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "result,expected_fragment",
    [
        ({"sent": 5, "failed": 0, "status": BroadcastStatus.SENT}, "all 5"),
        ({"sent": 3, "failed": 2, "status": BroadcastStatus.SENT}, "3 of 5"),
        ({"sent": 0, "failed": 4, "status": BroadcastStatus.SENT}, "all 4"),
        ({"sent": 0, "failed": 0, "status": BroadcastStatus.SENT}, "No one to send to"),
        ({"sent": 0, "failed": 0, "status": BroadcastStatus.FAILED}, "failed"),
    ],
)
def test_format_report(result: dict, expected_fragment: str):
    assert expected_fragment in broadcast_service.format_report(result)


async def test_notify_result_swallows_send_failures():
    """A failed report must never bubble up and break the sending flow."""
    bot = _mock_bot()
    bot.send_message = AsyncMock(side_effect=RuntimeError("chat not found"))

    await broadcast_service.notify_result(
        bot, 123, {"sent": 1, "failed": 0, "status": BroadcastStatus.SENT}
    )


# ---------------------------------------------------------------------------
# scheduler integration
# ---------------------------------------------------------------------------


async def test_scheduler_sends_due_broadcast_and_reports_to_admin(
    db_session: AsyncSession,
):
    from app.services import scheduler as scheduler_service

    _, _, bc = await _make_broadcast(
        db_session, recipients=2, first_telegram_id=7800, notify_chat_id=999
    )
    bc.status = BroadcastStatus.SCHEDULED
    await db_session.flush()

    bot = _mock_bot()
    result = await scheduler_service.process_due_broadcasts(db_session, bot)

    assert result["processed"] == 1
    assert result["recipients_sent"] == 2
    # 2 recipients + 1 report back to the admin chat
    assert bot.send_message.await_count == 3
    report = bot.send_message.await_args_list[-1]
    assert report.args[0] == 999
    assert "all 2" in report.args[1]


async def test_scheduler_does_not_report_when_no_notify_chat(
    db_session: AsyncSession,
):
    from app.services import scheduler as scheduler_service

    _, _, bc = await _make_broadcast(db_session, recipients=1, first_telegram_id=7900)
    bc.status = BroadcastStatus.SCHEDULED
    await db_session.flush()

    bot = _mock_bot()
    await scheduler_service.process_due_broadcasts(db_session, bot)

    assert bot.send_message.await_count == 1  # recipient only, no report
