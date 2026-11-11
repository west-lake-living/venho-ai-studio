from __future__ import annotations

import pytest

from growth_engine.settings import Settings


def test_production_rejects_unfilled_required_settings() -> None:
    with pytest.raises(ValueError, match="REQUIRED_FROM_P0"):
        Settings.from_env({"GE_ENV": "production"})


def test_settings_reads_static_and_channel_specific_environment_values() -> None:
    settings = Settings.from_env(
        {
            "GE_ENV": "test",
            "GE_DB_PATH": "/tmp/growth.db",
            "GE_MEDIA_ROOT": "/tmp/growth-media",
            "GE_PUBLIC_BASE_URL": "http://localhost:8021",
            "GE_DASHBOARD_BASE_URL": "https://dashboard.example.test",
            "GE_CAPABILITY_KEYS": "test-kid:test-key",
            "GE_SERVICE_TOKENS": "test-principal:test-hash",
            "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://example.test/hook",
            "GE_META_READ_TOKEN_PAGE_A": "sample-meta-token",
            "GE_META_TOKEN_EXPIRY_IG_VENHO": "2027-01-10",
            "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO": "2027-02-09",
            "GE_TELEGRAM_BOT_TOKEN": "sample-telegram-token",
        }
    )

    assert settings.env == "test"
    assert settings.db_path == "/tmp/growth.db"
    assert settings.media_root == "/tmp/growth-media"
    assert settings.make_webhook_urls == {"PAGE_A": "https://example.test/hook"}
    assert settings.meta_read_tokens == {"PAGE_A": "sample-meta-token"}
    assert settings.meta_token_expiries == {"IG_VENHO": "2027-01-10"}
    assert settings.meta_data_access_expiries == {"IG_VENHO": "2027-02-09"}
    assert settings.telegram == {"BOT_TOKEN": "sample-telegram-token"}
    assert "sample-meta-token" not in repr(settings)
    assert "sample-telegram-token" not in repr(settings)


def test_production_rejects_placeholder_in_channel_settings() -> None:
    with pytest.raises(ValueError, match="GE_META_READ_TOKEN_PAGE_A"):
        Settings.from_env(
            {
                "GE_ENV": "production",
                "GE_DB_PATH": "/srv/growth/growth_engine.db",
                "GE_MEDIA_ROOT": "/srv/growth/media",
                "GE_PUBLIC_BASE_URL": "https://growth.example.test",
                "GE_DASHBOARD_BASE_URL": "https://dashboard.example.test",
                "GE_CAPABILITY_KEYS": "kid:real-placeholder",
                "GE_SERVICE_TOKENS": "principal:hash-placeholder",
                "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://example.test/hook",
                "GE_META_READ_TOKEN_PAGE_A": "REQUIRED_FROM_P0",
                "GE_TELEGRAM_BOT_TOKEN": "sample-telegram-token",
                "GE_TELEGRAM_CHAT_ID": "sample-chat-id",
            }
        )


def test_production_requires_telegram_settings() -> None:
    with pytest.raises(ValueError, match="GE_TELEGRAM_BOT_TOKEN"):
        Settings.from_env(
            {
                "GE_ENV": "production",
                "GE_DB_PATH": "/srv/growth/growth_engine.db",
                "GE_MEDIA_ROOT": "/srv/growth/media",
                "GE_PUBLIC_BASE_URL": "https://growth.example.test",
                "GE_DASHBOARD_BASE_URL": "https://dashboard.example.test",
                "GE_CAPABILITY_KEYS": "kid:test-key",
                "GE_SERVICE_TOKENS": "principal:test-hash",
                "GE_MAKE_WEBHOOK_URL_PAGE_A": "https://example.test/hook",
                "GE_META_READ_TOKEN_PAGE_A": "sample-meta-token",
            }
        )
