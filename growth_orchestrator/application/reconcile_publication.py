from __future__ import annotations

from pathlib import Path
from typing import Optional

from publishing_gateway.publication_registry import PublicationRegistry

# approve_and_dispatch() sets status to whatever M07PublishingBridge.dispatch()
# returns -- for MakeGatewayAdapter that's GATEWAY_ACCEPTED (fire-and-forget;
# see its docstring), never PUBLISHED. Reconciliation is the only thing that
# can move a row past GATEWAY_ACCEPTED until a real callback receiver exists.
DISPATCHED_STATUSES = {"GATEWAY_ACCEPTED"}


def reconcile_publication(
    publication_id: str,
    *,
    platform_post_id: str,
    reconciled_by: str,
    permalink: Optional[str] = None,
    published_at: Optional[str] = None,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> dict:
    """Manually record proof that a dispatched publication actually went live.

    DoD #3 requires publication idempotency "proven by platform post ID or
    reconciliation evidence". No automatic callback receiver exists today --
    MakeGatewayAdapter.send() fires the Make.com webhook and discards the
    response (fire-and-forget); a real incoming callback would need venho-os
    deployed with a public URL, which Harry has not set up (same GitHub-
    Actions-only infra decision as the Mac Mini/deadman-switch question).

    Until that exists, this is the reconciliation path: after Make.com posts
    for real, the operator checks the actual Facebook/Instagram/Threads/Zalo
    post and records its platform_post_id here. This is also what unblocks
    M08AnalyticsBridge.observe(), which refuses to run until platform_post_id
    is set -- without this function the analytics feedback loop could never
    fire outside of tests that fabricate a PUBLISHED row directly.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    publication = registry.find(publication_id)
    if publication is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if publication.get("status") not in DISPATCHED_STATUSES:
        raise ValueError(
            f"publication_id {publication_id} is not in a dispatched state "
            f"(status={publication.get('status')!r}); reconciliation only applies "
            "after approve_and_dispatch has fired the Make.com webhook"
        )
    if not platform_post_id:
        raise ValueError("platform_post_id is required")
    return registry.update(
        publication_id,
        status="PUBLISHED",
        platform_post_id=platform_post_id,
        permalink=permalink,
        published_at=published_at,
        reconciled_by=reconciled_by,
    )
