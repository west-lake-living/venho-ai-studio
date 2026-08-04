from __future__ import annotations

import hashlib
import hmac
from typing import Any, Callable

from shared.http import HttpError, urllib_post, urllib_post_form

ZALO_REFRESH_TOKEN_URL = "https://oauth.zalo.me/v4/oa/access_token"


def refresh_zalo_access_token(
    *,
    app_id: str,
    app_secret: str,
    refresh_token: str,
    http_post_form: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Exchange a Zalo OA refresh_token for a fresh access_token (Zalo OAuth v4).

    Zalo's token endpoint requires x-www-form-urlencoded body and the app
    secret in a `secret_key` header (not JSON, not query string) -- returns
    the raw provider payload (access_token/refresh_token/expires_in) so the
    caller decides where to persist it.
    """
    if not (app_id and app_secret and refresh_token):
        raise ValueError("app_id, app_secret and refresh_token are all required")
    post = http_post_form or urllib_post_form
    return post(
        ZALO_REFRESH_TOKEN_URL,
        data={
            "app_id": app_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        headers={"secret_key": app_secret},
    )


def build_zalo_webhook_signature(secret: str, publication_id: str, idempotency_key: str) -> str:
    """Same HMAC-SHA256-over-canonical-string convention as `approval_verifier.build_approval_signature`."""
    message = f"{publication_id}:{idempotency_key}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


class ZaloOAAdapter:
    """Zalo OA channel adapter.

    Real send does NOT call Zalo's API directly from this codebase. Per
    Harry's integration decision, this adapter fires a webhook to a Make.com
    scenario; Make's own HTTP / Custom API Request module (configured in the
    Make UI, not here) makes the actual Zalo OA call right after the
    "Approve" click on VENHO OS Dashboard. That split is deliberate: Zalo OA
    has no public "feed post" API like Facebook Pages (real sending targets
    a specific follower `user_id` or an approved broadcast template), so the
    exact Zalo endpoint/payload shape is Harry's call to make inside Make.com
    -- this adapter only needs to hand it a fresh access_token + the message.

    `access_token_provider`, if given, is called once per `send()` to fetch
    a live token (e.g. wrapping `refresh_zalo_access_token`) so Make.com
    never has to manage Zalo OAuth itself. Without `webhook_url` configured,
    `send()` keeps the old mock behavior (flag off by default, IN-D5).
    """

    def __init__(
        self,
        enabled: bool = False,
        *,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        access_token_provider: Callable[[], str] | None = None,
        http_post: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret
        self._access_token_provider = access_token_provider
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
                "message": "accepted by Zalo OA adapter; awaiting callback or reconciliation",
            }
        payload = {
            "publication_id": publication_id,
            "idempotency_key": command.get("idempotency_key"),
            "platform": "zalo_oa",
            "content": command.get("content"),
        }
        if self._access_token_provider is not None:
            payload["access_token"] = self._access_token_provider()
        headers = None
        if self.webhook_secret and payload.get("idempotency_key"):
            headers = {
                "X-Venho-Signature": build_zalo_webhook_signature(
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
            "message": "forwarded to Make.com Zalo webhook; awaiting callback or reconciliation",
        }
