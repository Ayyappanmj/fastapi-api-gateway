"""
Phase 11 tests: app/config.py's Settings — defaults and the
cors_origin_list derived property's parsing/whitespace handling.
"""
import pytest

from app.config import Settings, get_settings

pytestmark = pytest.mark.unit


def test_get_settings_is_cached_singleton():
    assert get_settings() is get_settings()


def test_default_settings_have_sane_values():
    settings = Settings()
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes > 0
    assert settings.refresh_token_expire_days > 0
    assert settings.default_rate_limit_tokens > 0
    assert settings.default_rate_limit_refill_per_sec > 0


def test_cors_origin_list_splits_and_strips_whitespace():
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000 ,http://example.com")
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://example.com",
    ]


def test_cors_origin_list_handles_single_origin():
    settings = Settings(cors_origins="http://localhost:5173")
    assert settings.cors_origin_list == ["http://localhost:5173"]


def test_cors_origin_list_ignores_empty_entries():
    settings = Settings(cors_origins="http://localhost:5173,,http://localhost:3000")
    assert settings.cors_origin_list == ["http://localhost:5173", "http://localhost:3000"]


def test_service_url_map_uses_configured_urls_only():
    settings = Settings(echo_service_url="http://echo:8000", users_service_url="http://users:8000")

    assert settings.service_url_map == {
        "echo": "http://echo:8000",
        "users": "http://users:8000",
    }
