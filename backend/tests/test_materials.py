from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers.admin.materials import delete_material
from app.db.base import Base
from app.models.broadcast import Broadcast, BroadcastStatus
from app.models.enums import MaterialKind
from app.models.material import Material
from app.models.scheduled_message import ScheduledMessage
from app.models.sequence import Sequence, SequenceStep
from app.models.user import User
from app.services.automation import enroll_user_in_sequence


@pytest.fixture
async def fk_enforced_session():
    """A SQLite session with FK enforcement turned on.

    SQLite ignores foreign key constraints by default (unlike Postgres, which
    production runs on and does enforce them), so this fixture opts a single
    engine into PRAGMA foreign_keys=ON to reproduce the SET NULL / RESTRICT
    behavior that materials.id references rely on in production.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _make_material(session: AsyncSession, name: str = "Msg") -> Material:
    material = Material(name=name, kind=MaterialKind.TEXT, body="hi")
    session.add(material)
    await session.flush()
    return material


async def _make_user(session: AsyncSession) -> User:
    user = User(telegram_id=123, chat_id=123, first_name="Test")
    session.add(user)
    await session.flush()
    return user


async def test_delete_material_used_in_active_flow_returns_409(
    fk_enforced_session: AsyncSession,
) -> None:
    session = fk_enforced_session
    material = await _make_material(session, "In active flow")
    sequence = Sequence(name="Welcome flow", is_active=True)
    session.add(sequence)
    await session.flush()
    session.add(
        SequenceStep(
            sequence_id=sequence.id, position=1, delay_minutes=0, material_id=material.id
        )
    )
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await delete_material(material.id, session=session, _=None)

    assert exc_info.value.status_code == 409
    assert "active auto-flow" in exc_info.value.detail
    assert "Welcome flow" in exc_info.value.detail
    # Material must NOT have been deleted.
    assert await session.get(Material, material.id) is not None


async def test_delete_material_used_only_in_inactive_flow_succeeds(
    fk_enforced_session: AsyncSession,
) -> None:
    session = fk_enforced_session
    material = await _make_material(session, "In dormant flow")
    sequence = Sequence(name="Dormant flow", is_active=False)
    session.add(sequence)
    await session.flush()
    step = SequenceStep(
        sequence_id=sequence.id, position=1, delay_minutes=0, material_id=material.id
    )
    session.add(step)
    await session.commit()

    await delete_material(material.id, session=session, _=None)

    assert await session.get(Material, material.id) is None
    # The orphaned step survives with material_id nulled out.
    await session.refresh(step)
    assert step.material_id is None


async def test_delete_material_referenced_by_broadcast_succeeds(
    fk_enforced_session: AsyncSession,
) -> None:
    session = fk_enforced_session
    material = await _make_material(session, "Broadcast msg")
    broadcast = Broadcast(
        name="Old broadcast",
        material_id=material.id,
        status=BroadcastStatus.SENT,
    )
    session.add(broadcast)
    await session.commit()

    await delete_material(material.id, session=session, _=None)

    assert await session.get(Material, material.id) is None
    await session.refresh(broadcast)
    assert broadcast.material_id is None


async def test_delete_material_referenced_by_scheduled_message_succeeds(
    fk_enforced_session: AsyncSession,
) -> None:
    session = fk_enforced_session
    material = await _make_material(session, "Scheduled msg")
    user = await _make_user(session)
    msg = ScheduledMessage(
        user_id=user.id,
        material_id=material.id,
        scheduled_at=datetime.now(timezone.utc),
    )
    session.add(msg)
    await session.commit()

    await delete_material(material.id, session=session, _=None)

    assert await session.get(Material, material.id) is None
    await session.refresh(msg)
    assert msg.material_id is None


async def test_delete_unused_material_succeeds(
    fk_enforced_session: AsyncSession,
) -> None:
    session = fk_enforced_session
    material = await _make_material(session, "Unused")
    await session.commit()

    await delete_material(material.id, session=session, _=None)

    assert await session.get(Material, material.id) is None


async def test_enroll_skips_steps_with_null_material(
    fk_enforced_session: AsyncSession,
) -> None:
    """A reactivated flow whose step lost its material must not crash enrollment."""
    session = fk_enforced_session
    user = await _make_user(session)
    material = await _make_material(session, "Still here")
    sequence = Sequence(name="Reactivated flow", is_active=True)
    session.add(sequence)
    await session.flush()
    # One orphaned step (material deleted -> NULL) and one valid step.
    session.add(
        SequenceStep(
            sequence_id=sequence.id, position=1, delay_minutes=0, material_id=None
        )
    )
    session.add(
        SequenceStep(
            sequence_id=sequence.id, position=2, delay_minutes=5, material_id=material.id
        )
    )
    await session.commit()

    messages = await enroll_user_in_sequence(session, user, sequence)

    # Only the valid step is scheduled; the NULL-material step is skipped.
    assert len(messages) == 1
    assert messages[0].material_id == material.id
