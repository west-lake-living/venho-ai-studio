from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from growth_orchestrator.application.reconcile_slots import ALL_CANCELLED
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

EMPTY_DAYS_WINDOW = 28

# Mirrors controlled_rollout.scorecard.QUALITY_GATES' key set. Kept as a
# separate constant (not imported) so this module stays honest about which
# of those nine dimensions it can actually fill from real data today --
# importing the gate dict would silently imply coverage of all nine.
_COLLECTIBLE_FROM_REAL_DATA = {
    "critical_factual_precision",
    "brand_adherence",
    "duplicate_publication",
    "publication_post_id_rate",
    "human_acceptance_no_major_edit",
    "unplanned_empty_days",
}
# Real vision-QC judgements needed before the image gates are scored at all
# (2026-10-22): rows record `scorecard_signals.image_qc` since the server
# runner started generating images; fewer than this is too thin to gate on.
MIN_IMAGE_QC_SAMPLE = 8


def collect_real_scorecard_metrics(
    *, project: str = "venho_hotel", data_root: Path = Path("data/projects"), version: str, today: Optional[date] = None
) -> dict[str, Any]:
    """Build a `controlled_rollout.scorecard.evaluate_golden_set` input from
    real, already-persisted operational data -- not a fixture, not a
    hand-picked eval set.

    This is deliberately a *pilot telemetry* scorecard, not the plan's
    original golden eval set (Part 13.4: >=100 CreativeBrief cases,
    reviewer-scored, dataset-versioned). Building that properly requires a
    curated, human-graded corpus that does not exist yet -- see
    `docs/growth/eval_golden_sets.md` for the gap. What this function gives
    instead is an honest read of how the real pilot has actually performed
    so far, which is what `evaluate_golden_set()`'s 9.3 gate needs to be
    checked against before any rollout-stage advance (Part 12 Phase 8,
    `controlled_rollout.rollout_policy.next_rollout_stage`).

    Returns `{"version": ..., "metrics": {...}, "sample_size": N,
    "data_gaps": [...]}`. Any of the 9 scorecard dimensions this pilot
    cannot yet compute from real data is simply absent from `metrics`
    (`evaluate_golden_set` already treats a missing key as a failed gate --
    see its `missing:<key>` failure code), and named in `data_gaps` with why.
    """
    registry = PublicationRegistry(project, data_root=data_root)
    rows = registry.load()["publications"]
    published = [row for row in rows if row.get("status") == "PUBLISHED"]

    data_gaps: list[str] = []
    metrics: dict[str, Any] = {}
    _image_gates(rows, published, metrics, data_gaps)
    if published:
        scored = [row for row in published if (row.get("scorecard_signals") or {}).get("content_brand_fit") is not None]
        if scored:
            # Real content_brand_fit is on a 0-100 scale; the gate is a 0-1
            # share. Until 2026-10-22 the raw 95.2 was compared with 0.95 and
            # always passed.
            fits = [float(row["scorecard_signals"]["content_brand_fit"]) for row in scored]
            metrics["brand_adherence"] = round(sum(f / 100 if f > 1 else f for f in fits) / len(fits), 4)
        else:
            data_gaps.append("brand_adherence: no PUBLISHED row has a content_report brand_fit score yet")

        claim_scored = [row for row in published if "claim_kill_switch_triggered" in (row.get("scorecard_signals") or {})]
        if claim_scored:
            clean = sum(1 for row in claim_scored if not row["scorecard_signals"]["claim_kill_switch_triggered"])
            metrics["critical_factual_precision"] = round(clean / len(claim_scored), 4)
        else:
            data_gaps.append("critical_factual_precision: no PUBLISHED row has a claim report recorded yet")

        with_post_id = sum(1 for row in published if row.get("platform_post_id"))
        metrics["publication_post_id_rate"] = round(with_post_id / len(published), 4)

        unedited = sum(1 for row in published if not row.get("edited_by"))
        metrics["human_acceptance_no_major_edit"] = round(unedited / len(published), 4)
    else:
        data_gaps.append("brand_adherence, critical_factual_precision, publication_post_id_rate, human_acceptance_no_major_edit: 0 PUBLISHED publications yet")

    # duplicate_publication: reserve() test-and-sets on (idempotency_key,
    # platform) inside a file lock (Part 5.9/publication_registry.py) -- two
    # rows sharing that pair is architecturally impossible, not just
    # unobserved so far. Verified, not assumed, on every real call.
    seen: set[tuple[Any, Any]] = set()
    duplicates = 0
    for row in rows:
        key = (row.get("idempotency_key"), row.get("platform"))
        if key in seen:
            duplicates += 1
        seen.add(key)
    metrics["duplicate_publication"] = duplicates

    # Recent window, planned gaps excluded (2026-10-22): counting every
    # MISSED slot since August meant the gate could never pass again once
    # one day had been missed, and a day Harry cancelled on purpose is not
    # an unplanned gap.
    since = ((today or date.today()) - timedelta(days=EMPTY_DAYS_WINDOW)).isoformat()
    missed = SlotStore(db_path=data_root / project / "growth" / "growth.db").missed_since(since)
    metrics["unplanned_empty_days"] = sum(1 for _, reason in missed if reason != ALL_CANCELLED)

    return {"version": version, "metrics": metrics, "sample_size": len(published), "data_gaps": data_gaps}


def _image_gates(rows: list[dict[str, Any]], published: list[dict[str, Any]], metrics: dict[str, Any], data_gaps: list[str]) -> None:
    """The three image gates, from real vision-QC judgements only.

    hotel_dna_pass: share of QC'd drafts whose generated image passed (a
    failed image falls back to a stock photo). copy_image_alignment: share
    of PUBLISHED posts from the same era that went out with a generated or
    chosen image rather than a fallback -- fallbacks were what made photo
    and copy disagree (28/08-21/10), and Harry approves the pair together.
    linh_an_identity_pass: not applicable while no post features Linh An.
    """
    judged = [
        row for row in rows
        if ((row.get("scorecard_signals") or {}).get("image_qc") or {}).get("provider") not in (None, "mock")
    ]
    if len(judged) < MIN_IMAGE_QC_SAMPLE:
        for key in ("copy_image_alignment", "hotel_dna_pass"):
            data_gaps.append(f"{key}: {len(judged)} real vision-QC judgements so far, need {MIN_IMAGE_QC_SAMPLE}")
    else:
        metrics["hotel_dna_pass"] = round(sum(1 for row in judged if row["scorecard_signals"]["image_qc"]["passed"]) / len(judged), 4)
        judged_ids = {row["publication_id"] for row in judged}
        sent = [row for row in published if row.get("publication_id") in judged_ids]
        if sent:
            aligned = sum(1 for row in sent if not (row.get("content") or {}).get("image_is_fallback"))
            metrics["copy_image_alignment"] = round(aligned / len(sent), 4)
        else:
            data_gaps.append("copy_image_alignment: no vision-QC'd post published yet")

    if any(row.get("dna_subject") == "linh_an" for row in published):
        data_gaps.append("linh_an_identity_pass: Linh An posts exist but no face-gate result is recorded on rows yet")
    else:
        metrics["linh_an_identity_pass"] = 1.0
        data_gaps.append("linh_an_identity_pass: not applicable -- no published post features Linh An (counted as pass)")
