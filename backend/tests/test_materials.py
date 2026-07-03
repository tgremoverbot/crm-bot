from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routers.admin.materials import delete_material
from app.db.base import Base
from app.models.enums import MaterialKind
from app.models.material import Material
from app.models.sequence import Sequence, SequenceStep


@pytest.fixture
async def fk_enforced_session():
    """A SQLite session with FK enforcement turned on.

    SQLite ignores foreign key constraints by default (unlike Postgres, which
    production runs on and does enforce them), so this fixture opts a single
    engine into PRAGMA foreign_keys=ON to reproduce the RESTRICT behavior that
    materials.id references rely on in production.
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


async def test_delete_in_use_material_returns_409(fk_enforced_session: AsyncSession) -> None:
    session = fk_enforced_session
    material = Material(name="In use", kind=MaterialKind.TEXT, body="hi")
    session.add(material)
    await session.flush()
    sequence = Sequence(name="Flow")
    session.add(sequence)
    await session.flush()
    session.add(
        SequenceStep(sequence_id=sequence.id, position=1, delay_minutes=0, material_id=material.id)
    )
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await delete_material(material.id, session=session, _=None)

    assert exc_info.value.status_code == 409
    assert "used in" in exc_info.value.detail


async def test_delete_unused_material_succeeds(fk_enforced_session: AsyncSession) -> None:
    session = fk_enforced_session
    material = Material(name="Unused", kind=MaterialKind.TEXT, body="hi")
    session.add(material)
    await session.commit()

    await delete_material(material.id, session=session, _=None)

    assert await session.get(Material, material.id) is None
