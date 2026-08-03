from __future__ import annotations


RUBRIC_WEIGHTS = {
    "factual_support": 0.0,
    "brief_adherence": 0.20,
    "audience_relevance": 0.20,
    "hook_strength": 0.15,
    "benefit_clarity": 0.15,
    "brand_voice": 0.10,
    "platform_fit": 0.10,
    "cta_coherence": 0.10,
}


def score_candidate(candidate: dict, brief: dict) -> dict:
    if any(not claim.get("fact_key") for claim in candidate.get("claims", []) if isinstance(claim, dict)):
        return {"total": 0.0, "kill_switch": "unsupported_critical_claim"}
    score = 9.0
    if candidate.get("platform") not in brief.get("platforms", []):
        score -= 1.5
    if brief["single_minded_message"] not in candidate.get("body", ""):
        score -= 1.0
    return {"total": round(max(score, 0.0), 2), "kill_switch": None}


def select_best_candidate(candidates: list[dict], brief: dict) -> dict:
    if len({item.get("angle_type") for item in candidates}) < 3:
        raise ValueError("Three genuinely different candidate angles are required")
    scored = []
    for candidate in candidates:
        rubric = score_candidate(candidate, brief)
        scored.append({**candidate, "rubric": rubric})
    viable = [item for item in scored if not item["rubric"].get("kill_switch")]
    if not viable:
        raise ValueError("No candidate passed factual support")
    return sorted(viable, key=lambda item: item["rubric"]["total"], reverse=True)[0]
