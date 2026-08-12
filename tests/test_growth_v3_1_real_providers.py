from __future__ import annotations

from typing import Any

import pytest

from growth_orchestrator.application.daily_dispatch import daily_dispatch
from growth_orchestrator.bridges.m07_publishing_bridge import (
    M07PublishingBridge,
    m07_publishing_bridge_from_env,
)
from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter, build_make_webhook_signature
from publishing_gateway.fallback_images import fallback_image_url
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter, build_zalo_webhook_signature, refresh_zalo_access_token
from research_engine.trend_radar.collectors.tavily_search import collect_tavily_search
from shared.http import HttpError, urllib_post
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


# --- Zalo OA -> Make.com webhook trigger (Approve button flow) -------------


def test_zalo_adapter_without_webhook_url_keeps_old_mock_behavior() -> None:
    # Backward compat: existing callers that only pass enabled=True must not
    # suddenly attempt a real network call.
    adapter = ZaloOAAdapter(enabled=True)
    result = adapter.send({"publication_id": "pub-1"})
    assert result["status"] == "GATEWAY_ACCEPTED"
    assert result["published"] is False


def test_zalo_adapter_forwards_to_make_webhook_with_fresh_token() -> None:
    fake = FakeHttpPost({"received": True})
    adapter = ZaloOAAdapter(
        enabled=True,
        webhook_url="https://hook.us1.make.com/zalo-test",
        access_token_provider=lambda: "fresh-access-token",
        http_post=fake,
    )
    result = adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "content": {"text": "hello"}})
    assert result["status"] == "GATEWAY_ACCEPTED"
    call = fake.calls[0]
    assert call["url"] == "https://hook.us1.make.com/zalo-test"
    assert call["json"] == {
        "publication_id": "pub-1",
        "idempotency_key": "idem-1",
        "platform": "zalo_oa",
        "content": {"text": "hello"},
        "access_token": "fresh-access-token",
    }


def test_zalo_adapter_signs_webhook_when_secret_configured() -> None:
    fake = FakeHttpPost({"received": True})
    adapter = ZaloOAAdapter(enabled=True, webhook_url="https://hook.example/zalo", webhook_secret="shh", http_post=fake)
    adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1"})
    expected_signature = build_zalo_webhook_signature("shh", "pub-1", "idem-1")
    assert fake.calls[0]["headers"] == {"X-Venho-Signature": expected_signature}


def test_zalo_adapter_returns_gateway_error_on_webhook_failure() -> None:
    def failing_post(*args, **kwargs):
        raise HttpError(500, "make.com down")

    adapter = ZaloOAAdapter(enabled=True, webhook_url="https://hook.example/zalo", http_post=failing_post)
    result = adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1"})
    assert result["status"] == "GATEWAY_ERROR"
    assert result["published"] is False


def test_make_adapter_forwards_to_make_webhook() -> None:
    fake = FakeHttpPost({"received": True})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.us1.make.com/fb-test", http_post=fake)
    result = adapter.send(
        {"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook", "content": {"text": "hello"}}
    )
    assert result["status"] == "GATEWAY_ACCEPTED"
    call = fake.calls[0]
    assert call["url"] == "https://hook.us1.make.com/fb-test"
    assert call["json"] == {
        "publication_id": "pub-1",
        "idempotency_key": "idem-1",
        "platform": "facebook",
        "content": {"text": "hello"},
        "image_url": fallback_image_url(),
    }


def test_make_adapter_never_sends_null_image_url() -> None:
    """Regression (2026-08-06): a publication with no generated image sent
    image_url: null, and Make's "HTTP: Download a file" module rejects a null
    `url` with BundleValidationError -- killing the whole dispatch, text
    included. An on-brand hotel photo now stands in."""
    fake = FakeHttpPost({"received": True})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.us1.make.com/fb-test", http_post=fake)
    adapter.send(
        {
            "publication_id": "pub-1",
            "idempotency_key": "idem-1",
            "platform": "facebook",
            "content": {"text": "hello", "image_public_url": None},
        }
    )
    image_url = fake.calls[0]["json"]["image_url"]
    assert image_url == fallback_image_url()
    assert image_url.startswith("https://venhohotel.com/images/Social-fallback/")


