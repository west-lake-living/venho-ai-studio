from __future__ import annotations

import os
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from automation_studio.approval_snapshot import assert_dispatch_allowed, create_approval_snapshot
from controlled_rollout.rollout_state_store import RolloutStateStore
from growth_orchestrator.bridges.m07_publishing_bridge import (
    M07PublishingBridge,
    m07_publishing_bridge_from_env,
)
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore
from validator_studio.alignment_validator import validate_alignment
from validator_studio.claim_validator import ClaimValidator
from validator_studio.content_validator import validate_content
from validator_studio.schemas.validation_base import Recommendation

PENDING_STATUS = "PENDING_APPROVAL"
DISPATCHING_STATUS = "DISPATCHING"
GATEWAY_ERROR_STATUS = "GATEWAY_ERROR"
REJECTED_STATUS = "REJECTED"
NEEDS_REVISION_STATUS = "NEEDS_REVISION"
EDITING_STATUS = "EDITING"
SHADOW_HELD_STATUS = "SHADOW_HELD"
EDITABLE_STATUSES = {PENDING_STATUS, GATEWAY_ERROR_STATUS, SHADOW_HELD_STATUS}
# Rows a dispatch can be (re-)attempted from: a failed one, and one the
# rollout gate below parked. Approval itself is not repeated for either.
REDISPATCHABLE_STATUSES = {GATEWAY_ERROR_STATUS, SHADOW_HELD_STATUS}

SHADOW_STAGE = "shadow"
APPROVED_SCHEDULED_STATUS = "APPROVED_SCHEDULED"

_SLOT_DATE_PATTERN = re.compile(r"^slot-(\d{4}-\d{2}-\d{2})-")


def _scheduled_week_start(publication: dict) -> date | None:
    """Return the Monday for a publication's immutable cadence slot."""
    slot_id = publication.get("slot_id") or ""
    match = _SLOT_DATE_PATTERN.match(slot_id)
    if match is None:
        return None
    slot_date = date.fromisoformat(match.group(1))
    return slot_date - timedelta(days=slot_date.weekday())


def _rollout_stage(*, project: str, data_root: Path) -> str:
    """Current `controlled_rollout` stage, defaulting to `shadow` on any
    read failure -- an unreadable/corrupt rollout state must fail closed
    (hold the post) rather than open (publish it)."""
    try:
        return RolloutStateStore(project, data_root).status().get("current_stage", SHADOW_STAGE)
    except Exception:  # noqa: BLE001 - see docstring: unreadable state means hold, not publish
        return SHADOW_STAGE


def list_pending(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict]:
    """Rows the operator has an action to take on right now.

    Includes both PENDING_APPROVAL (needs Duyệt/Từ chối/Sửa) and GATEWAY_ERROR
    (approved already, dispatch failed -- needs Thử lại gửi/Sửa). A
    SHADOW_HELD row was already approved, so it is not a draft to review and
    belongs in rollout/history monitoring rather than this action queue.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    actionable = {PENDING_STATUS, GATEWAY_ERROR_STATUS}
    return [item for item in registry.load()["publications"] if item.get("status") in actionable]


def approve_week(
    *,
    approved_by: str,
    week_start: date,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict]:
    """Approve every pending platform post scheduled for one ISO week.

    This is deliberately a state-only operation: it records an exact content
    snapshot and the weekly approval, but does not instantiate a publishing
    bridge or make a network call.  The scheduler is responsible for the
    later, per-slot dispatch.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    candidates = [
        item
        for item in registry.load()["publications"]
        if item.get("status") == PENDING_STATUS
        and (scheduled_week := _scheduled_week_start(item)) is not None
        and week_start <= scheduled_week < week_start + timedelta(days=14)
    ]
    if not candidates:
        raise ValueError(f"no PENDING_APPROVAL publications scheduled for two-week cycle starting {week_start.isoformat()}")

    approved_at = datetime.now(timezone.utc).isoformat()
    updates: list[tuple[str, str, dict]] = []
    for publication in candidates:
        package_snapshot = publication.get("package_snapshot")
        approval_snapshot = (
            create_approval_snapshot(package_snapshot, approved_by=approved_by)
            if package_snapshot is not None
            else None
        )
        updates.append(
            (
                publication["publication_id"],
                PENDING_STATUS,
                {
                    "status": APPROVED_SCHEDULED_STATUS,
                    "approved_by": approved_by,
                    "approved_at": approved_at,
                    "approval_scope": "weekly_schedule",
                    "approval_snapshot": approval_snapshot,
                },
            )
        )
    return registry.update_many_if_status(updates)


