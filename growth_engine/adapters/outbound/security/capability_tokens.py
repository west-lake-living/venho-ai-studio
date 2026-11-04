from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


_KID = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
_PAYLOAD_HASH = re.compile(r"[0-9a-f]{64}\Z")
_CLAIM_KEYS = {"iss", "aud", "kid", "cmd", "rev", "ch", "ph", "ep", "exp"}


class CapabilityTokenInvalid(ValueError):
    code = "ERR_GC2_CAPABILITY_INVALID"

    def __init__(self) -> None:
        super().__init__("Capability token is invalid or expired.")


class TokenClaims(Protocol):
    command_id: str
    revision_id: str
    channel_id: str
    payload_hash: str
    dispatch_epoch: str
    audience: str
    expires_at_ms: int


@dataclass(frozen=True)
class VerifiedCapabilityClaims:
    command_id: str
    revision_id: str
    channel_id: str
    payload_hash: str
    dispatch_epoch: str
    audience: str
    expires_at_ms: int
    key_id: str


def parse_key_ring(value: str) -> dict[str, bytes]:
    """Parse GE_CAPABILITY_KEYS while never returning or logging key material."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("GE_CAPABILITY_KEYS must contain at least one key.")
    keys: dict[str, bytes] = {}
    for entry in value.split(","):
        if entry.count(":") != 1:
            raise ValueError("GE_CAPABILITY_KEYS entry is malformed.")
        kid, encoded = entry.split(":", 1)
        if not _KID.fullmatch(kid) or kid in keys or not encoded:
            raise ValueError("GE_CAPABILITY_KEYS entry is malformed.")
        try:
            padded = encoded + "=" * (-len(encoded) % 4)
            key = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError) as error:
            raise ValueError("GE_CAPABILITY_KEYS entry is malformed.") from error
        if len(key) < 32:
            raise ValueError("Capability keys must contain at least 32 bytes.")
        keys[kid] = key
    return keys


class CapabilityTokenManager:
    """Issue and verify canonical, audience-bound HMAC capability tokens."""

    def __init__(self, keys: Mapping[str, bytes]) -> None:
        normalized: dict[str, bytes] = {}
        for kid, key in keys.items():
            if not isinstance(kid, str) or not _KID.fullmatch(kid):
                raise ValueError("capability key id is malformed.")
            if not isinstance(key, bytes) or len(key) < 32:
                raise ValueError("Capability keys must contain at least 32 bytes.")
            normalized[kid] = key
        if not normalized:
            raise ValueError("At least one capability key is required.")
        self._keys = normalized
        self._active_kid = next(iter(normalized))

    @classmethod
    def from_environment(cls, variable: str = "GE_CAPABILITY_KEYS") -> CapabilityTokenManager:
        value = os.environ.get(variable, "")
        return cls(parse_key_ring(value))

    def issue(self, claims: TokenClaims) -> str:
        values = _claims_for_issue(claims)
        kid = self._active_kid
        payload = {
            "iss": "growth-engine",
            "aud": values["audience"],
            "kid": kid,
            "cmd": values["command_id"],
            "rev": values["revision_id"],
            "ch": values["channel_id"],
            "ph": values["payload_hash"],
            "ep": values["dispatch_epoch"],
            "exp": values["expires_at_ms"],
        }
        payload_part = _b64url(_canonical_json(payload))
        signing_input = f"v1.{payload_part}".encode("ascii")
        signature = hmac.new(self._keys[kid], signing_input, "sha256").digest()
        return f"v1.{payload_part}.{_b64url(signature)}"

    def verify(self, token: str, audience: str, now_ms: int) -> VerifiedCapabilityClaims:
        try:
            if not isinstance(token, str) or type(now_ms) is not int or now_ms < 0:
                raise CapabilityTokenInvalid()
            if not isinstance(audience, str) or not audience.strip():
                raise CapabilityTokenInvalid()
            parts = token.split(".")
            if len(parts) != 3 or parts[0] != "v1":
                raise CapabilityTokenInvalid()
            payload_bytes = _unb64url(parts[1])
            signature = _unb64url(parts[2])
            payload = json.loads(payload_bytes.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != _CLAIM_KEYS:
                raise CapabilityTokenInvalid()
            kid = payload.get("kid")
            key = self._keys.get(kid) if isinstance(kid, str) else None
            if key is None:
                raise CapabilityTokenInvalid()
            signing_input = f"v1.{parts[1]}".encode("ascii")
            expected = hmac.new(key, signing_input, "sha256").digest()
            if not hmac.compare_digest(expected, signature):
                raise CapabilityTokenInvalid()
            if _canonical_json(payload) != payload_bytes:
                raise CapabilityTokenInvalid()
            command_id = _required_text(payload, "cmd")
            revision_id = _required_text(payload, "rev")
            channel_id = _required_text(payload, "ch")
            token_audience = _required_text(payload, "aud")
            dispatch_epoch = _required_text(payload, "ep")
            payload_hash = payload.get("ph")
            expires_at_ms = payload.get("exp")
            if (
                payload.get("iss") != "growth-engine"
                or token_audience != audience
                or not isinstance(payload_hash, str)
                or not _PAYLOAD_HASH.fullmatch(payload_hash)
                or type(expires_at_ms) is not int
                or expires_at_ms < 0
                or now_ms > expires_at_ms
            ):
                raise CapabilityTokenInvalid()
            # The token contract deliberately binds the page ID through the channel claim;
            # the remote ID is loaded from the channel record after authorization.
            return VerifiedCapabilityClaims(
                command_id=command_id,
                revision_id=revision_id,
                channel_id=channel_id,
                payload_hash=payload_hash,
                dispatch_epoch=dispatch_epoch,
                audience=token_audience,
                expires_at_ms=expires_at_ms,
                key_id=kid,
            )
        except CapabilityTokenInvalid:
            raise
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as error:
            raise CapabilityTokenInvalid() from error


def _claims_for_issue(claims: TokenClaims) -> dict[str, object]:
    values = {
        "command_id": getattr(claims, "command_id", None),
        "revision_id": getattr(claims, "revision_id", None),
        "channel_id": getattr(claims, "channel_id", None),
        "payload_hash": getattr(claims, "payload_hash", None),
        "dispatch_epoch": getattr(claims, "dispatch_epoch", None),
        "audience": getattr(claims, "audience", None),
        "expires_at_ms": getattr(claims, "expires_at_ms", None),
    }
    if any(not isinstance(values[name], str) or not values[name].strip() for name in (
        "command_id", "revision_id", "channel_id", "dispatch_epoch", "audience"
    )):
        raise ValueError("Capability claims are incomplete.")
    if not isinstance(values["payload_hash"], str) or not _PAYLOAD_HASH.fullmatch(values["payload_hash"]):
        raise ValueError("Capability claims are incomplete.")
    if type(values["expires_at_ms"]) is not int or values["expires_at_ms"] < 0:
        raise ValueError("Capability claims are incomplete.")
    return values


def _required_text(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityTokenInvalid()
    return value


def _canonical_json(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64url(value: str) -> bytes:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise CapabilityTokenInvalid()
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as error:
        raise CapabilityTokenInvalid() from error
