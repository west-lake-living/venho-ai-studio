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
DISPATCHING_STATUS = "DISPATCHING"
GATEWAY_ERROR_STATUS = "GATEWAY_ERROR"
REJECTED_STATUS = "REJECTED"


def list_pending(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict]:
    registry = registry or PublicationRegistry(project, data_root=data_root)
    return [item for item in registry.load()["publications"] if item.get("status") == PENDING_STATUS]


def _dispatch_claimed(
    publication: dict,
    *,
    registry: PublicationRegistry,
    bridge: M07PublishingBridge,
    approved_by: Optional[str] = None,
) -> dict:
    """Fire the real webhook for an already-claimed (status already flipped
    off PENDING_APPROVAL) row, and finalize its status from the response.

    Split out of `approve_and_dispatch` so `retry_dispatch` (GATEWAY_ERROR ->
    retry) can reuse the exact same snapshot-check + dispatch + finalize
    sequence without re-deriving a fresh approval_snapshot each retry.
    """
    publication_id = publication["publication_id"]
    approval_snapshot = publication.get("approval_snapshot")
    package_snapshot = publication.get("package_snapshot")
    if approval_snapshot is None and package_snapshot is not None and approved_by is not None:
        approval_snapshot = create_approval_snapshot(package_snapshot, approved_by=approved_by)
    if approval_snapshot is not None and package_snapshot is not None:
        assert_dispatch_allowed(approval_snapshot, package_snapshot)

    command = {
        "publication_id": publication_id,
        "idempotency_key": publication["idempotency_key"],
        "content_package_id": publication["content_package_id"],
        "platform": publication["platform"],
        "content": publication.get("content"),
    }
    try:
        response = bridge.dispatch(command)
    except Exception as exc:  # noqa: BLE001 - any transport/provider failure must land on GATEWAY_ERROR, never crash mid-claim
        return registry.update(publication_id, status=GATEWAY_ERROR_STATUS, gateway_status=GATEWAY_ERROR_STATUS, gateway_error=str(exc))

    updates: dict = {
        "status": response["status"],
        "gateway_status": response["status"],
    }
    if approved_by is not None:
        updates["approved_by"] = approved_by
    if approval_snapshot is not None:
        updates["approval_snapshot"] = approval_snapshot
    return registry.update(publication_id, **updates)


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
    retry the dispatch (see `retry_dispatch`) instead of re-approving.

    The PENDING_APPROVAL -> DISPATCHING transition is claimed atomically via
    `registry.claim()` *before* the network call, so two concurrent callers
    for the same publication_id (double-click, two browser tabs, a client
    retry after a request timeout) can never both pass the status check and
    both fire the real webhook -- the loser's `claim()` raises immediately.

    When the row carries a `package_snapshot` (daily_cycle always sets one),
    approval is recorded as a real automation_studio exact-version snapshot
    (DoD #7: "owner approval references exact copy + asset versions") rather
    than just flipping a status string -- `assert_dispatch_allowed` re-checks
    the version checksum right before dispatch and raises if it no longer
    matches, so an edit made after queuing can never silently ride through on
    a stale approval. Rows without a snapshot (older/manual reservations)
    fall back to the plain status-flip behavior.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=PENDING_STATUS, claimed_status=DISPATCHING_STATUS)
    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    return _dispatch_claimed(claimed, registry=registry, bridge=bridge, approved_by=approved_by)


def retry_dispatch(
    publication_id: str,
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
) -> dict:
    """Re-fire the webhook for a row stranded in GATEWAY_ERROR.

    Before this existed, a transient Make.com/network failure permanently
    stranded a publication -- approve_and_dispatch refuses non-PENDING_APPROVAL
    rows, so there was no CLI/API path back. Reuses the already-recorded
    approval_snapshot (approved_by is not re-collected -- the original
    approval still stands, only the dispatch attempt is repeated) and the
    same atomic claim as the first attempt.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=GATEWAY_ERROR_STATUS, claimed_status=DISPATCHING_STATUS)
    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    return _dispatch_claimed(claimed, registry=registry, bridge=bridge)


def reject_publication(
    publication_id: str,
    *,
    rejected_by: str,
    reason: Optional[str] = None,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> dict:
    """Human rejects a queued draft -- no dispatch, no network call.

    Only PENDING_APPROVAL rows can be rejected (mirrors approve's guard, same
    atomic claim so a concurrent approve/reject race can't both win). Rejected
    rows fall out of `list_pending()` automatically since that only filters on
    PENDING_APPROVAL -- no separate "hide rejected" logic needed.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=PENDING_STATUS, claimed_status=REJECTED_STATUS)
    return registry.update(claimed["publication_id"], rejected_by=rejected_by, rejected_reason=reason)