def _advance_slot_on_dispatch_success(
    publication: dict, *, slot_store: Optional[SlotStore], confirmed_published: bool = False
) -> None:
    """Best-effort PENDING_APPROVAL -> FILLED -> DISPATCHED on the slot this
    publication's daily_cycle run recorded (`slot_id`, absent on older rows
    or when daily_cycle ran without slot tracking). Never raises: a stale/
    already-advanced slot or a missing slot_store must not block the real
    dispatch this is just bookkeeping for.

    `confirmed_published` carries it the last step to COMPLETED. That
    transition existed in the state machine with no production caller, so
    every slot stopped at DISPATCHED -- "handed to Make" -- and the table
    could not distinguish a post the platform actually accepted from one
    that died inside the scenario. It is only true when Make answered
    synchronously with a real platform outcome
    (make_gateway.interpret_make_response -> PUBLISHED).
    """
    slot_id = publication.get("slot_id")
    if not slot_id or slot_store is None:
        return
    try:
        slot = slot_store.get(slot_id)
        if slot is None:
            return
        if slot.status == "PENDING_APPROVAL":
            filled_from = publication.get("filled_from") or "pipeline"
            slot_store.transition(slot_id, "FILLED", content_package_id=publication.get("content_package_id"), filled_from=filled_from)
            slot_store.transition(slot_id, "DISPATCHED")
        elif slot.status == "FILLED":
            slot_store.transition(slot_id, "DISPATCHED")
        if confirmed_published and (slot_store.get(slot_id) or slot).status == "DISPATCHED":
            slot_store.transition(slot_id, "COMPLETED")
    except Exception:  # noqa: BLE001 - slot bookkeeping must never block a real dispatch that already succeeded
        pass


def _preflight_claim_alignment(
    publication: dict,
    *,
    project: str,
    data_root: Path,
) -> dict:
    """Re-run ClaimValidator/validate_alignment right before the real
    webhook fires (PB-005 pre-flight, v3.1 §9.4).

    `daily_cycle` queues a draft once; Harry may approve it days later once
    the weekly batch is reviewed. A Knowledge Fact backing a claim can
    expire in that window (DoD #15: "fact hết hạn ... revoke approval của
    package chưa publish") -- before this, only `edit_publication` re-ran
    this check, so an *unedited* approved row could ride a since-expired
    fact straight to a real Facebook/Instagram post. This closes that gap
    at the last possible moment: inside the same atomic claim, before
    `bridge.dispatch()` is ever called.

    Rows written before 2026-08-05 (no persisted `creative_brief`) skip this
    -- same convention as `edit_publication` -- and are reported as
    `claim_alignment_skipped: true`, not silently treated as passing.
    """
    creative_brief = publication.get("creative_brief")
    if creative_brief is None:
        return {"claim_alignment_skipped": True, "passed": True}
    claim_report = ClaimValidator(project=project, data_root=data_root).validate(publication.get("claims") or [])
    alignment_report = validate_alignment(creative_brief, publication.get("scene_summary") or {})
    passed = not claim_report["kill_switches"] and not alignment_report["kill_switches"]
    return {"claim_report": claim_report, "alignment_report": alignment_report, "passed": passed}


