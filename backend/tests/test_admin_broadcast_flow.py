"""End-to-end tests of the bot's "📣 Send to everyone" admin flow.

Updates are fed through the real Dispatcher so router ordering and FSM state
transitions are exercised, not just the handler bodies.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from aiogram.types import Update

from app.models.broadcast import BroadcastStatus
from app.telegram import handlers
from app.telegram.bot import get_dispatcher

_ADMIN_ID = 4242
_ADMIN_PASSWORD = "bot-admin-pass"


@pytest_asyncio.fixture(autouse=True)
async def _admin_session(_create_app_tables):
    from app.config import get_settings

    settings = get_settings()
    original = settings.ADMIN_BOT_PASSWORD
    settings.ADMIN_BOT_PASSWORD = _ADMIN_PASSWORD
    handlers._admin_sessions.add(_ADMIN_ID)
    yield
    handlers._admin_sessions.discard(_ADMIN_ID)
    settings.ADMIN_BOT_PASSWORD = original


@pytest_asyncio.fixture
async def bot() -> AsyncMock:
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    bot.copy_message = AsyncMock(return_value=MagicMock(message_id=1))
    bot.edit_message_reply_markup = AsyncMock(return_value=MagicMock(message_id=1))
    bot.answer_callback_query = AsyncMock(return_value=True)
    return bot


@pytest_asyncio.fixture(autouse=True)
async def _clear_state():
    """The Dispatcher is a process-wide singleton, so wipe its in-memory FSM
    data between tests to keep them independent."""
    yield
    storage = get_dispatcher().storage
    storage.storage.clear()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_create_app_tables):
    """These tests run against the app's process-wide engine, so rows have to be
    cleared between them or recipient counts bleed across tests."""
    from sqlalchemy import delete

    from app.db.session import get_session_factory
    from app.models.broadcast import Broadcast, BroadcastDelivery
    from app.models.material import Material
    from app.models.user import User

    async def wipe() -> None:
        factory = get_session_factory()
        async with factory() as session:
            for model in (BroadcastDelivery, Broadcast, Material, User):
                await session.execute(delete(model))
            await session.commit()

    await wipe()
    yield
    await wipe()


def _message_update(text: str | None = None, *, update_id: int = 1, **extra) -> Update:
    message = {
        "message_id": update_id,
        "date": 1700000000,
        "chat": {"id": _ADMIN_ID, "type": "private"},
        "from": {"id": _ADMIN_ID, "is_bot": False, "first_name": "Teacher"},
        **extra,
    }
    if text is not None:
        message["text"] = text
    return Update.model_validate({"update_id": update_id, "message": message})


def _callback_update(data: str, *, update_id: int = 900) -> Update:
    return Update.model_validate(
        {
            "update_id": update_id,
            "callback_query": {
                "id": str(update_id),
                "from": {"id": _ADMIN_ID, "is_bot": False, "first_name": "Teacher"},
                "chat_instance": "1",
                "data": data,
                "message": {
                    "message_id": update_id,
                    "date": 1700000000,
                    "chat": {"id": _ADMIN_ID, "type": "private"},
                    "from": {"id": 1, "is_bot": True, "first_name": "Bot"},
                    "text": "Ready to broadcast",
                },
            },
        }
    )


async def _feed(bot: AsyncMock, update: Update) -> None:
    await get_dispatcher().feed_update(bot=bot, update=update)


def _replies(bot: AsyncMock) -> list[str]:
    """Text of every message the bot sent to the admin.

    `message.answer(...)` is dispatched by awaiting the bot itself with a
    SendMessage object, while `bot.send_message(...)` (used by the delivery
    report) hits the named attribute — collect both.
    """
    texts: list[str] = []
    for call in bot.await_args_list:
        method = call.args[0] if call.args else None
        text = getattr(method, "text", None)
        if text is not None:
            texts.append(text)
    for call in bot.send_message.await_args_list:
        texts.append(call.args[1] if len(call.args) > 1 else call.kwargs.get("text", ""))
    return texts


async def _make_subscribers(count: int, first_telegram_id: int = 8100) -> list:
    from app.db.session import get_session_factory
    from app.repositories import users as user_repo

    factory = get_session_factory()
    async with factory() as session:
        users = [
            await user_repo.create(
                session,
                telegram_id=first_telegram_id + i,
                chat_id=first_telegram_id + i,
            )
            for i in range(count)
        ]
        await session.commit()
        return users


async def _latest_broadcast():
    from app.db.session import get_session_factory
    from app.repositories import broadcasts as broadcast_repo

    factory = get_session_factory()
    async with factory() as session:
        items = await broadcast_repo.list_broadcasts(session)
        return items[0] if items else None


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_button_prompts_for_the_post(bot: AsyncMock):
    await _make_subscribers(2, first_telegram_id=8100)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL))

    assert "Broadcast mode" in _replies(bot)[-1]


async def test_full_flow_sends_to_every_subscriber_and_reports(bot: AsyncMock):
    users = await _make_subscribers(3, first_telegram_id=8200)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Lesson starts tomorrow!", update_id=2))

    # Confirmation is requested before anything is sent.
    assert "Send it?" in _replies(bot)[-1]
    assert bot.copy_message.await_count == 0

    await _feed(bot, _callback_update("bcast:send"))

    # Each subscriber got the post (copy_message, so it arrives verbatim).
    copied_to = {c.args[0] for c in bot.copy_message.await_args_list}
    assert copied_to == {u.chat_id for u in users}

    assert "✅ Sent to all 3 subscribers." in _replies(bot)[-1]

    bc = await _latest_broadcast()
    assert bc.status == BroadcastStatus.SENT
    assert bc.success_count == 3
    assert bc.failure_count == 0


async def test_report_shows_partial_failure(bot: AsyncMock):
    users = await _make_subscribers(3, first_telegram_id=8300)
    from aiogram.exceptions import TelegramForbiddenError

    async def copy(chat_id, *args, **kwargs):
        if chat_id == users[0].chat_id:
            raise TelegramForbiddenError(method=MagicMock(), message="blocked")
        return MagicMock(message_id=1)

    bot.copy_message = AsyncMock(side_effect=copy)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Hi", update_id=2))
    await _feed(bot, _callback_update("bcast:send"))

    report = _replies(bot)[-1]
    assert "Sent to 2 of 3" in report
    assert "1 failed" in report


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------


async def test_nothing_is_sent_until_confirmed(bot: AsyncMock):
    await _make_subscribers(2, first_telegram_id=8400)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Draft post", update_id=2))

    bot.copy_message.assert_not_awaited()
    assert await _latest_broadcast() is None


async def test_cancel_button_aborts_without_sending(bot: AsyncMock):
    await _make_subscribers(2, first_telegram_id=8500)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Draft post", update_id=2))
    await _feed(bot, _callback_update("bcast:cancel"))

    bot.copy_message.assert_not_awaited()
    assert "nothing was sent" in _replies(bot)[-1]
    assert await _latest_broadcast() is None


async def test_cancel_keyboard_button_exits_broadcast_mode(bot: AsyncMock):
    """Tapping Cancel while waiting for the post must not save it as a message."""
    await _make_subscribers(1, first_telegram_id=8600)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update(handlers._BTN_CANCEL, update_id=2))
    await _feed(bot, _message_update("Now this is a normal save", update_id=3))

    # Back in save mode: the bot asks for a name rather than a confirmation.
    assert "What do you want to call this message?" in _replies(bot)[-1]


async def test_confirm_without_a_pending_broadcast_is_rejected(bot: AsyncMock):
    await _make_subscribers(1, first_telegram_id=8700)

    await _feed(bot, _callback_update("bcast:send"))

    bot.copy_message.assert_not_awaited()
    assert await _latest_broadcast() is None


async def test_non_admin_cannot_confirm_a_broadcast(bot: AsyncMock):
    """The callback carries no admin session — it must be refused outright."""
    await _make_subscribers(1, first_telegram_id=8800)
    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Post", update_id=2))

    handlers._admin_sessions.discard(_ADMIN_ID)
    await _feed(bot, _callback_update("bcast:send"))

    bot.copy_message.assert_not_awaited()
    assert await _latest_broadcast() is None


async def test_no_subscribers_short_circuits(bot: AsyncMock):
    await _feed(bot, _message_update(handlers._BTN_SEND_ALL))

    assert "no active subscribers" in _replies(bot)[-1]


async def test_large_audience_is_queued_for_the_scheduler(
    bot: AsyncMock, monkeypatch: pytest.MonkeyPatch
):
    """Sending inline would risk a webhook timeout and a duplicated broadcast."""
    from app.services import broadcast as broadcast_service

    monkeypatch.setattr(broadcast_service, "INLINE_SEND_LIMIT", 2)
    await _make_subscribers(3, first_telegram_id=8900)

    await _feed(bot, _message_update(handlers._BTN_SEND_ALL, update_id=1))
    await _feed(bot, _message_update("Big announcement", update_id=2))
    await _feed(bot, _callback_update("bcast:send"))

    bot.copy_message.assert_not_awaited()
    assert "Queued for 3 subscribers" in _replies(bot)[-1]

    bc = await _latest_broadcast()
    assert bc.status == BroadcastStatus.SCHEDULED
    assert bc.notify_chat_id == _ADMIN_ID


async def test_saving_a_message_still_works(bot: AsyncMock):
    """The broadcast flow must not shadow the existing save-a-message flow."""
    from app.db.session import get_session_factory
    from app.repositories import materials as material_repo

    await _feed(bot, _message_update("A lesson", update_id=1))
    assert "What do you want to call this message?" in _replies(bot)[-1]

    await _feed(bot, _message_update("Lesson 1", update_id=2))
    assert "saved as a Text message" in _replies(bot)[-1]

    factory = get_session_factory()
    async with factory() as session:
        names = [m.name for m in await material_repo.list_materials(session)]
    assert "Lesson 1" in names

