from __future__ import annotations

from app.config import Settings


def test_cors_origins_parses_comma_separated_list():
    s = Settings(FRONTEND_ORIGIN="http://a.test, http://b.test ,http://c.test")
    assert s.cors_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_is_production_flag():
    assert Settings(ENV="production").is_production is True
    assert Settings(ENV="development").is_production is False