def _dispatch_claimed(
    publication: dict,
    *,
    registry: PublicationRegistry,
    bridge: M07PublishingBridge,
    approved_by: Optional[str] = None,
    slot_store: Optional[SlotStore] = None,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    allow_shadow: bool = False,
) -> dict:
    """Fire the real webhook for an already-claimed (status already flipped
    off PENDING_APPROVAL) row, and finalize its status from the response.

    Split out of `approve_and_dispatch` so `retry_dispatch` (GATEWAY_ERROR ->
    retry) can reuse the exact same snapshot-check + dispatch + finalize
    sequence without re-deriving a fresh approval_snapshot each retry.

    While the rollout stage is `shadow` the webhook does not fire at all and
    the row parks on SHADOW_HELD (see the gate below). `allow_shadow=True` is
    the deliberate, recorded override for publishing a specific post before
    the stage advances.
    """
    publication_id = publication["publication_id"]

    preflight = _preflight_claim_alignment(publication, project=project, data_root=data_root)
    if not preflight["passed"]:
        return registry.update(
            publication_id,
            status=NEEDS_REVISION_STATUS,
            preflight_report=preflight,
        )

    approval_snapshot = publication.get("approval_snapshot")
    package_snapshot = publication.get("package_snapshot")
    if approval_snapshot is None and package_snapshot is not None and approved_by is not None:
        approval_snapshot = create_approval_snapshot(package_snapshot, approved_by=approved_by)
    if approval_snapshot is not None and package_snapshot is not None:
        assert_dispatch_allowed(approval_snapshot, package_snapshot)

    # Rollout gate (2026-08-06). `shadow` is the stage the Growth Agent has
    # been in since it went live, and until now it meant nothing in code:
    # RolloutStateStore was a governance record, so the only thing standing
    # between a stage-shadow agent and a real Facebook post was an empty
    # MAKE_GROWTH_WEBHOOK_URL in .env.local -- configuration, not logic. Now
    # the stage decides. Everything upstream still runs (generation,
    # validation, approval, snapshot) so shadow exercises the whole pipeline;
    # only the outbound webhook is withheld.
    #
    # Advance the stage with `venho-rollout rollout-advance` (requires a real
    # passing scorecard) to publish normally; `allow_shadow=True` publishes
    # one specific row now and records who overrode it.
    stage = _rollout_stage(project=project, data_root=data_root)
    if stage == SHADOW_STAGE and not allow_shadow:
        updates: dict = {
            "status": SHADOW_HELD_STATUS,
            "gateway_status": SHADOW_HELD_STATUS,
            "rollout_stage": stage,
            "shadow_held_reason": "rollout stage is shadow; dispatch withheld",
        }
        if approved_by is not None:
            updates["approved_by"] = approved_by
        if approval_snapshot is not None:
            updates["approval_snapshot"] = approval_snapshot
        return registry.update(publication_id, **updates)

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
        # A retried row keeps the error text from the attempt that failed,
        # so a row that has since gone through still reads as broken.
        "gateway_error": None,
    }
    # Only present when the Make scenario answers synchronously with the real
    # platform outcome (see make_gateway.interpret_make_response). Never blank
    # out a value an earlier reconciliation already established.
    for field in ("platform_post_id", "permalink"):
        if response.get(field):
            updates[field] = response[field]
    if response["status"] == GATEWAY_ERROR_STATUS:
        updates["gateway_error"] = response.get("error")
    if approved_by is not None:
        updates["approved_by"] = approved_by
    if approval_snapshot is not None:
        updates["approval_snapshot"] = approval_snapshot
    if stage == SHADOW_STAGE:
        # Published despite shadow -- keep the audit trail on the row itself,
        # not only in whatever CLI invocation happened to carry the flag.
        updates["shadow_override_by"] = approved_by or publication.get("approved_by")
    updated = registry.update(publication_id, **updates)
    if response["status"] in ("GATEWAY_ACCEPTED", "PUBLISHED"):
        _advance_slot_on_dispatch_success(
            updated, slot_store=slot_store, confirmed_published=response["status"] == "PUBLISHED"
        )
    return updated


