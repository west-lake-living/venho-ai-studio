from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from automation_studio.approval_snapshot import assert_dispatch_allowed, create_approval_snapshot
from growth_orchestrator.bridges.m07_publishing_bridge import (
    M07PublishingBridge,
    m07_publishing_bridge_from_env,
)
from publishing_gateway.publication_registry import PublicationRegistry

PENDING_STATUS = "PENDING_APPROVAL"


def list_pending(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict]:
    registry = registry or PublicationRegistry(project, data_root=data_root)
    return [item for item in registry.load()["publications"] if item.get("status") == PENDING_STATUS]


def approve_and_dispatch(
    publication_id: str,
    *,
    approved_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
) -> dict:
    """Approve a queued draft and immediately dispatch it (Approve-triggers-publish).

    Only PENDING_APPROVAL rows (produced by `daily_cycle.run_daily_cycle`) can
    be approved -- this is the human gate between content prep (cron) and the
    real Make.com webhook firing (this function). Dispatch failure does not
    revert the approval: the row is marked GATEWAY_ERROR so the operator can
    retry the dispatch instead of re-approving.

    When the row carries a `package_snapshot` (daily_cycle always sets one),
    approval is recorded as a real automation_studio exact-version snapshot
    (DoD #7: "owner approval references exact copy + asset versions") rather
    than just flipping a status string -- `assert_dispatch_allowed` re-checks
    the version checksum right before dispatch and raises if it no longer
    matches, so an edit made after queuing (once an edit UI exists) can never
    silently ride through on a stale approval. Rows without a snapshot
    (older/manual reservations) fall back to the plain status-flip behavior.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    publication = registry.find(publication_id)
    if publication is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if publication.get("status") != PENDING_STATUS:
        raise ValueError(f"publication_id {publication_id} is not {PENDING_STATUS} (status={publication.get('status')})")

    approval_snapshot = None
    package_snapshot = publication.get("package_snapshot")
    if package_snapshot is not None:
        approval_snapshot = create_approval_snapshot(package_snapshot, approved_by=approved_by)
        assert_dispatch_allowed(approval_snapshot, package_snapshot)

    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    command = {
        "publication_id": publication["publication_id"],
        "idempotency_key": publication["idempotency_key"],
        "content_package_id": publication["content_package_id"],
        "platform": publication["platform"],
        "content": publication.get("content"),
    }
    response = bridge.dispatch(command)
    updates: dict = {
        "status": response["status"],
        "gateway_status": response["status"],
        "approved_by": approved_by,
    }
    if approval_snapshot is not None:
        updates["approval_snapshot"] = approval_snapshot
    return registry.update(publication_id, **updates)
