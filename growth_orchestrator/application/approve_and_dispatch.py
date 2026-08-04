from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from automation_studio.approval_snapshot import assert_dispatch_allowed, create_approval_snapshot
from growth_orchestrator.bridges.m07_publishing_bridge import (
    M07PublishingBridge,
    m07_publishing_bridge_from_env,
)
from publishing_gateway.publication_registry import PublicationRegistry
from validator_studio.content_validator import validate_content
from validator_studio.schemas.validation_base import Recommendation

PENDING_STATUS = "PENDING_APPROVAL"
DISPATCHING_STATUS = "DISPATCHING"
GATEWAY_ERROR_STATUS = "GATEWAY_ERROR"
REJECTED_STATUS = "REJECTED"
NEEDS_REVISION_STATUS = "NEEDS_REVISION"
EDITING_STATUS = "EDITING"
EDITABLE_STATUSES = {PENDING_STATUS, GATEWAY_ERROR_STATUS}


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


def edit_publication(
    publication_id: str,
    *,
    edited_by: str,
    new_text: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> dict:
    """Edit a queued draft's copy and re-run the real content Validator gate
    before it can re-enter the approval queue.

    Per plan Part 2.1 decision #7 and the ContentPackage invariants (Part
    4.3): "Sửa copy ... sau approval -> tự revoke" -- editing must never let
    a changed draft ride through on a stale approval, and the edited text
    must clear the same bar daily_cycle's own drafts do, not just get
    silently re-queued. Concretely:

    - Editable from PENDING_APPROVAL (not yet approved) or GATEWAY_ERROR (was
      approved, dispatch failed) -- anything already DISPATCHING/
      GATEWAY_ACCEPTED/PUBLISHED cannot be edited (the post already exists or
      is in flight; reject and let a fresh cycle regenerate instead).
    - Any prior `approval_snapshot`/`approved_by`/`gateway_status` is cleared
      unconditionally, even if the edited text ends up re-passing -- a later
      Approve always builds a fresh snapshot off the edited content, never
      the pre-edit one.
    - The edited text is re-scored by `validator_studio.content_validator`
      (the same brand_fit/tone/clarity/cta/language_fit rubric
      M03ValidatorBridge gates on in daily_cycle) against the row's own
      `dna_subject` (persisted on the registry row since 2026-08-04
      specifically so edits can be re-validated without needing the original
      CreativeBrief object, which the registry does not retain). Only a real
      Recommendation.APPROVE re-enters PENDING_APPROVAL; anything else lands
      on NEEDS_REVISION and drops out of the approval queue, same as a
      failed daily_cycle draft would.

    Note: this re-runs the content-quality gate only, not the claim/
    alignment validators (those score against the original CreativeBrief's
    proof_points/scene_summary, which are not persisted on the registry row
    -- persisting the full brief would be a larger change than this edit
    feature warrants; flagged for Harry rather than silently skipped).
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=EDITABLE_STATUSES, claimed_status=EDITING_STATUS)

    dna_subject = claimed.get("dna_subject")
    if not dna_subject:
        registry.update(publication_id, status=NEEDS_REVISION_STATUS, edit_error="missing dna_subject on record; cannot re-validate edit")
        raise ValueError(f"publication_id {publication_id} has no dna_subject on record; cannot re-validate edit")

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(new_text)
            tmp_path = Path(handle.name)
        report = validate_content(project, dna_subject, tmp_path, platform=claimed.get("platform", "facebook"))
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    new_content = dict(claimed.get("content") or {})
    new_content["text"] = new_text
    passed = not report.kill_switch.triggered and report.verdict == Recommendation.APPROVE
    return registry.update(
        publication_id,
        content=new_content,
        edited_by=edited_by,
        edit_validation=report.model_dump(mode="json"),
        status=PENDING_STATUS if passed else NEEDS_REVISION_STATUS,
        # a fresh Approve must always build a new snapshot off the edited
        # content -- never let it ride through on the pre-edit approval.
        approval_snapshot=None,
        approved_by=None,
        gateway_status=None,
        gateway_error=None,
    )
