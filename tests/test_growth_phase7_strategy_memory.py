from __future__ import annotations

import json

import pytest

from analytics_feedback.research_question_generator import generate_research_question_from_analytics
from strategy_memory.pattern_inference import bayesian_qbsr, infer_strategy_pattern, promote_strategy_memory
from strategy_memory.qbsr_guardrail import evaluate_qbsr_guardrail, qbsr_rate
from strategy_memory.weekly_brief import build_weekly_strategy_brief


def _snapshots(n: int = 6) -> list[dict]:
    return [
        {
            "publication_id": f"pub-{index}",
            "qualified_booking_signals": 2,
            "eligible_reach": 100,
            "pillar": "lake_view_rooms",
            "platform": "instagram",
        }
        for index in range(n)
    ]


def test_bayesian_strategy_memory_has_evidence_limitations_scope_and_expiry() -> None:
    memory = infer_strategy_pattern(
        _snapshots(),
        pattern="Lake-view proof-led posts produce qualified booking signals",
        scope={"pillar": "lake_view_rooms", "platform": "instagram"},
        min_sample_size=5,
    )

    assert memory["status"] == "pending_approval"
    assert memory["confidence"] == bayesian_qbsr(12, 600)
    assert memory["scope"]["pillar"] == "lake_view_rooms"
    assert memory["evidence"]
    assert memory["limitations"]
    assert memory["expires_at"]


def test_insufficient_sample_is_inconclusive_and_cannot_promote() -> None:
    memory = infer_strategy_pattern(
        _snapshots(2),
        pattern="Small sample should not become strategy memory",
        scope={"pillar": "guest_voice", "platform": "facebook"},
        min_sample_size=5,
    )

    assert memory["status"] == "INCONCLUSIVE"
    with pytest.raises(ValueError, match="insufficient sample"):
        promote_strategy_memory(memory, approved_by="harry")


def test_strategy_memory_promotion_requires_evidence_limitations_and_approval() -> None:
    memory = infer_strategy_pattern(
        _snapshots(),
        pattern="Qualified booking signal pattern",
        scope={"pillar": "lake_view_rooms", "platform": "instagram"},
    )

    with pytest.raises(ValueError, match="founder approval"):
        promote_strategy_memory(memory)
    with pytest.raises(ValueError, match="evidence and limitations"):
        promote_strategy_memory({**memory, "limitations": []}, approved_by="harry")

    approved = promote_strategy_memory(memory, approved_by="harry")
    assert approved["status"] == "approved"


def test_weekly_strategy_brief_is_advisory_only_and_guardrails_qbsr_drop() -> None:
    memory = infer_strategy_pattern(
        _snapshots(),
        pattern="Use lake-view proof-led posts",
        scope={"pillar": "lake_view_rooms", "platform": "instagram"},
    )
    brief = build_weekly_strategy_brief(week_id="2026-W32", memories=[memory], baseline_qbsr=0.02, candidate_qbsr=0.015)

    assert brief["status"] == "pending_approval"
    assert brief["advisory_only"] is True
    assert brief["guardrails"]["qbsr"]["passed"] is False
    assert brief["recommendations"] == []

    ok = build_weekly_strategy_brief(week_id="2026-W32", memories=[memory], baseline_qbsr=0.02, candidate_qbsr=0.02)
    assert ok["recommendations"][0]["evidence"]
    assert ok["recommendations"][0]["limitations"]


def test_qbsr_rate_and_guardrail() -> None:
    baseline = qbsr_rate(unique_qualified_booking_signals=20, eligible_reach=1000)
    candidate = qbsr_rate(unique_qualified_booking_signals=18, eligible_reach=1000)

    result = evaluate_qbsr_guardrail(baseline_rate=baseline, candidate_rate=candidate, max_relative_drop=0.05)

    assert baseline == 0.02
    assert result["passed"] is False
    assert result["reason"] == "qbsr_guardrail_drop"


def test_analytics_signal_generates_research_question(tmp_path) -> None:
    path = generate_research_question_from_analytics(
        {
            "id": "strategy-lake-view",
            "status": "INCONCLUSIVE",
            "scope": {"pillar": "lake_view_rooms"},
            "pattern": "Lake-view posts are inconclusive",
        },
        root=tmp_path,
    )

    assert path.exists()
    assert "what evidence should Ven Ho collect next" in path.read_text(encoding="utf-8")
    assert path.parent == tmp_path
