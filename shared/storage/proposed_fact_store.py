"""Queue of facts a research cycle proposes, waiting for Harry's decision.

Why (2026-08-06): `venho-research promote` took `--approved-by` as an
argument, which means the only way a fact could ever exist was for a human to
already know its key and value and type them into a terminal. There was no
"here is what the research turned up, approve or reject" step at all -- so
the Research OS could collect, but nothing it collected could reach content
without Harry doing the extraction by hand. The vault held zero notes and the
fact store held only the four bootstrap seeds.

This is the missing middle. A cycle writes proposals here; the VENHO OS
dashboard (and `venho-research pending`) lists them; approving one runs the
*existing* promotion path -- R2 synthesis note + human approval -> R3 fact.
Rejecting records the decision so the next cycle does not re-propose it.

Deliberately mirrors TrendCandidateStore: same flat JSON, same id-keyed
dedupe, same single-writer assumption. Nothing here can approve itself --
`approve()` requires an `approved_by`, and the promotion policy it delegates
to still refuses anything that is not an R2 note (DoD #13).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PENDING = "pending_approval"
APPROVED = "approved"
REJECTED = "rejected"


def proposal_id(domain: str, fact_key: str, value: str) -> str:
    """Stable across cycles: re-running a domain must not create a second
    copy of a proposal Harry has already rejected."""
    digest = hashlib.sha256(f"{domain}:{fact_key}:{value}".encode("utf-8")).hexdigest()[:10]
    return f"fact-{domain}-{digest}"


class ProposedFactStore:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "research" / "proposed_facts.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def merge_new(self, proposals: list[dict[str, Any]]) -> int:
        """Insert proposals not already present. An existing row keeps its
        decision: a re-scan must never resurrect something Harry rejected,
        nor reset an approved row back to pending."""
        existing = {item["id"]: item for item in self.load()}
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for proposal in proposals:
            if proposal["id"] in existing:
                continue
            existing[proposal["id"]] = {
                **proposal,
                "status": PENDING,
                "proposed_at": now,
                "decided_by": None,
                "decided_at": None,
            }
            inserted += 1
        self._save(list(existing.values()))
        return inserted

    def list_items(self, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        items = self.load()
        return [item for item in items if status is None or item.get("status") == status]

    def get(self, proposal_id_: str) -> Optional[dict[str, Any]]:
        return next((item for item in self.load() if item["id"] == proposal_id_), None)

    def _decide(self, proposal_id_: str, *, status: str, decided_by: str, **extra: Any) -> dict[str, Any]:
        items = self.load()
        for item in items:
            if item["id"] != proposal_id_:
                continue
            if item.get("status") != PENDING:
                raise ValueError(f"{proposal_id_} is already {item.get('status')}")
            item.update(status=status, decided_by=decided_by, decided_at=datetime.now(timezone.utc).isoformat(), **extra)
            self._save(items)
            return item
        raise KeyError(f"Unknown proposal: {proposal_id_}")

    def mark_approved(self, proposal_id_: str, *, approved_by: str, fact_path: str) -> dict[str, Any]:
        return self._decide(proposal_id_, status=APPROVED, decided_by=approved_by, fact_path=fact_path)

    def mark_rejected(self, proposal_id_: str, *, rejected_by: str, reason: Optional[str] = None) -> dict[str, Any]:
        return self._decide(proposal_id_, status=REJECTED, decided_by=rejected_by, reject_reason=reason)
