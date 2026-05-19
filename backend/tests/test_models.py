from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AdminUser,
    Broadcast,
    BroadcastDelivery,
    BroadcastStatus,
    Campaign,
    EventLog,
    Material,
    MaterialKind,
    ScheduledMessage,
    ScheduledMessageStatus,
    Segment,
    Sequence,
    SequenceStep,
    SequenceTriggerKind,
    SourceKind,
    User,
    UserSegment,
)


@pytest.mark.asyncio
async def test_create_admin_user(db_session):
    admin = AdminUser(email="a@b.test", password_hash="x")
    db_session.add(admin)
    await db_session.commit()
    assert isinstance(admin.id, uuid.UUID)
    assert admin.is_active is True
    assert admin.created_at is not None


@pytest.mark.asyncio
async def test_admin_email_unique(db_session):
    db_session.add(AdminUser(email="dup@test", password_hash="a"))
    await db_session.commit()
    db_session.add(AdminUser(email="dup@test", password_hash="b"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_telegram_id_unique(db_session):
    db_session.add(User(telegram_id=42, chat_id=42))
    await db_session.commit()
    db_session.add(User(telegram_id=42, chat_id=99))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_campaign_slug_unique(db_session):
    db_session.add(Campaign(name="A", slug="dup"))
    await db_session.commit()
    db_session.add(Campaign(name="B", slug="dup"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_full_sequence_graph(db_session):
    material = Material(name="Welcome", kind=MaterialKind.TEXT, body="Hi")
    seq = Sequence(name="Onboard", trigger_kind=SequenceTriggerKind.CAMPAIGN_JOIN)
    db_session.add_all([material, seq])
    await db_session.flush()

    step = SequenceStep(
        sequence_id=seq.id, position=1, delay_minutes=0, material_id=material.id
    )
    db_session.add(step)
    await db_session.commit()

    fetched = (
        await db_session.execute(
            select(SequenceStep).where(SequenceStep.sequence_id == seq.id)
        )
    ).scalar_one()
    assert fetched.position == 1
    assert fetched.material_id == material.id


@pytest.mark.asyncio
async def test_sequence_step_unique_position(db_session):
    material = Material(name="M", kind=MaterialKind.TEXT, body="x")
    seq = Sequence(name="S")
    db_session.add_all([material, seq])
    await db_session.flush()

    db_session.add(
        SequenceStep(
            sequence_id=seq.id, position=1, delay_minutes=0, material_id=material.id
        )
    )
    await db_session.commit()
    db_session.add(
        SequenceStep(
            sequence_id=seq.id, position=1, delay_minutes=5, material_id=material.id
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_scheduled_message_defaults(db_session):
    material = Material(name="M", kind=MaterialKind.TEXT, body="x")
    user = User(telegram_id=1, chat_id=1)
    db_session.add_all([material, user])
    await db_session.flush()

    msg = ScheduledMessage(
        user_id=user.id,
        material_id=material.id,
        scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        source_kind=SourceKind.MANUAL,
    )
    db_session.add(msg)
    await db_session.commit()

    assert msg.status == ScheduledMessageStatus.PENDING
    assert msg.attempts == 0


@pytest.mark.asyncio
async def test_user_segment_unique(db_session):
    seg = Segment(name="VIP")
    user = User(telegram_id=10, chat_id=10)
    db_session.add_all([seg, user])
    await db_session.flush()

    db_session.add(UserSegment(user_id=user.id, segment_id=seg.id))
    await db_session.commit()
    db_session.add(UserSegment(user_id=user.id, segment_id=seg.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_broadcast_and_delivery(db_session):
    material = Material(name="M", kind=MaterialKind.TEXT, body="x")
    user = User(telegram_id=22, chat_id=22)
    db_session.add_all([material, user])
    await db_session.flush()

    bc = Broadcast(name="Promo", material_id=material.id)
    db_session.add(bc)
    await db_session.flush()
    assert bc.status == BroadcastStatus.DRAFT

    delivery = BroadcastDelivery(broadcast_id=bc.id, user_id=user.id)
    db_session.add(delivery)
    await db_session.commit()
    assert delivery.id is not None


@pytest.mark.asyncio
async def test_event_log_payload_roundtrip(db_session):
    ev = EventLog(type="campaign.joined", payload={"campaign_id": "abc"})
    db_session.add(ev)
    await db_session.commit()
    fetched = (
        await db_session.execute(select(EventLog).where(EventLog.id == ev.id))
    ).scalar_one()
    assert fetched.payload == {"campaign_id": "abc"}
    assert fetched.type == "campaign.joined"
