from __future__ import annotations

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import BroadcastStatus
from app.models.enums import MaterialKind
from app.repositories import broadcasts as broadcast_repo
from app.repositories import materials as material_repo
from app.repositories import users as user_repo
from app.services import scheduler as scheduler_service

_INTERNAL_KEY = "test-internal-key-abc123"
_NOW = datetime.now(timezone.utc)


async def _make_broadcast(
    session: AsyncSession,
    *,
    status: BroadcastStatus,
    finished_at: datetime | None,
    created_at: datetime | None = None,
    name: str = "Announcement",
):
    mat = await material_repo.create(
        session, name=f"mat-{name}", kind=MaterialKind.TEXT, body="hi"
    )
    bc = await broadcast_repo.create(session, name=name, material_id=mat.id)
    bc.status = status
    bc.finished_at = finished_at
    if created_at is not None:
        bc.created_at = created_at
    await session.flush()
    return bc


async def test_deletes_old_sent_broadcast(db_session: AsyncSession):
    old = await _make_broadcast(
        db_session, status=BroadcastStatus.SENT, finished_at=_NOW - timedelta(days=100)
    )

    result = await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert result["deleted"] == 1
    assert await broadcast_repo.get_by_id(db_session, old.id) is None


async def test_keeps_recent_sent_broadcast(db_session: AsyncSession):
    recent = await _make_broadcast(
        db_session, status=BroadcastStatus.SENT, finished_at=_NOW - timedelta(days=10)
    )

    result = await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert result["deleted"] == 0
    assert await broadcast_repo.get_by_id(db_session, recent.id) is not None


async def test_keeps_old_draft_broadcast(db_session: AsyncSession):
    draft = await _make_broadcast(
        db_session,
        status=BroadcastStatus.DRAFT,
        finished_at=None,
        created_at=_NOW - timedelta(days=200),
    )

    result = await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert result["deleted"] == 0
    assert await broadcast_repo.get_by_id(db_session, draft.id) is not None


async def test_keeps_old_scheduled_broadcast(db_session: AsyncSession):
    scheduled = await _make_broadcast(
        db_session,
        status=BroadcastStatus.SCHEDULED,
        finished_at=None,
        created_at=_NOW - timedelta(days=200),
    )

    result = await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert result["deleted"] == 0
    assert await broadcast_repo.get_by_id(db_session, scheduled.id) is not None


async def test_falls_back_to_created_at_when_no_finished_at(db_session: AsyncSession):
    old_failed = await _make_broadcast(
        db_session,
        status=BroadcastStatus.FAILED,
        finished_at=None,
        created_at=_NOW - timedelta(days=120),
    )

    result = await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert result["deleted"] == 1
    assert await broadcast_repo.get_by_id(db_session, old_failed.id) is None


async def test_deletes_associated_deliveries(db_session: AsyncSession):
    old = await _make_broadcast(
        db_session, status=BroadcastStatus.SENT, finished_at=_NOW - timedelta(days=100)
    )
    user = await user_repo.create(db_session, telegram_id=9001, chat_id=9001)
    await broadcast_repo.add_delivery(db_session, broadcast_id=old.id, user_id=user.id)
    await db_session.flush()

    assert len(await broadcast_repo.list_deliveries(db_session, old.id)) == 1

    await scheduler_service.cleanup_old_broadcasts(db_session, retention_days=90)

    assert len(await broadcast_repo.list_deliveries(db_session, old.id)) == 0


async def test_dry_run_does_not_delete(db_session: AsyncSession):
    old = await _make_broadcast(
        db_session, status=BroadcastStatus.SENT, finished_at=_NOW - timedelta(days=100)
    )

    result = await scheduler_service.cleanup_old_broadcasts(
        db_session, retention_days=90, dry_run=True
    )

    assert result["dry_run"] is True
    assert result["deleted"] == 0
    assert result["eligible"] == 1
    assert await broadcast_repo.get_by_id(db_session, old.id) is not None


async def test_process_scheduled_endpoint_includes_cleanup(client: AsyncClient, admin_user):
    resp = await client.post(
        "/internal/process-scheduled",
        headers={"X-Internal-Api-Key": _INTERNAL_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "broadcast_cleanup" in data
    assert "deleted" in data["broadcast_cleanup"]
