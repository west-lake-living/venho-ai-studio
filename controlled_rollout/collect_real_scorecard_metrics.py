from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

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
# Require real paid Vision QC (validator_studio.image_validator) run per
# publication to fill -- daily_cycle defaults image_validation_provider to
# "mock" (Part 5.7/DoD #26 budget discipline), so this data does not exist
# in the registry today. Not fabricated; reported as a real gap instead.
_MISSING_REQUIRES_VISION_QC = {"copy_image_alignment", "hotel_dna_pass", "linh_an_identity_pass"}


def collect_real_scorecard_metrics(
    *, project: str = "venho_hotel", data_root: Path = Path("data/projects"), version: str
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

    data_gaps = [f"{key}: requires real paid Vision QC runs (image_validation_provider!='mock'); none recorded yet" for key in sorted(_MISSING_REQUIRES_VISION_QC)]

    metrics: dict[str, Any] = {}
    if published:
        scored = [row for row in published if (row.get("scorecard_signals") or {}).get("content_brand_fit") is not None]
        if scored:
            metrics["brand_adherence"] = round(sum(row["scorecard_signals"]["content_brand_fit"] for row in scored) / len(scored), 4)
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

    missed_slots = SlotStore(db_path=data_root / project / "growth" / "growth.db").list_all(status="MISSED")
    metrics["unplanned_empty_days"] = len(missed_slots)

    return {"version": version, "metrics": metrics, "sample_size": len(published), "data_gaps": data_gaps}
