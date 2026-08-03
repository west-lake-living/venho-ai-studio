from __future__ import annotations

from datetime import datetime
from typing import Any

from research_engine.domain.promotion_policy import PromotionPolicy
from research_engine.domain.research_note import ResearchNote


def propose_fact(note: ResearchNote, *, fact_key: str, value: Any, value_type: str, approved_by: str | None = None) -> dict[str, Any]:
    decision = PromotionPolicy().evaluate(note, human_approved=bool(approved_by))
    if not decision.allowed:
        raise ValueError(decision.reason)
    return {
        "fact_key": fact_key,
        "value": value,
        "value_type": value_type,
        "source_type": "document",
        "source_rs_id": note.rs_id,
        "confidence": note.confidence,
        "valid_from": datetime.now().isoformat(),
        "valid_to": note.expires_at.isoformat() if note.expires_at else None,
        "status": "approved",
        "version": 1,
        "approved_by": approved_by,
        "approved_at": datetime.now().isoformat(),
    }
