from __future__ import annotations

from typing import Any, Callable

from shared.http import urllib_post_form

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


class ZaloOAAdapter:
    """Zalo OA channel adapter. Flag off by default (IN-D5) -- ships after
    Phase 4.5 once a dedicated Zalo OA app/quota exists; MVP scope is FB+IG
    only.

    NOTE: unlike Facebook/Instagram, Zalo OA has no public "feed post" API --
    real message sending is scoped to a specific follower `user_id` (7-day
    consultation window) or an approved broadcast template. The exact
    endpoint/payload for this adapter's real `send()` is intentionally left
    unimplemented until that target/use-case (P1 alert vs. broadcast) is
    confirmed -- guessing here risks burning real OA quota or notifying the
    wrong audience.
    """

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def send(self, command: dict) -> dict:
        if not self.enabled:
            return {"status": "DISABLED", "command_id": command.get("publication_id"), "published": False}
        return {
            "status": "GATEWAY_ACCEPTED",
            "command_id": command.get("publication_id"),
            "published": False,
            "message": "accepted by Zalo OA adapter; awaiting callback or reconciliation",
        }
