from __future__ import annotations

from typing import Protocol, runtime_checkable

from growth_engine.application.dto import CommandClaims, TransportResult


@runtime_checkable
class PublishTransport(Protocol):
    def deliver(self, route_ref: str, envelope: dict[str, object]) -> TransportResult: ...


@runtime_checkable
class CapabilityTokens(Protocol):
    def issue(self, claims: CommandClaims) -> str: ...
    def verify(self, token: str, audience: str, now_ms: int) -> CommandClaims: ...
