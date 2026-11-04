from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Protocol


class TelegramDeliveryError(RuntimeError):
    """Sanitized transport failure; never contains bot token or response body."""


class TelegramTransport(Protocol):
    def post(self, url: str, body: bytes, *, timeout: float) -> tuple[int, bytes]: ...


class UrllibTelegramTransport:
    def post(self, url: str, body: bytes, *, timeout: float) -> tuple[int, bytes]:
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()


@dataclass(frozen=True)
class TelegramNotifier:
    bot_token: str
    chat_id: str
    transport: TelegramTransport | None = None
    timeout: float = 10.0

    def __post_init__(self) -> None:
        if not self.bot_token.strip() or "REQUIRED_FROM_P0" in self.bot_token:
            raise ValueError("Telegram bot token is not configured")
        if not self.chat_id.strip() or "REQUIRED_FROM_P0" in self.chat_id:
            raise ValueError("Telegram chat ID is not configured")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    def __repr__(self) -> str:
        return "TelegramNotifier(bot_token=<redacted>, chat_id=<redacted>)"

    def send(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Telegram message must not be empty")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": message, "disable_web_page_preview": True},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        transport = self.transport or UrllibTelegramTransport()
        try:
            status, response_body = transport.post(url, payload, timeout=self.timeout)
            response = json.loads(response_body.decode("utf-8"))
        except Exception as error:
            raise TelegramDeliveryError(f"Telegram transport failed ({type(error).__name__})") from None
        if status < 200 or status >= 300 or not isinstance(response, Mapping) or response.get("ok") is not True:
            raise TelegramDeliveryError(f"Telegram rejected message (HTTP {status})")