def test_make_adapter_surfaces_image_public_url_at_top_level(tmp_path) -> None:
    """Regression test: image_run_path (a local file, meaningless to Make.com)
    used to be the only image reference in the dispatch payload -- generated
    photos never reached the real post. content.image_public_url (set by
    daily_cycle's Google Drive upload) is now also copied to a top-level
    image_url field for easier Make.com field-mapping."""
    fake = FakeHttpPost({"received": True})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.us1.make.com/fb-test", http_post=fake)
    adapter.send(
        {
            "publication_id": "pub-1",
            "idempotency_key": "idem-1",
            "platform": "facebook",
            "content": {"text": "hello", "image_public_url": "https://drive.google.com/uc?export=download&id=abc"},
        }
    )
    assert fake.calls[0]["json"]["image_url"] == "https://drive.google.com/uc?export=download&id=abc"


def test_make_adapter_signs_webhook_when_secret_configured() -> None:
    fake = FakeHttpPost({"received": True})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", webhook_secret="shh", http_post=fake)
    adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"})
    expected_signature = build_make_webhook_signature("shh", "pub-1", "idem-1")
    assert fake.calls[0]["headers"] == {"X-Venho-Signature": expected_signature}


def test_make_adapter_returns_gateway_error_on_webhook_failure() -> None:
    def failing_post(*args, **kwargs):
        raise HttpError(500, "make.com down")

    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", http_post=failing_post)
    result = adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"})
    assert result["status"] == "GATEWAY_ERROR"


def test_m07_bridge_routes_zalo_platform_to_zalo_adapter() -> None:
    zalo_calls = []
    make_calls = []
    zalo_adapter = ZaloOAAdapter(enabled=True)
    make_adapter = MakeGatewayAdapter(enabled=True)
    zalo_adapter.send = lambda command: zalo_calls.append(command) or {"status": "GATEWAY_ACCEPTED"}
    make_adapter.send = lambda command: make_calls.append(command) or {"status": "GATEWAY_ACCEPTED"}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=zalo_adapter)

    bridge.dispatch({"publication_id": "pub-1", "platform": "zalo"})

    assert len(zalo_calls) == 1
    assert len(make_calls) == 0


def test_m07_bridge_routes_facebook_instagram_threads_to_make_adapter() -> None:
    zalo_calls = []
    make_calls = []
    zalo_adapter = ZaloOAAdapter(enabled=True)
    make_adapter = MakeGatewayAdapter(enabled=True)
    zalo_adapter.send = lambda command: zalo_calls.append(command) or {"status": "GATEWAY_ACCEPTED"}
    make_adapter.send = lambda command: make_calls.append(command) or {"status": "GATEWAY_ACCEPTED"}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=zalo_adapter)

    for platform in ["facebook", "instagram", "threads"]:
        bridge.dispatch({"publication_id": f"pub-{platform}", "platform": platform})

    assert len(make_calls) == 3
    assert len(zalo_calls) == 0


def test_daily_dispatch_uses_injected_bridge_for_all_commands() -> None:
    dispatched = []
    bridge = M07PublishingBridge()
    bridge.dispatch = lambda command: dispatched.append(command) or {"status": "GATEWAY_ACCEPTED"}

    results = daily_dispatch(
        [{"publication_id": "pub-1", "platform": "zalo"}, {"publication_id": "pub-2", "platform": "facebook"}],
        bridge=bridge,
    )

    assert len(dispatched) == 2
    assert all(result["status"] == "GATEWAY_ACCEPTED" for result in results)


def test_m07_bridge_from_env_wires_real_adapters_when_configured() -> None:
    env = {
        "MAKE_GROWTH_WEBHOOK_URL": "https://hook.example/fb",
        "MAKE_GROWTH_WEBHOOK_SECRET": "fb-secret",
        "MAKE_ZALO_WEBHOOK_URL": "https://hook.example/zalo",
        "MAKE_ZALO_WEBHOOK_SECRET": "zalo-secret",
        "ZALO_APP_ID": "app-1",
        "ZALO_APP_SECRET": "secret-1",
        "ZALO_REFRESH_TOKEN": "refresh-1",
    }
    bridge = m07_publishing_bridge_from_env(env)

    assert bridge._make_adapter.enabled is True
    assert bridge._make_adapter.webhook_url == "https://hook.example/fb"
    assert bridge._zalo_adapter.enabled is True
    assert bridge._zalo_adapter.webhook_url == "https://hook.example/zalo"
    assert bridge._zalo_adapter._access_token_provider is not None


