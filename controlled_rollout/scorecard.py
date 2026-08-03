from __future__ import annotations

from dataclasses import dataclass
from typing import Any


QUALITY_GATES = {
    "critical_factual_precision": 1.0,
    "brand_adherence": 0.95,
    "copy_image_alignment": 0.95,
    "hotel_dna_pass": 0.95,
    "linh_an_identity_pass": 0.92,
    "duplicate_publication": 0.0,
    "publication_post_id_rate": 0.99,
    "human_acceptance_no_major_edit": 0.70,
    "unplanned_empty_days": 0.0,
}


@dataclass(frozen=True)
class ScorecardResult:
    version: str
    score: float
    passed: bool
    failures: list[str]


def evaluate_golden_set(golden_set: dict[str, Any], *, minimum_score: float = 9.3) -> ScorecardResult:
    version = golden_set.get("version")
    if not version:
        raise ValueError("golden set version is required")
    metrics = golden_set.get("metrics") or {}
    failures: list[str] = []
    normalized_scores: list[float] = []
    for key, gate in QUALITY_GATES.items():
        if key not in metrics:
            failures.append(f"missing:{key}")
            normalized_scores.append(0.0)
            continue
        value = float(metrics[key])
        if key in {"duplicate_publication", "unplanned_empty_days"}:
            passed = value <= gate
            normalized_scores.append(1.0 if passed else 0.0)
        else:
            passed = value >= gate
            normalized_scores.append(min(value / gate, 1.0))
        if not passed:
            failures.append(key)
    score = round((sum(normalized_scores) / len(normalized_scores)) * 10, 2)
    return ScorecardResult(version=version, score=score, passed=score >= minimum_score and not failures, failures=failures)
