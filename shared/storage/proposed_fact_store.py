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
import re
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


# Words that carry no distinguishing meaning in a fact_key -- they are what
# the extractor adds or drops at random between runs.
_KEY_NOISE = frozenset({"rating", "ratings", "review", "reviews", "customer", "guest",
                        "competitor", "hotel", "score", "diem", "danh", "gia",
                        "overall", "average", "avg", "total"})


def _finding(proposal: dict[str, Any]) -> tuple[str, str, str, frozenset[str]]:
    """What identifies a proposal as a finding, independent of its naming."""
    tokens = frozenset(re.split(r"[^a-z0-9]+", str(proposal.get("fact_key", "")).lower())) - _KEY_NOISE
    return (
        str(proposal.get("domain", "")),
        str(proposal.get("source_uri", "")),
        str(proposal.get("value", "")).strip().lower(),
        tokens - {""},
    )


def is_same_finding(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True when two proposals say the same thing under different names.

    The id alone is not enough (2026-08-06). The extractor renames the same
    fact between runs -- one Booking page's 8.8 arrived as
    `competitor.rating_an_homestay_lakeview`, then
    `competitor.an_homestay_lakeview_apartment_rating`, then
    `competitor.an_homestay_rating` -- so an id keyed on fact_key put three
    rows of the same number in front of Harry.

    Same domain, same page and same value is necessary but NOT sufficient:
    on one OTA listing `cleanliness` and `value_for_money` are both 7.9 and
    are different facts. So the meaningful tokens of the key must also line
    up, by subset rather than equality -- the model's renames add or drop
    words (`..._apartment_rating`) but do not contradict.
    """
    domain_a, uri_a, value_a, tokens_a = _finding(a)
    domain_b, uri_b, value_b, tokens_b = _finding(b)
    if (domain_a, uri_a, value_a) != (domain_b, uri_b, value_b):
        return False
    if not tokens_a or not tokens_b:
        # A key made entirely of noise words (`customer_review.overall_rating`)
        # has nothing left to compare, and the empty set is a subset of
        # everything -- which would swallow any unrelated fact that happens to
        # share its number. Only an equally empty key matches it.
        return tokens_a == tokens_b
    return tokens_a <= tokens_b or tokens_b <= tokens_a


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
        kept = list(existing.values())
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for proposal in proposals:
            if proposal["id"] in existing or any(is_same_finding(proposal, item) for item in kept):
                continue
            existing[proposal["id"]] = {
                **proposal,
                "status": PENDING,
                "proposed_at": now,
                "decided_by": None,
                "decided_at": None,
            }
            kept.append(existing[proposal["id"]])
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