def approve_and_dispatch(
    publication_id: str,
    *,
    approved_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
    slot_store: Optional[SlotStore] = None,
    allow_shadow: bool = False,
) -> dict:
    """Approve a queued draft and immediately dispatch it (Approve-triggers-publish).

    Only PENDING_APPROVAL rows (produced by `daily_cycle.run_daily_cycle`) can
    be approved -- this is the human gate between content prep (cron) and the
    real Make.com webhook firing (this function). Dispatch failure does not
    revert the approval: the row is marked GATEWAY_ERROR so the operator can
    retry the dispatch (see `retry_dispatch`) instead of re-approving.

    Before the webhook ever fires, `_preflight_claim_alignment` re-runs
    ClaimValidator/validate_alignment against the row's persisted claims
    (PB-005 pre-flight, DoD #15) -- a fact that expired in the days between
    queueing and this click lands the row on NEEDS_REVISION instead of
    publishing a since-unsupported claim.

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

    Approval is recorded even when the rollout stage is `shadow` -- the row
    lands on SHADOW_HELD with its approval snapshot intact, so advancing the
    stage later turns it into a plain `retry_dispatch` rather than a re-review.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=PENDING_STATUS, claimed_status=DISPATCHING_STATUS)
    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    slot_store = slot_store or SlotStore(db_path=data_root / project / "growth" / "growth.db")
    return _dispatch_claimed(
        claimed, registry=registry, bridge=bridge, approved_by=approved_by, slot_store=slot_store,
        project=project, data_root=data_root, allow_shadow=allow_shadow,
    )


def retry_dispatch(
    publication_id: str,
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
    slot_store: Optional[SlotStore] = None,
    allow_shadow: bool = False,
) -> dict:
    """Re-fire the webhook for a row stranded in GATEWAY_ERROR or SHADOW_HELD.

    Before this existed, a transient Make.com/network failure permanently
    stranded a publication -- approve_and_dispatch refuses non-PENDING_APPROVAL
    rows, so there was no CLI/API path back. Reuses the already-recorded
    approval_snapshot (approved_by is not re-collected -- the original
    approval still stands, only the dispatch attempt is repeated) and the
    same atomic claim as the first attempt.

    This is also the path a SHADOW_HELD row takes once the rollout stage
    advances: the approval it already carries is still valid, so releasing it
    is a dispatch retry, not a second approval.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    claimed = registry.claim(publication_id, expected_status=REDISPATCHABLE_STATUSES, claimed_status=DISPATCHING_STATUS)
    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    slot_store = slot_store or SlotStore(db_path=data_root / project / "growth" / "growth.db")
    return _dispatch_claimed(
        claimed, registry=registry, bridge=bridge, slot_store=slot_store,
        project=project, data_root=data_root, allow_shadow=allow_shadow,
    )


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
      CreativeBrief object, which the registry did not retain at the time).
    - The row's persisted `claims`/`scene_summary`/`creative_brief` (added
      2026-08-05 to daily_cycle's registry.update call specifically for this)
      are also re-run through the same ClaimValidator/validate_alignment
      M03ValidatorBridge calls -- a kill-switch on either (unsupported claim,
      forbidden/missing scene entity) still blocks re-entering the queue.
      Rows written before 2026-08-05 won't have these fields; that half of
      the gate is skipped for them (logged on the report as
      `claim_alignment_skipped: true`), not silently treated as passing.
    - Important limitation: claims/scene_summary are structured metadata
      captured from the *original* LLM generation, not re-derived from the
      edited prose -- there is no claim-extraction step in this codebase
      that turns arbitrary edited text back into structured claims. So this
      catches "the original claims still have no supporting fact_key" or
      "the original scene plan still uses a forbidden entity", but it
      cannot catch a brand-new false claim Harry types into the edit by
      hand. That is caught by the content-quality rubric's brand_fit/clarity
      checks on a best-effort basis, not guaranteed.

    Only a real Recommendation.APPROVE from content_validator *and* no
    claim/alignment kill-switch re-enters PENDING_APPROVAL; anything else
    lands on NEEDS_REVISION and drops out of the approval queue, same as a
    failed daily_cycle draft would.
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

    content_passed = not report.kill_switch.triggered and report.verdict == Recommendation.APPROVE
    edit_validation: dict = {"content_report": report.model_dump(mode="json")}

    claim_alignment_passed = True
    creative_brief = claimed.get("creative_brief")
    if creative_brief is None:
        edit_validation["claim_alignment_skipped"] = True
    else:
        claim_report = ClaimValidator(project=project, data_root=data_root).validate(claimed.get("claims") or [])
        alignment_report = validate_alignment(creative_brief, claimed.get("scene_summary") or {})
        edit_validation["claim_report"] = claim_report
        edit_validation["alignment_report"] = alignment_report
        if claim_report["kill_switches"] or alignment_report["kill_switches"]:
            claim_alignment_passed = False

    new_content = dict(claimed.get("content") or {})
    new_content["text"] = new_text
    passed = content_passed and claim_alignment_passed
    return registry.update(
        publication_id,
        content=new_content,
        edited_by=edited_by,
        edit_validation=edit_validation,
        status=PENDING_STATUS if passed else NEEDS_REVISION_STATUS,
        # a fresh Approve must always build a new snapshot off the edited
        # content -- never let it ride through on the pre-edit approval.
        approval_snapshot=None,
        approved_by=None,
        gateway_status=None,
        gateway_error=None,
    )
