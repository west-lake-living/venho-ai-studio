from __future__ import annotations

import hashlib
import hmac
import json
import time

from publishing_gateway.publication_registry import PublicationRegistry


def verify_callback_signature(body: bytes, signature: str, secret: str, *, timestamp: int) -> bool:
    # timestamp must be part of the signed message, otherwise an attacker can
    # replay an old valid (body, signature) pair with a freshly forged
    # timestamp and sail through the replay-window check below.
    message = f"{timestamp}.".encode("utf-8") + body
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_callback(body: bytes, *, signature: str, secret: str, timestamp: int, max_age_seconds: int = 300) -> dict:
    if abs(int(time.time()) - timestamp) > max_age_seconds:
        raise ValueError("callback timestamp outside replay window")
    if not verify_callback_signature(body, signature, secret, timestamp=timestamp):
        raise ValueError("invalid callback signature")
    payload = json.loads(body.decode("utf-8"))
    required = {"publication_id", "idempotency_key", "platform", "status", "platform_post_id", "permalink", "published_at"}
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"callback missing fields: {', '.join(sorted(missing))}")
    return payload


def apply_callback(payload: dict, *, registry: PublicationRegistry) -> dict:
    status = payload["status"]
    if status == "PUBLISHED" and not payload.get("platform_post_id"):
        raise ValueError("published callback requires platform_post_id")
    return registry.update(
        payload["publication_id"],
        status=status,
        platform_post_id=payload.get("platform_post_id"),
        permalink=payload.get("permalink"),
        published_at=payload.get("published_at"),
    )
