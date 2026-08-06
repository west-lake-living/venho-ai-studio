from __future__ import annotations

import hashlib
import hmac
from typing import Any, Callable

from publishing_gateway.fallback_images import fallback_image_url
from shared.http import HttpError, urllib_post


def build_make_webhook_signature(secret: str, publication_id: str, idempotency_key: str) -> str:
    """Same HMAC-SHA256-over-canonical-string convention as `zalo_oa.build_zalo_webhook_signature`."""
    message = f"{publication_id}:{idempotency_key}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class MakeGatewayAdapter:
    """Facebook/Instagram/Threads channel adapter.

    Real send does not call any platform API directly from this codebase --
    it fires a webhook to the same Make.com relay pattern as `ZaloOAAdapter`,
    and Make's own modules make the actual platform call. Without
    `webhook_url` configured, `send()` keeps the old mock behavior (flag off
    by default).

    The webhook must be a Make scenario dedicated to growth
    (`MAKE_GROWTH_WEBHOOK_URL`), NOT the legacy VenHoSocialManager one: that
    scenario is built around a flat legacy payload (`url`, `message`,
    `publish_to_facebook`) this adapter never sends. Sharing one webhook made
    every growth dispatch fail Make-side (2026-08-04).
    """

    def __init__(
        self,
        enabled: bool = False,
        *,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        http_post: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret
        self._http_post = http_post or urllib_post

    def send(self, command: dict) -> dict:
        publication_id = command.get("publication_id")
        if not self.enabled:
            return {"status": "DISABLED", "command_id": publication_id, "published": False}
        if not self.webhook_url:
            return {
                "status": "GATEWAY_ACCEPTED",
                "command_id": publication_id,
                "published": False,
                "message": "accepted by Make adapter; awaiting callback or reconciliation",
            }
        content = command.get("content") or {}
        payload = {
            "publication_id": publication_id,
            "idempotency_key": command.get("idempotency_key"),
            "platform": command.get("platform"),
            "content": content,
            # Top-level convenience copy of content.image_public_url --
            # Make.com's "HTTP: Download a file" module maps a flat field more
            # easily than a nested path, and its `url` is a required parameter:
            # sending null fails the whole bundle with BundleValidationError
            # (2026-08-06 incident). daily_cycle already substitutes an
            # on-brand hotel photo at queue time; this second layer covers rows
            # queued before that existed, and any other caller of this adapter.
            "image_url": content.get("image_public_url") or fallback_image_url(),
        }
        headers = None
        if self.webhook_secret and payload.get("idempotency_key"):
            headers = {
                "X-Venho-Signature": build_make_webhook_signature(
                    self.webhook_secret, publication_id, payload["idempotency_key"]
                )
            }
        try:
            self._http_post(self.webhook_url, json=payload, headers=headers)
        except HttpError as exc:
            return {
                "status": "GATEWAY_ERROR",
                "command_id": publication_id,
                "published": False,
                "error": str(exc),
            }
        return {
            "status": "GATEWAY_ACCEPTED",
            "command_id": publication_id,
            "published": False,
            "message": "forwarded to Make.com webhook; awaiting callback or reconciliation",
        }
