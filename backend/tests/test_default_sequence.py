from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialKind, SequenceTriggerKind
from app.repositories import app_settings as settings_repo
from app.repositories import materials as material_repo
from app.repositories import scheduled as scheduled_repo
from app.repositories import sequences as seq_repo
from app.telegram import service as svc


async def _make_sequence_with_step(session: AsyncSession, *, is_active: bool = True):
    seq = await seq_repo.create(
        session,
        name="Default Seq",
        trigger_kind=SequenceTriggerKind.CAMPAIGN_JOIN,
        is_active=is_active,
    )
    mat = await material_repo.create(
        session, name="DefaultMat", kind=MaterialKind.TEXT, body="Welcome"
    )
    await seq_repo.add_step(
        session, sequence_id=seq.id, position=1, delay_minutes=0, material_id=mat.id
    )
    return seq


async def test_organic_start_enrolls_in_default_sequence(db_session: AsyncSession):
    seq = await _make_sequence_with_step(db_session)
    await settings_repo.set_default_sequence(db_session, seq.id)

    user, is_new, campaign = await svc.handle_start(
        db_session, telegram_id=6001, chat_id=6001, campaign_slug=None
    )

    assert is_new is True
    assert campaign is None
    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    assert any(m.user_id == user.id for m in messages)


async def test_organic_start_without_default_sequence_enrolls_nothing(
    db_session: AsyncSession,
):
    user, _, _ = await svc.handle_start(
        db_session, telegram_id=6002, chat_id=6002, campaign_slug=None
    )
    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    assert not any(m.user_id == user.id for m in messages)


async def test_organic_start_skips_inactive_default_sequence(db_session: AsyncSession):
    seq = await _make_sequence_with_step(db_session, is_active=False)
    await settings_repo.set_default_sequence(db_session, seq.id)

    user, _, _ = await svc.handle_start(
        db_session, telegram_id=6003, chat_id=6003, campaign_slug=None
    )
    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    assert not any(m.user_id == user.id for m in messages)


async def test_invite_link_start_does_not_use_default_sequence(
    db_session: AsyncSession,
):
    """A campaign_join (even with an unrecognised/invalid slug) must not fall back
    to the organic-start default sequence — only a completely missing slug should."""
    default_seq = await _make_sequence_with_step(db_session)
    await settings_repo.set_default_sequence(db_session, default_seq.id)

    user, _, campaign = await svc.handle_start(
        db_session, telegram_id=6004, chat_id=6004, campaign_slug="does-not-exist"
    )

    assert campaign is None
    messages = await scheduled_repo.list_due(
        db_session, now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    )
    assert not any(m.user_id == user.id for m in messages)


async def test_get_or_create_singleton_settings(db_session: AsyncSession):
    settings = await settings_repo.get(db_session)
    assert settings.id == 1
    assert settings.default_sequence_id is None

    # Calling again must return the same row, not create a second one
    again = await settings_repo.get(db_session)
    assert again.id == settings.id


async def test_settings_endpoint_requires_auth(client: AsyncClient):
    resp = await client.get("/api/admin/settings")
    assert resp.status_code == 401


async def test_get_settings_defaults_to_null(auth_client: AsyncClient, admin_user):
    resp = await auth_client.get("/api/admin/settings")
    assert resp.status_code == 200
    assert resp.json()["default_sequence_id"] is None


async def test_update_settings_round_trip(auth_client: AsyncClient, admin_user):
    create_resp = await auth_client.post(
        "/api/admin/sequences",
        json={"name": "API Seq", "trigger_kind": "campaign_join", "is_active": True},
    )
    assert create_resp.status_code == 201
    seq_id = create_resp.json()["id"]

    patch_resp = await auth_client.patch(
        "/api/admin/settings", json={"default_sequence_id": seq_id}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["default_sequence_id"] == seq_id

    get_resp = await auth_client.get("/api/admin/settings")
    assert get_resp.json()["default_sequence_id"] == seq_id

    clear_resp = await auth_client.patch(
        "/api/admin/settings", json={"default_sequence_id": None}
    )
    assert clear_resp.json()["default_sequence_id"] is None
