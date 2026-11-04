from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Callable

from fastapi import Request

from growth_engine.domain.kernel.errors import DomainError, ErrorCode


@dataclass(frozen=True)
class Principal:
    id: str
    scopes: frozenset[str]
    channel_id: str | None = None


_PRINCIPAL_POLICY: dict[str, tuple[frozenset[str], str | None]] = {
    "bff": (frozenset({"dashboard:read", "dashboard:write", "operator"}), None),
    "make-fb-hanoi": (frozenset({"execution", "receipt", "media:approved"}), "fb_hanoi"),
    "make-fb-venho": (frozenset({"execution", "receipt", "media:approved"}), "fb_venho"),
    "make-ig": (frozenset({"execution", "receipt", "media:approved"}), "ig_venho"),
    "research-ingest": (frozenset({"ingest"}), None),
}

def principal_from_request(request: Request) -> Principal:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token.strip():
        raise _unauthenticated()

    digest = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    principal_id = _resolve_principal(request.app.state.container.settings.service_tokens, digest)
    if principal_id is None:
        raise _unauthenticated()

    scopes, channel_id = _PRINCIPAL_POLICY.get(principal_id, (frozenset(), None))
    actor_header = request.headers.get("x-venho-actor")
    if actor_header is not None and principal_id != "bff":
        raise _forbidden()
    if actor_header is not None and not actor_header.strip():
        raise _forbidden()
    request.state.principal_id = principal_id
    request.state.actor = actor_header.strip() if actor_header is not None else principal_id
    return Principal(id=principal_id, scopes=scopes, channel_id=channel_id)


def require_scopes(*required_scopes: str) -> Callable[[Request], Principal]:
    def dependency(request: Request) -> Principal:
        principal = principal_from_request(request)
        if not set(required_scopes).issubset(principal.scopes):
            raise _forbidden()
        return principal

    return dependency


def _resolve_principal(configured_hashes: str, digest: str) -> str | None:
    for entry in configured_hashes.replace("\n", ",").replace(";", ",").split(","):
        principal_id, separator, expected_hash = entry.strip().partition(":")
        if separator and principal_id and hmac.compare_digest(expected_hash.strip().lower(), digest):
            return principal_id
    return None


def _unauthenticated() -> DomainError:
    return DomainError(ErrorCode.UNAUTHENTICATED, "Phiên đăng nhập không hợp lệ.")


def _forbidden() -> DomainError:
    return DomainError(ErrorCode.FORBIDDEN, "Bạn không có quyền thực hiện thao tác này.")
