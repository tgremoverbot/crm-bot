from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialKind, ScheduledMessageStatus, SequenceTriggerKind
from app.repositories import campaigns as campaign_repo
from app.repositories import events as event_repo
from app.repositories import materials as material_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import sequences as seq_repo
from app.repositories import users as user_repo
from app.services.automation import enroll_user_in_sequence
from app.telegram import service as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_material(session: AsyncSession, name: str = "Mat") -> object:
    return await material_repo.create(
        session, name=name, kind=MaterialKind.TEXT, body="Hello"
    )


async def _make_user(session: AsyncSession, telegram_id: int = 1001) -> object:
    return await user_repo.create(
        session, telegram_id=telegram_id, chat_id=telegram_id
    )


async def _make_sequence_with_steps(
    session: AsyncSession, step_delays: list[int]
) -> object:
    seq = await seq_repo.create(
        session,
        name="Test Seq",
        trigger_kind=SequenceTriggerKind.CAMPAIGN_JOIN,
        is_active=True,
    )
    mat = await _make_material(session, "StepMat")
    for i, delay in enumerate(step_delays):
        await seq_repo.add_step(
            session,
            sequence_id=seq.id,
            position=i + 1,
            delay_minutes=delay,
            material_id=mat.id,
        )
    return seq


# ---------------------------------------------------------------------------
# enroll_user_in_sequence
# ---------------------------------------------------------------------------


async def test_enroll_creates_one_message_per_step(db_session: AsyncSession):
    user = await _make_user(db_session, 2001)
    seq = await _make_sequence_with_steps(db_session, [0, 60, 120])

    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    messages = await enroll_user_in_sequence(db_session, user, seq, now=now)

    assert len(messages) == 3
    assert messages[0].scheduled_at == now + timedelta(minutes=0)
    assert messages[1].scheduled_at == now + timedelta(minutes=60)
    assert messages[2].scheduled_at == now + timedelta(minutes=120)


async def test_enroll_sets_source_kind_sequence(db_session: AsyncSession):
    from app.models.enums import SourceKind

    user = await _make_user(db_session, 2002)
    seq = await _make_sequence_with_steps(db_session, [30])
    messages = await enroll_user_in_sequence(db_session, user, seq)

    assert messages[0].source_kind == SourceKind.SEQUENCE
    assert messages[0].source_id == seq.id


async def test_enroll_logs_sequence_enrolled_event(db_session: AsyncSession):
    user = await _make_user(db_session, 2003)
    seq = await _make_sequence_with_steps(db_session, [0, 45])
    await enroll_user_in_sequence(db_session, user, seq)

    logs = await event_repo.list_for_user(db_session, user.id)
    types = [e.type for e in logs]
    assert "sequence_enrolled" in types


async def test_enroll_empty_sequence_creates_no_messages(db_session: AsyncSession):
    user = await _make_user(db_session, 2004)
    seq = await _make_sequence_with_steps(db_session, [])
    messages = await enroll_user_in_sequence(db_session, user, seq)
    assert messages == []


# ---------------------------------------------------------------------------
# handle_start + default_sequence_id
# ---------------------------------------------------------------------------


async def test_handle_start_enrolls_new_user_in_campaign_sequence(
    db_session: AsyncSession,
):
    seq = await _make_sequence_with_steps(db_session, [0, 60])
    campaign = await campaign_repo.create(
        db_session,
        name="Promo",
        slug="promo-seq",
        is_active=True,
        default_sequence_id=seq.id,
    )

    user, is_new, detected = await svc.handle_start(
        db_session, telegram_id=3001, chat_id=3001, campaign_slug="promo-seq"
    )

    assert is_new is True
    assert detected is not None
    messages = await scheduled_repo.list_due(
        db_session,
        now=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    user_msgs = [m for m in messages if m.user_id == user.id]
    assert len(user_msgs) == 2


async def test_handle_start_does_not_enroll_existing_user(db_session: AsyncSession):
    seq = await _make_sequence_with_steps(db_session, [0])
    await campaign_repo.create(
        db_session,
        name="Promo2",
        slug="promo-exist",
        is_active=True,
        default_sequence_id=seq.id,
    )

    # First /start — new user
    await svc.handle_start(
        db_session, telegram_id=3002, chat_id=3002, campaign_slug="promo-exist"
    )
    # Second /start — existing user, should not re-enroll
    await svc.handle_start(
        db_session, telegram_id=3002, chat_id=3002, campaign_slug="promo-exist"
    )

    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    user_msgs = [
        m
        for m in messages
        if str(m.user_id)
        in [
            str(u.id)
            async for u in _iter_users_with_telegram_id(db_session, 3002)
        ]
    ]
    # Exactly 1 message from the first enrolment
    assert len(user_msgs) == 1


async def _iter_users_with_telegram_id(session, telegram_id):
    from app.repositories import users as ur

    u = await ur.get_by_telegram_id(session, telegram_id)
    if u:
        yield u


async def test_handle_start_skips_enrollment_for_inactive_sequence(
    db_session: AsyncSession,
):
    seq = await seq_repo.create(
        db_session,
        name="Inactive Seq",
        trigger_kind=SequenceTriggerKind.CAMPAIGN_JOIN,
        is_active=False,
    )
    await campaign_repo.create(
        db_session,
        name="Promo3",
        slug="promo-inactive",
        is_active=True,
        default_sequence_id=seq.id,
    )

    user, is_new, _ = await svc.handle_start(
        db_session, telegram_id=3003, chat_id=3003, campaign_slug="promo-inactive"
    )
    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    user_msgs = [m for m in messages if m.user_id == user.id]
    assert user_msgs == []
