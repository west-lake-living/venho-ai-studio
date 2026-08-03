from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from strategy_memory.qbsr_guardrail import evaluate_qbsr_guardrail


def build_weekly_strategy_brief(
    *,
    week_id: str,
    memories: list[dict[str, Any]],
    baseline_qbsr: float,
    candidate_qbsr: float,
) -> dict[str, Any]:
    recommendations = []
    for memory in memories:
        if memory.get("status") not in {"pending_approval", "approved"}:
            continue
        if not memory.get("evidence") or not memory.get("limitations"):
            raise ValueError("recommendation requires evidence and limitations")
        recommendations.append(
            {
                "pattern": memory["pattern"],
                "confidence": memory["confidence"],
                "scope": memory.get("scope", {}),
                "expires_at": memory["expires_at"],
                "evidence": memory["evidence"],
                "limitations": memory["limitations"],
                "status": "pending_approval",
            }
        )
    guardrail = evaluate_qbsr_guardrail(baseline_rate=baseline_qbsr, candidate_rate=candidate_qbsr)
    return {
        "week_id": week_id,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pending_approval",
        "advisory_only": True,
        "recommendations": recommendations if guardrail["passed"] else [],
        "guardrails": {"qbsr": guardrail},
    }
