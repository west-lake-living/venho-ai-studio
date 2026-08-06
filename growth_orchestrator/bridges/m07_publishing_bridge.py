from __future__ import annotations

from typing import Mapping

from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter, refresh_zalo_access_token

ZALO_PLATFORMS = {"zalo", "zalo_oa"}


class M07PublishingBridge:
    """Routes a growth_orchestrator publish command to the right channel adapter.

    Routing key is `command["platform"]`: `zalo`/`zalo_oa` goes to `ZaloOAAdapter`
    (Make.com Zalo webhook), everything else (facebook/instagram/threads) goes to
    `MakeGatewayAdapter` (Make.com FB/IG/Threads webhook). Both adapters only ever return
    GATEWAY_ACCEPTED/GATEWAY_ERROR/DISABLED here -- actual PUBLISHED status still
    arrives later via `publishing_gateway.callback_receiver` or `reconciliation`.
    """

    def __init__(
        self,
        *,
        make_adapter: MakeGatewayAdapter | None = None,
        zalo_adapter: ZaloOAAdapter | None = None,
    ) -> None:
        self._make_adapter = make_adapter or MakeGatewayAdapter()
        self._zalo_adapter = zalo_adapter or ZaloOAAdapter()

    def dispatch(self, command: dict) -> dict:
        platform = command.get("platform")
        adapter = self._zalo_adapter if platform in ZALO_PLATFORMS else self._make_adapter
        return adapter.send(command)


def m07_publishing_bridge_from_env(env: Mapping[str, str]) -> M07PublishingBridge:
    """Build a bridge wired to real Make.com webhooks from `.env.local`-style vars.

    Missing/placeholder values fall back to each adapter's disabled default
    (`enabled=False`) rather than raising, since this is meant to be called from
    process startup where partial configuration (e.g. Zalo ready, FB not yet) is
    expected during rollout.

    The FB/IG/Threads adapter reads `MAKE_GROWTH_WEBHOOK_URL`, deliberately NOT
    the legacy `MAKE_WEBHOOK_URL` that venho-social-content-agent posts to. The
    two payload schemas are incompatible: the legacy scenario's "HTTP: Get a
    file" module requires a flat `url` field, which this adapter never sends, so
    sharing one webhook made every growth dispatch fail Make-side with
    BundleValidationError (2026-08-04). Growth needs its own Make scenario.
    """
    make_url = env.get("MAKE_GROWTH_WEBHOOK_URL")
    make_adapter = MakeGatewayAdapter(
        enabled=bool(make_url),
        webhook_url=make_url,
        webhook_secret=env.get("MAKE_GROWTH_WEBHOOK_SECRET"),
    )

    zalo_url = env.get("MAKE_ZALO_WEBHOOK_URL")
    app_id = env.get("ZALO_APP_ID")
    app_secret = env.get("ZALO_APP_SECRET")
    refresh_token = env.get("ZALO_REFRESH_TOKEN")
    access_token_provider = None
    if app_id and app_secret and refresh_token:
        def access_token_provider() -> str:
            return refresh_zalo_access_token(
                app_id=app_id, app_secret=app_secret, refresh_token=refresh_token
            )["access_token"]

    zalo_adapter = ZaloOAAdapter(
        enabled=bool(zalo_url),
        webhook_url=zalo_url,
        webhook_secret=env.get("MAKE_ZALO_WEBHOOK_SECRET"),
        access_token_provider=access_token_provider,
    )

    return M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=zalo_adapter)
