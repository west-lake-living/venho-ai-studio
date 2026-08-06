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


def interpret_make_response(body: Any, *, publication_id: str | None) -> dict[str, Any]:
    """Turn Make.com's webhook reply into a dispatch outcome.

    Why (2026-08-06): a 200 from the webhook only means Make *accepted* the
    bundle. The platform call happens afterwards inside the scenario, so a post
    Instagram rejected outright -- `(36003) aspect ratio not supported` -- was
    still recorded GATEWAY_ACCEPTED here and had to be corrected by hand. Make
    cannot call back into this machine (the registry is local, there is no
    public endpoint), so the scenario answers *synchronously* instead: a
    `Webhooks > Webhook response` module at the end of each route replies with

        {"status": "PUBLISHED", "platform_post_id": "...", "permalink": "..."}

    or `{"status": "GATEWAY_ERROR", "error": "..."}` on the error handler path.

    A scenario without those modules replies with Make's plain-text "Accepted",
    which is why an unrecognised body keeps the old optimistic GATEWAY_ACCEPTED:
    routes are added one platform at a time, and a Threads route that has not
    been built yet must not start reporting failures.
    """
    accepted = {
        "status": "GATEWAY_ACCEPTED",
        "command_id": publication_id,
        "published": False,
        "message": "forwarded to Make.com webhook; awaiting callback or reconciliation",
    }
    if not isinstance(body, dict) or "raw" in body:
        return accepted

    error = body.get("error")
    status = str(body.get("status") or "").upper()
    if error or status in ("GATEWAY_ERROR", "ERROR", "FAILED"):
        return {
            "status": "GATEWAY_ERROR",
            "command_id": publication_id,
            "published": False,
            "error": str(error or f"Make.com reported {status or 'failure'}"),
        }

    post_id = body.get("platform_post_id") or body.get("post_id") or body.get("id")
    if status == "PUBLISHED" or post_id:
        return {
            "status": "PUBLISHED",
            "command_id": publication_id,
            "published": True,
            "platform_post_id": str(post_id) if post_id else None,
            "permalink": body.get("permalink"),
        }
    return accepted


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
        # Well past the default 10s: with a Webhook response module the
        # scenario answers only after Facebook/Instagram have actually run,
        # which measured 6-8s per platform and is slower on retries.
        timeout: float = 60.0,
    ) -> None:
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret
        self.timeout = timeout
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
            body = self._http_post(
                self.webhook_url, json=payload, headers=headers, timeout=self.timeout
            )
        except HttpError as exc:
            return {
                "status": "GATEWAY_ERROR",
                "command_id": publication_id,
                "published": False,
                "error": str(exc),
            }
        return interpret_make_response(body, publication_id=publication_id)
