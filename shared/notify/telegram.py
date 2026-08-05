from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

import yaml

from shared.http import urllib_post


class TelegramSender(Protocol):
    def send(self, *, chat_id: str, text: str) -> dict[str, Any]: ...


@dataclass
class MockTelegramNotifier:
    """Default sender in tests and until IN-D4 is wired to a real bot token."""

    sent: list[dict[str, Any]] = field(default_factory=list)

    def send(self, *, chat_id: str, text: str) -> dict[str, Any]:
        record = {"chat_id": chat_id, "text": text}
        self.sent.append(record)
        return {"ok": True, **record}


class TelegramNotifier:
    """Real Telegram Bot API sender (feature-flagged off by default, IN-D4).

    `http_post` defaults to the stdlib transport (`shared.http.urllib_post`)
    so real usage needs no extra wiring; tests always inject a fake to keep
    the suite at 0 API calls.
    """

    def __init__(self, *, bot_token: str, http_post: Callable[..., dict[str, Any]] | None = None) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is required")
        self._bot_token = bot_token
        self._http_post = http_post or urllib_post

    def send(self, *, chat_id: str, text: str) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        return self._http_post(url, json={"chat_id": chat_id, "text": text})


def telegram_notifier_from_env(env: Mapping[str, str]) -> TelegramNotifier:
    """Build a real TelegramNotifier from process env (e.g. `os.environ` after dotenv load).

    Raises KeyError if TELEGRAM_BOT_TOKEN is missing -- callers must only use
    this once `telegram_alerts_enabled`-style feature flag is on.
    """
    bot_token = env["TELEGRAM_BOT_TOKEN"]
    return TelegramNotifier(bot_token=bot_token)


def telegram_notifier_or_mock_from_env(env: Mapping[str, str]) -> "TelegramNotifier | MockTelegramNotifier":
    """Real notifier if TELEGRAM_BOT_TOKEN is set, else the disabled/dev-safe
    Mock -- same graceful-fallback convention as
    `shared.storage.google_drive.google_drive_uploader_from_env`. Used by
    best-effort callers (e.g. `manage_queue.check_runway`) that must never
    raise just because Harry hasn't set the bot token yet."""
    if not env.get("TELEGRAM_BOT_TOKEN"):
        return MockTelegramNotifier()
    return telegram_notifier_from_env(env)


def load_alert_policy(path: Path = Path("shared/notify/alert_policy.yaml")) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_alert(
    event: str,
    *,
    policy: dict[str, Any] | None = None,
    policy_path: Path = Path("shared/notify/alert_policy.yaml"),
) -> dict[str, Any]:
    policy = policy if policy is not None else load_alert_policy(policy_path)
    events = policy.get("events", {})
    if event not in events:
        raise ValueError(f"Unknown alert event: {event}")
    return events[event]


def send_alert(
    event: str,
    message: str,
    *,
    notifier: TelegramSender,
    chat_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    routing = resolve_alert(event, policy=policy)
    result = notifier.send(chat_id=chat_id, text=f"[{routing['severity'].upper()}] {message}")
    return {"event": event, **routing, **result}
