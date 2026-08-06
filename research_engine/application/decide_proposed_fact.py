"""Harry's decision on a proposed fact, from the dashboard or the CLI.

Approval deliberately does not write a fact directly. It loads the R2
synthesis note the proposal cites and runs the same `propose_fact` /
`PromotionPolicy` path a hand-typed `venho-research promote` would: R2 only,
confidence at or above threshold, human approval present. A proposal whose
note fails that gate is refused here too -- the approval UI cannot become a
way around the Evidence Ladder (DoD #13).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from research_engine.adapters.m01_facts_bridge import M01FactsBridge
from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.propose_fact import propose_fact
from research_engine.domain.research_note import ResearchNote
from shared.storage.proposed_fact_store import ProposedFactStore


def approve_proposed_fact(
    proposal_id: str,
    *,
    approved_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    vault_root: Path = Path("research"),
    store: Optional[ProposedFactStore] = None,
) -> dict[str, Any]:
    if not approved_by.strip():
        raise ValueError("approved_by is required — a fact cannot approve itself")
    store = store or ProposedFactStore(project=project, data_root=data_root)
    proposal = store.get(proposal_id)
    if proposal is None:
        raise KeyError(f"Unknown proposal: {proposal_id}")
    note_path = proposal.get("synthesis_note")
    if not note_path:
        raise ValueError(f"{proposal_id} cites no synthesis note; nothing to promote from")

    frontmatter = VaultReader(vault_root).read_frontmatter(Path(note_path))
    note = ResearchNote.model_validate(frontmatter)
    fact = propose_fact(
        note,
        fact_key=proposal["fact_key"],
        value=proposal["value"],
        value_type=proposal.get("value_type", "string"),
        approved_by=approved_by,
    )
    path = M01FactsBridge(project=project, data_root=data_root).save_approved_fact(fact)
    updated = store.mark_approved(proposal_id, approved_by=approved_by, fact_path=str(path))
    return {"proposal": updated, "fact_path": str(path), "fact": fact}


def reject_proposed_fact(
    proposal_id: str,
    *,
    rejected_by: str,
    reason: Optional[str] = None,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    store: Optional[ProposedFactStore] = None,
) -> dict[str, Any]:
    store = store or ProposedFactStore(project=project, data_root=data_root)
    return store.mark_rejected(proposal_id, rejected_by=rejected_by, reason=reason)
