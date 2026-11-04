from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from urllib.parse import quote

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_KEY_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COMMAND_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class MediaUrlClaims:
    sha256: str
    command_id: str
    expires_at_ms: int
    key_id: str


class SignedMediaUrlIssuer:
    """Issues and verifies expiring media URLs using the configured HMAC key ring."""

    def __init__(self, public_base_url: str, key_config: str) -> None:
        base_url = public_base_url.strip().rstrip("/")
        if not (base_url.startswith("https://") or base_url.startswith("http://")):
            raise ValueError("public_base_url must be an absolute HTTP URL")
        self._base_url = base_url
        self._keys = _parse_keys(key_config)
        self._signing_key_id = next(iter(self._keys))

    def media_url(self, sha256: str, command_id: str, expires_at_ms: int) -> str:
        _validate_sha(sha256)
        if not _COMMAND_ID.fullmatch(command_id):
            raise ValueError("command_id is invalid")
        if type(expires_at_ms) is not int or expires_at_ms <= 0:
            raise ValueError("expires_at_ms must be a positive integer")
        key_id = self._signing_key_id
        payload = _mac_payload(sha256, command_id, expires_at_ms)
        signature = _encode(hmac.new(self._keys[key_id], payload, hashlib.sha256).digest())
        token = f"v1.{key_id}.{command_id}.{expires_at_ms}.{signature}"
        return f"{self._base_url}/media/publish/{sha256}.jpg?t={quote(token, safe='')}"

    def verify(self, token: str, sha256: str, *, now_ms: int) -> MediaUrlClaims | None:
        try:
            _validate_sha(sha256)
            if type(now_ms) is not int:
                return None
            version, key_id, command_id, raw_expiry, signature = token.split(".")
            if version != "v1" or key_id not in self._keys or not _COMMAND_ID.fullmatch(command_id):
                return None
            expires_at_ms = int(raw_expiry)
            if str(expires_at_ms) != raw_expiry or expires_at_ms < now_ms:
                return None
            expected = hmac.new(
                self._keys[key_id],
                _mac_payload(sha256, command_id, expires_at_ms),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(expected, _decode(signature)):
                return None
            return MediaUrlClaims(sha256, command_id, expires_at_ms, key_id)
        except (TypeError, ValueError):
            return None


def _parse_keys(value: str) -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    for entry in value.replace("\n", ",").replace(";", ",").split(","):
        key_id, separator, encoded = entry.strip().partition(":")
        if not separator or not _KEY_ID.fullmatch(key_id) or not encoded.strip():
            continue
        try:
            raw = _decode(encoded.strip())
        except ValueError:
            continue
        if len(raw) >= 32:
            keys[key_id] = raw
    if not keys:
        raise ValueError("at least one base64 HMAC key of 32 bytes is required")
    return keys


def _validate_sha(value: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")


def _mac_payload(sha256: str, command_id: str, expires_at_ms: int) -> bytes:
    return f"{sha256}\n{command_id}\n{expires_at_ms}".encode("utf-8")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    if not value or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=" for character in value):
        raise ValueError("invalid base64url value")
    padded = value.rstrip("=") + "=" * (-len(value.rstrip("=")) % 4)
    return base64.b64decode(padded, altchars=b"-_", validate=True)
