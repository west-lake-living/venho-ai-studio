from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit


class HeartbeatSender(Protocol):
    def ping(self, url: str) -> None: ...


class Heartbeat:
    """Send an external dead-man ping only when the publish lane requests it."""

    def __init__(self, url: str, sender: HeartbeatSender) -> None:
        self._url = url.strip()
        self._sender = sender
        if self._url:
            parsed = urlsplit(self._url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError("GE_HEARTBEAT_URL must be HTTPS")

    def __repr__(self) -> str:
        return "Heartbeat(url=<redacted>)"

    def execute(self) -> bool:
        if not self._url:
            return False
        try:
            self._sender.ping(self._url)
        except Exception:
            return False
        return True
