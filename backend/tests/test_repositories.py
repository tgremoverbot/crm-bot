from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import (
    MaterialKind,
    ScheduledMessageStatus,
    SequenceTriggerKind,
    SourceKind,
)
from app.repositories import (
    admin_users as admin_repo,
    broadcasts as broadcast_repo,
    campaigns as campaign_repo,
    events as event_repo,
    materials as material_repo,
    scheduled as scheduled_repo,
    segments as segment_repo,
    sequences as sequence_repo,
    users as user_repo,
)


@pytest.mark.asyncio
async def test_admin_user_repo(db_session):
    admin = await admin_repo.create(
        db_session, email="Admin@Example.com", password_hash="hash"
    )
    await db_session.commit()
    assert admin.email == "admin@example.com"

    found = await admin_repo.get_by_email(db_session, "admin@example.com")
    assert found is not None
    assert found.id == admin.id


@pytest.mark.asyncio
async def test_user_repo_basic_ops(db_session):
    user = await user_repo.create(
        db_session, telegram_id=12345, chat_id=12345, username="alice"
    )
    await db_session.commit()

    found = await user_repo.get_by_telegram_id(db_session, 12345)
    assert found is not None
    assert found.id == user.id

    await user_repo.set_blocked(db_session, found, True)
    assert found.is_blocked is True

    users = await user_repo.list_users(db_session)
    assert len(users) == 1


@pytest.mark.asyncio
async def test_campaign_repo(db_session):
    c = await campaign_repo.create(db_session, name="Insta Q3", slug="insta-q3")
    await db_session.commit()
    assert (await campaign_repo.get_by_slug(db_session, "insta-q3")).id == c.id
    assert (await campaign_repo.get_by_slug(db_session, "missing")) is None

    active = await campaign_repo.list_campaigns(db_session, is_active=True)
    assert len(active) == 1


@pytest.mark.asyncio
async def test_material_repo(db_session):
    m = await material_repo.create(
        db_session, name="Hello", kind=MaterialKind.TEXT, body="hi"
    )
    await db_session.commit()
    assert (await material_repo.get_by_id(db_session, m.id)).body == "hi"
    assert len(await material_repo.list_materials(db_session)) == 1


@pytest.mark.asyncio
async def test_segment_repo_add_user_idempotent(db_session):
    user = await user_repo.create(db_session, telegram_id=1, chat_id=1)
    seg = await segment_repo.create(db_session, name="Beginners")
    await db_session.commit()

    first = await segment_repo.add_user(
        db_session, user_id=user.id, segment_id=seg.id
    )
    second = await segment_repo.add_user(
        db_session, user_id=user.id, segment_id=seg.id
    )
    await db_session.commit()
    assert first is not None
    assert second is None

    in_seg = await segment_repo.list_users_in_segment(db_session, seg.id)
    assert len(in_seg) == 1


@pytest.mark.asyncio
async def test_sequence_repo_with_steps(db_session):
    material = await material_repo.create(
        db_session, name="step", kind=MaterialKind.TEXT, body="x"
    )
    seq = await sequence_repo.create(
        db_session, name="Welcome", trigger_kind=SequenceTriggerKind.CAMPAIGN_JOIN
    )
    await sequence_repo.add_step(
        db_session,
        sequence_id=seq.id,
        position=1,
        delay_minutes=0,
        material_id=material.id,
    )
    await sequence_repo.add_step(
        db_session,
        sequence_id=seq.id,
        position=2,
        delay_minutes=60,
        material_id=material.id,
    )
    await db_session.commit()

    steps = await sequence_repo.list_steps(db_session, seq.id)
    assert [s.position for s in steps] == [1, 2]


@pytest.mark.asyncio
async def test_scheduled_repo_lifecycle(db_session):
    user = await user_repo.create(db_session, telegram_id=7, chat_id=7)
    material = await material_repo.create(
        db_session, name="m", kind=MaterialKind.TEXT, body="x"
    )
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    future = datetime.now(timezone.utc) + timedelta(hours=1)

    due_msg = await scheduled_repo.create(
        db_session,
        user_id=user.id,
        material_id=material.id,
        scheduled_at=past,
        source_kind=SourceKind.MANUAL,
        idempotency_key="manual:1",
    )
    await scheduled_repo.create(
        db_session,
        user_id=user.id,
        material_id=material.id,
        scheduled_at=future,
        source_kind=SourceKind.MANUAL,
        idempotency_key="manual:2",
    )
    await db_session.commit()

    due = await scheduled_repo.list_due(db_session)
    assert [m.id for m in due] == [due_msg.id]

    await scheduled_repo.mark_sent(db_session, due_msg)
    await db_session.commit()
    assert due_msg.status == ScheduledMessageStatus.SENT
    assert due_msg.sent_at is not None


@pytest.mark.asyncio
async def test_broadcast_repo(db_session):
    material = await material_repo.create(
        db_session, name="b", kind=MaterialKind.TEXT, body="x"
    )
    user = await user_repo.create(db_session, telegram_id=8, chat_id=8)
    bc = await broadcast_repo.create(
        db_session, name="Promo", material_id=material.id
    )
    await broadcast_repo.add_delivery(
        db_session, broadcast_id=bc.id, user_id=user.id
    )
    await db_session.commit()

    deliveries = await broadcast_repo.list_deliveries(db_session, bc.id)
    assert len(deliveries) == 1


@pytest.mark.asyncio
async def test_event_repo_log_and_filters(db_session):
    user = await user_repo.create(db_session, telegram_id=9, chat_id=9)
    await event_repo.log(
        db_session, type="campaign.joined", user_id=user.id, payload={"slug": "x"}
    )
    await event_repo.log(db_session, type="campaign.joined", user_id=None)
    await event_repo.log(db_session, type="user.blocked_bot", user_id=user.id)
    await db_session.commit()

    by_type = await event_repo.list_by_type(db_session, "campaign.joined")
    assert len(by_type) == 2

    by_user = await event_repo.list_for_user(db_session, user.id)
    assert len(by_user) == 2
