from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml


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
    """Real Telegram Bot API sender (feature-flagged off by default, IN-D4)."""

    def __init__(self, *, bot_token: str, http_post: Callable[..., dict[str, Any]]) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is required")
        self._bot_token = bot_token
        self._http_post = http_post

    def send(self, *, chat_id: str, text: str) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        return self._http_post(url, json={"chat_id": chat_id, "text": text})


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
