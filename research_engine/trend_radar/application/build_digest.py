from __future__ import annotations


def build_digest(candidates: list[dict], limit: int = 3) -> list[dict]:
    eligible = [item for item in candidates if item.get("status") == "needs_human_approval"]
    return sorted(eligible, key=lambda item: item.get("relevance_score", 0), reverse=True)[:limit]
