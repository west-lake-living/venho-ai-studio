from __future__ import annotations


def score_relevance(candidate: dict, policy: dict) -> float:
    dims = policy["relevance_dimensions"]
    geo = dims["geographic"].get(candidate.get("geographic"), 0.0)
    thematic = dims["thematic"].get(candidate.get("thematic"), 0.0)
    action = dims["actionability"].get(candidate.get("actionability"), 0.0)
    return round(geo * thematic * action, 4)
