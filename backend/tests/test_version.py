from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_version_returns_metadata(client, settings):
    resp = await client.get("/api/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == settings.APP_NAME
    assert body["version"] == settings.APP_VERSION
    assert body["env"] == settings.ENV
