from __future__ import annotations

from typing import Any

import pytest

from publishing_gateway.adapters.zalo_oa import refresh_zalo_access_token
from research_engine.trend_radar.collectors.tavily_search import collect_tavily_search
from shared.http import urllib_post
from shared.notify.telegram import TelegramNotifier, telegram_notifier_from_env


class FakeHttpPost:
    """Captures every call instead of touching the network -- keeps this suite at 0 API calls."""

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"url": url, **kwargs})
        return self.response


# --- Telegram real transport (IN-D4) ---------------------------------------


def test_telegram_notifier_defaults_to_real_urllib_transport() -> None:
    notifier = TelegramNotifier(bot_token="123:ABC")
    assert notifier._http_post is urllib_post


def test_telegram_notifier_send_hits_correct_url_and_payload() -> None:
    fake = FakeHttpPost({"ok": True})
    notifier = TelegramNotifier(bot_token="123:ABC", http_post=fake)
    result = notifier.send(chat_id="999", text="hello")
    assert result == {"ok": True}
    assert fake.calls[0]["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert fake.calls[0]["json"] == {"chat_id": "999", "text": "hello"}


def test_telegram_notifier_from_env_reads_bot_token() -> None:
    notifier = telegram_notifier_from_env({"TELEGRAM_BOT_TOKEN": "123:ABC"})
    assert notifier._bot_token == "123:ABC"


def test_telegram_notifier_from_env_missing_token_raises() -> None:
    with pytest.raises(KeyError):
        telegram_notifier_from_env({})


# --- Tavily search collector (research_engine) ------------------------------


def test_collect_tavily_search_requires_api_key() -> None:
    with pytest.raises(ValueError):
        collect_tavily_search("west lake hanoi", api_key="")


def test_collect_tavily_search_normalizes_raw_results() -> None:
    fake = FakeHttpPost(
        {
            "results": [
                {"title": "West Lake sunrise", "url": "https://example.com/a", "content": "snippet", "score": 0.9},
            ]
        }
    )
    results = collect_tavily_search("west lake hanoi", api_key="tvly-test", http_post=fake)
    assert results == [
        {
            "id": "tavily-https://example.com/a",
            "title": "West Lake sunrise",
            "source_uri": "https://example.com/a",
            "snippet": "snippet",
            "relevance_hint": 0.9,
        }
    ]
    assert fake.calls[0]["json"]["api_key"] == "tvly-test"
    assert fake.calls[0]["json"]["query"] == "west lake hanoi"


# --- Zalo OA token refresh (IN-D5) ------------------------------------------


def test_refresh_zalo_access_token_requires_all_credentials() -> None:
    with pytest.raises(ValueError):
        refresh_zalo_access_token(app_id="", app_secret="s", refresh_token="r")


def test_refresh_zalo_access_token_uses_form_body_and_secret_header() -> None:
    fake = FakeHttpPost({"access_token": "new-token", "refresh_token": "new-refresh", "expires_in": "3600"})
    result = refresh_zalo_access_token(app_id="app-1", app_secret="shh", refresh_token="old-refresh", http_post_form=fake)
    assert result["access_token"] == "new-token"
    call = fake.calls[0]
    assert call["data"] == {"app_id": "app-1", "refresh_token": "old-refresh", "grant_type": "refresh_token"}
    assert call["headers"] == {"secret_key": "shh"}
