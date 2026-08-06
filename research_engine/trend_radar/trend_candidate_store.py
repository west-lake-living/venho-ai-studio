from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TrendCandidateStore:
    """JSON-file store for scan_trends() output awaiting/holding human approval.

    Mirrors PublicationRegistry's shape (flat JSON list, id-keyed dedupe) but
    intentionally simpler -- no locking, since this is only ever written by
    a single CLI invocation at a time (`trend-scan`/`trend-approve`), never
    concurrently from a cron + a dashboard click the way publications are.
    A candidate only becomes eligible for daily_cycle's Saturday rotation
    once `approve()` sets verified_by_human=True -- brand_safety.yaml's
    `human_approval: mandatory` is enforced here, not just documented.
    """

    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "research" / "trend_candidates.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _save(self, candidates: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    def merge_new(self, scanned: list[dict[str, Any]]) -> int:
        """Insert newly-scanned candidates by id; never overwrites an
        already-approved candidate's verified_by_human flag with a re-scan.
        Returns the count actually inserted."""
        existing = {c["id"]: c for c in self.load()}
        inserted = 0
        now = datetime.now(timezone.utc).isoformat()
        for candidate in scanned:
            if candidate["id"] in existing:
                continue
            existing[candidate["id"]] = {**candidate, "verified_by_human": False, "scanned_at": now}
            inserted += 1
        self._save(list(existing.values()))
        return inserted

    def approve(self, candidate_id: str, *, approved_by: str) -> dict[str, Any]:
        candidates = self.load()
        for candidate in candidates:
            if candidate["id"] == candidate_id:
                candidate["verified_by_human"] = True
                candidate["approved_by"] = approved_by
                candidate["approved_at"] = datetime.now(timezone.utc).isoformat()
                self._save(candidates)
                return candidate
        raise KeyError(f"Unknown trend candidate id: {candidate_id}")

    def reject(self, candidate_id: str, *, rejected_by: str) -> dict[str, Any]:
        """Take a candidate out of circulation for good.

        Kept as a tombstone rather than deleted from the file (2026-08-06),
        which looks like a deletion from the dashboard but behaves better:
        `merge_new` dedupes on id, so a row that is actually removed comes
        straight back on the next Friday scan, and Harry would reject the
        same stale festival every week. `status: rejected` also drops it out
        of `list_eligible_for_saturday` on its own.
        """
        candidates = self.load()
        for candidate in candidates:
            if candidate["id"] == candidate_id:
                candidate["status"] = "rejected"
                candidate["verified_by_human"] = False
                candidate["rejected_by"] = rejected_by
                candidate["rejected_at"] = datetime.now(timezone.utc).isoformat()
                self._save(candidates)
                return candidate
        raise KeyError(f"Unknown trend candidate id: {candidate_id}")

    def list_eligible_for_saturday(self) -> list[dict[str, Any]]:
        """Approved, still-scored-eligible (status != rejected), not-yet-used
        candidates, shaped for special_lane.select_special_lane_candidate
        (type + verified_by_human)."""
        return [
            c for c in self.load()
            if c.get("verified_by_human") is True and c.get("status") == "needs_human_approval" and not c.get("used_at")
        ]

    def mark_used(self, candidate_id: str) -> None:
        """Once a trend candidate has been picked into a real Saturday
        CreativeBrief, exclude it from future rotations -- without this, the
        same approved trend would resurface every time the rotation cursor
        wraps back to its position in the candidate list."""
        candidates = self.load()
        for candidate in candidates:
            if candidate["id"] == candidate_id:
                candidate["used_at"] = datetime.now(timezone.utc).isoformat()
                self._save(candidates)
                return
