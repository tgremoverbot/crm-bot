from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_sets_request_id_header(client):
    resp = await client.get("/health")
    assert "x-request-id" in {k.lower() for k in resp.headers.keys()}