def test_m07_bridge_from_env_ignores_legacy_social_agent_webhook() -> None:
    """Regression (2026-08-04): growth used to reuse venho-social-content-agent's
    MAKE_WEBHOOK_URL, whose scenario requires a flat `url` field growth never
    sends -> BundleValidationError on every dispatch. Legacy var alone must
    leave the adapter disabled."""
    bridge = m07_publishing_bridge_from_env(
        {"MAKE_WEBHOOK_URL": "https://hook.example/legacy-social", "MAKE_WEBHOOK_SECRET": "legacy"}
    )

    assert bridge._make_adapter.enabled is False
    assert bridge._make_adapter.webhook_url is None


def test_m07_bridge_from_env_disables_adapters_when_unconfigured() -> None:
    bridge = m07_publishing_bridge_from_env({})

    assert bridge._make_adapter.enabled is False
    assert bridge._zalo_adapter.enabled is False
    assert bridge._zalo_adapter._access_token_provider is None


# --- Make.com synchronous outcome (2026-08-06) ------------------------------


def test_make_adapter_reports_published_when_scenario_returns_a_post_id() -> None:
    fake = FakeHttpPost({"status": "PUBLISHED", "platform_post_id": "1122", "permalink": "https://fb.com/p/1122"})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", http_post=fake)
    result = adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"})
    assert result["status"] == "PUBLISHED"
    assert result["published"] is True
    assert result["platform_post_id"] == "1122"
    assert result["permalink"] == "https://fb.com/p/1122"


def test_make_adapter_reports_gateway_error_when_the_platform_rejected_the_post() -> None:
    """The failure this was built for: Make accepts the bundle (HTTP 200), then
    Instagram rejects the photo with (36003) aspect ratio not supported. Without
    reading the reply that post was recorded GATEWAY_ACCEPTED and had to be
    corrected by hand."""
    fake = FakeHttpPost({"status": "GATEWAY_ERROR", "error": "(36003) The aspect ratio is not supported."})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/ig", http_post=fake)
    result = adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "instagram"})
    assert result["status"] == "GATEWAY_ERROR"
    assert result["published"] is False
    assert "36003" in result["error"]


def test_make_adapter_rejects_static_make_mapping_label_as_post_id() -> None:
    fake = FakeHttpPost(
        {
            "status": "PUBLISHED",
            "platform_post_id": "3. Post ID",
            "permalink": "3.permalink_url",
        }
    )
    adapter = MakeGatewayAdapter(
        enabled=True, webhook_url="https://hook.example/fb", http_post=fake
    )

    result = adapter.send(
        {"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"}
    )

    assert result["status"] == "GATEWAY_ERROR"
    assert result["published"] is False
    assert "valid platform_post_id" in result["error"]


def test_make_adapter_rejects_published_without_post_id() -> None:
    adapter = MakeGatewayAdapter(
        enabled=True,
        webhook_url="https://hook.example/fb",
        http_post=FakeHttpPost({"status": "PUBLISHED"}),
    )

    result = adapter.send(
        {"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"}
    )

    assert result["status"] == "GATEWAY_ERROR"
    assert "valid platform_post_id" in result["error"]


def test_make_adapter_keeps_accepting_a_scenario_without_response_modules() -> None:
    """Routes get built one platform at a time. A scenario replying with Make's
    plain-text "Accepted" must keep the old optimistic behaviour rather than
    start reporting failures."""
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", http_post=FakeHttpPost({"raw": "Accepted"}))
    assert adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"})["status"] == "GATEWAY_ACCEPTED"
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", http_post=FakeHttpPost({}))
    assert adapter.send({"publication_id": "pub-2", "idempotency_key": "idem-2", "platform": "facebook"})["status"] == "GATEWAY_ACCEPTED"


def test_make_adapter_waits_longer_than_the_default_transport_timeout() -> None:
    """A synchronous response only arrives after FB/IG have really run (6-8s
    each), so the 10s default would time out a post that in fact succeeded."""
    fake = FakeHttpPost({"raw": "Accepted"})
    adapter = MakeGatewayAdapter(enabled=True, webhook_url="https://hook.example/fb", http_post=fake)
    adapter.send({"publication_id": "pub-1", "idempotency_key": "idem-1", "platform": "facebook"})
    assert fake.calls[0]["timeout"] >= 30
