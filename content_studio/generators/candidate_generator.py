from __future__ import annotations

from content_studio.generators.candidate_selector import select_best_candidate
from content_studio.generators.provider_text import MockTextProvider, TextProvider


def generate_three_candidates(brief: dict, provider: TextProvider | None = None) -> list[dict]:
    candidates = (provider or MockTextProvider()).generate_candidates(brief)
    if len(candidates) != 3:
        raise ValueError("Provider must return exactly 3 candidates")
    if len({candidate.get("angle_type") for candidate in candidates}) != 3:
        raise ValueError("Candidates must use three different angles")
    return candidates


def generate_and_select_candidate(brief: dict, provider: TextProvider | None = None) -> dict:
    candidates = generate_three_candidates(brief, provider)
    return select_best_candidate(candidates, brief)
