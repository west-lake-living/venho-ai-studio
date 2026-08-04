from __future__ import annotations

import hashlib
import hmac
from typing import Any, Callable

from shared.http import HttpError, urllib_post


def build_make_webhook_signature(secret: str, publication_id: str, idempotency_key: str) -> str:
    """Same HMAC-SHA256-over-canonical-string convention as `zalo_oa.build_zalo_webhook_signature`."""
    message = f"{publication_id}:{idempotency_key}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class MakeGatewayAdapter:
    """Facebook/Instagram/Threads channel adapter.

    Real send does not call any platform API directly from this codebase --
    it fires a webhook to the same Make.com relay pattern as `ZaloOAAdapter`
    (reusing the existing Make.com scenario Harry already runs for the legacy
    VenHoSocialManager FB posting flow). Make's own HTTP / Custom API Request
    module makes the actual platform call. Without `webhook_url` configured,
    `send()` keeps the old mock behavior (flag off by default).
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
            # Make.com's "HTTP: Get a file" module maps a flat field more
            # easily than a nested path. None when no image was generated/
            # uploaded (daily_cycle still queues text-only in that case).
            "image_url": content.get("image_public_url"),
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
