from __future__ import annotations

import http.client
import socket
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPSConnection
from typing import Protocol
from urllib.parse import urlsplit

from growth_engine.application.ports.clock import Clock
from growth_engine.application.publishing.dispatch_outbox import (
    DispatchTransportResult,
    TransportDisposition,
)
from growth_engine.domain.kernel.hashing import canonical_json_bytes


class HttpResponse(Protocol):
    status: int
    headers: Mapping[str, str]


class HttpConnection(Protocol):
    sock: object | None

    def request(self, method: str, target: str, *, body: bytes, headers: Mapping[str, str]) -> None: ...
    def getresponse(self) -> HttpResponse: ...
    def close(self) -> None: ...


ConnectionFactory = Callable[..., HttpConnection]


class HttpTransport:
    """POST one envelope to a Make route without logging route or envelope data."""

    def __init__(
        self,
        clock: Clock,
        *,
        connection_factory: ConnectionFactory = HTTPSConnection,
    ) -> None:
        self._clock = clock
        self._connection_factory = connection_factory

    def deliver(self, route_ref: str, envelope: dict[str, object]) -> DispatchTransportResult:
        try:
            parsed = urlsplit(route_ref)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.fragment
            ):
                return DispatchTransportResult(TransportDisposition.FATAL, status=None)
            try:
                port = parsed.port or 443
            except ValueError:
                return DispatchTransportResult(TransportDisposition.FATAL, status=None)
            target = parsed.path or "/"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            connection = self._connection_factory(parsed.hostname, port, timeout=5)
        except (TypeError, ValueError, UnicodeError):
            return DispatchTransportResult(TransportDisposition.FATAL, status=None)

        try:
            connection.request(
                "POST",
                target,
                body=canonical_json_bytes(envelope),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            stream = getattr(connection, "sock", None)
            settimeout = getattr(stream, "settimeout", None)
            if callable(settimeout):
                settimeout(15)
            response = connection.getresponse()
            status = response.status
            retry_after = _retry_after_seconds(response.headers, self._clock.now_ms())
            if 200 <= status < 300:
                return DispatchTransportResult(TransportDisposition.ACK, status=status)
            if status in {408, 425, 429} or status >= 500:
                return DispatchTransportResult(
                    TransportDisposition.RETRYABLE,
                    status=status,
                    retry_after_seconds=retry_after,
                )
            return DispatchTransportResult(TransportDisposition.FATAL, status=status)
        except (TimeoutError, socket.timeout, OSError, http.client.HTTPException):
            return DispatchTransportResult(TransportDisposition.RETRYABLE, status=None)
        finally:
            try:
                connection.close()
            except OSError:
                pass


def _retry_after_seconds(headers: Mapping[str, str], now_ms: int) -> float | None:
    value = next((item for key, item in headers.items() if key.lower() == "retry-after"), None)
    if value is None:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return float(stripped)
    try:
        retry_at = parsedate_to_datetime(stripped)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at.timestamp() * 1000 - now_ms) / 1000)
    except (TypeError, ValueError, OverflowError):
        return None
