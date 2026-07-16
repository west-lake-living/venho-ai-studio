from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from validator_studio.schemas.image_validation import ImageObservation
from validator_studio.schemas.face_validation import FaceValidationObservation
from validator_studio.schemas.validation_base import (
    AllowedImperfectionCheck,
    DnaSectionScore,
    ForbiddenViolation,
    Issue,
    KillSwitch,
    MatchState,
    Recommendation,
    Severity,
    Status,
)


IMAGE_CATEGORIES = {
    "dna_match",
    "authenticity",
    "composition",
    "lighting",
    "material",
    "technical_quality",
    "forbidden",
}
PROMPT_CATEGORIES = {
    "dna_coverage",
    "forbidden_conflict",
    "clarity",
    "token_efficiency",
    "output_specificity",
    "production_readiness",
}
CONTENT_CATEGORIES = {
    "brand_fit",
    "tone",
    "clarity",
    "cta",
    "language_fit",
    "production_readiness",
}


FACE_DEFAULT_CATEGORIES = {
    "facial_shape",
    "eyes",
    "hair",
    "expression",
    "technical_quality",
}


@dataclass(frozen=True)
class ScoreResult:
    overall_score: float
    verdict: Recommendation
    recommendation: Recommendation
    dna_match_score: float
    category_scores: dict[str, float]
    section_scores: list[DnaSectionScore]
    forbidden_violations: list[ForbiddenViolation]
    allowed_imperfections_check: list[AllowedImperfectionCheck]
    issues: list[Issue]
    kill_switch: KillSwitch


def validate_weights(weights: dict[str, float], expected: set[str]) -> None:
    keys = set(weights)
    if keys != expected:
        raise ValueError(f"Weight categories mismatch. expected={sorted(expected)} actual={sorted(keys)}")
    total = round(sum(weights.values()), 6)
    if total != 1:
        raise ValueError(f"Weight total must be 1.00, got {total}")


def verdict_for_score(score: float) -> Recommendation:
    if score >= 90:
        return Recommendation.APPROVE
    if score >= 80:
        return Recommendation.REVISE
    if score >= 70:
        return Recommendation.REVISE
    if score >= 60:
        return Recommendation.REGENERATE
    return Recommendation.REJECT


def status_for_score(score: float) -> Status:
    if score >= 90:
        return Status.OK
    if score >= 60:
        return Status.WARNING
    return Status.FAIL


def score_match_state(state: MatchState, rubric: dict[str, float]) -> Optional[float]:
    if state == MatchState.NOT_VISIBLE:
        return None
    return float(rubric[state.value])


def weighted_average(items: list[tuple[float, float]]) -> float:
    usable = [(score, weight) for score, weight in items if weight > 0]
    if not usable:
        return 0
    return round(sum(score * weight for score, weight in usable) / sum(weight for _, weight in usable), 2)


def score_image_observation(observation: ImageObservation, config: dict) -> ScoreResult:
    weights = dict(config["image_validation_weights"])
    validate_weights(weights, IMAGE_CATEGORIES)
    rubric = dict(config["rubric"])

    section_scores: list[DnaSectionScore] = []
    category_items: dict[str, list[tuple[float, float]]] = {category: [] for category in IMAGE_CATEGORIES}
    dna_items: list[tuple[float, float]] = []
    issues: list[Issue] = []

    for item in observation.dna_matches:
        score = score_match_state(item.match_state, rubric)
        if score is None:
            continue
        weight = max(item.confidence, 0.01)
        dna_items.append((score, weight))
        category = item.category if item.category in IMAGE_CATEGORIES else "dna_match"
        category_items[category].append((score, weight))
        section = DnaSectionScore(
            section=item.category or "dna_match",
            key=item.key,
            match_state=item.match_state,
            score=score,
            status=status_for_score(score),
            reason=item.reason,
            evidence=item.evidence or item.observed,
            category=category,
        )
        section_scores.append(section)
        if score < 90:
            sev = Severity.HIGH if score == 0 else Severity.MEDIUM
            issues.append(Issue(
                issue=f"{item.key} does not fully match DNA.",
                severity=sev,
                suggestion=f"Strengthen prompt/output direction for: {item.expected}",
            ))

    dna_match_score = weighted_average(dna_items)

    category_scores: dict[str, float] = {}
    for category in IMAGE_CATEGORIES:
        if category == "dna_match":
            category_scores[category] = dna_match_score
        elif category == "forbidden":
            continue
        else:
            category_scores[category] = weighted_average(category_items[category]) if category_items[category] else dna_match_score

    forbidden_violations = [
        ForbiddenViolation(
            rule=item.rule,
            source=item.source,
            severity=item.severity,
            violated=item.violated,
            confidence=item.confidence,
            reason=item.reason,
        )
        for item in observation.forbidden
    ]
    any_forbidden = any(item.violated for item in forbidden_violations)
    category_scores["forbidden"] = 0 if any_forbidden else 100

    allowed_checks = [
        AllowedImperfectionCheck(item=item.item, present=item.present, penalized=False, reason=item.reason)
        for item in observation.allowed_imperfections
    ]

    overall = round(sum(category_scores[name] * weights[name] for name in weights), 2)
    high_forbidden = [item for item in forbidden_violations if item.violated and item.severity == Severity.HIGH]
    kill_switch = KillSwitch()
    if high_forbidden:
        cap = float(config["kill_switch"]["forbidden_high_cap"])
        overall = min(overall, cap)
        kill_switch = KillSwitch(triggered=True, reason="high-severity forbidden violated")
        issues.insert(0, Issue(
            issue=f"Forbidden rule violated: {high_forbidden[0].rule}",
            severity=Severity.HIGH,
            suggestion="Regenerate the artifact with the forbidden rule stated clearly in the negative constraints.",
        ))

    recommendation = Recommendation.REGENERATE if kill_switch.triggered else verdict_for_score(overall)
    verdict = Recommendation.REJECT if kill_switch.triggered else recommendation
    return ScoreResult(
        overall_score=overall,
        verdict=verdict,
        recommendation=recommendation,
        dna_match_score=dna_match_score,
        category_scores=category_scores,
        section_scores=section_scores,
        forbidden_violations=forbidden_violations,
        allowed_imperfections_check=allowed_checks,
        issues=issues,
        kill_switch=kill_switch,
    )


def score_prompt_categories(category_scores: dict[str, float], config: dict) -> tuple[float, Recommendation]:
    weights = dict(config["prompt_validation_weights"])
    validate_weights(weights, PROMPT_CATEGORIES)
    missing = PROMPT_CATEGORIES - set(category_scores)
    if missing:
        raise ValueError(f"Missing prompt scores: {sorted(missing)}")
    overall = round(sum(category_scores[name] * weights[name] for name in weights), 2)
    return overall, verdict_for_score(overall)


def score_content_categories(category_scores: dict[str, float], config: dict) -> tuple[float, Recommendation]:
    weights = dict(config["content_validation_weights"])
    validate_weights(weights, CONTENT_CATEGORIES)
    missing = CONTENT_CATEGORIES - set(category_scores)
    if missing:
        raise ValueError(f"Missing content scores: {sorted(missing)}")
    overall = round(sum(category_scores[name] * weights[name] for name in weights), 2)
    return overall, verdict_for_score(overall)


def score_face_observation(observation: FaceValidationObservation, rubric: dict) -> ScoreResult:
    gates = observation.gates
    failed_gates = [gate for gate in gates if not gate.passed]
    weights = dict(rubric.get("weighted", {}))
    if weights:
        validate_weights(weights, set(weights))
    else:
        weights = {category: 1 / len(FACE_DEFAULT_CATEGORIES) for category in FACE_DEFAULT_CATEGORIES}

    category_scores = {
        category: float(observation.weighted_scores.get(category, 0))
        for category in weights
    }
    # Older observer responses occasionally used normalized 0..1 values even
    # though Validator Studio reports every category on a 0..100 scale.
    if category_scores and all(0 <= score <= 1 for score in category_scores.values()):
        category_scores = {
            category: round(score * 100, 2)
            for category, score in category_scores.items()
        }
    category_scores = {
        category: max(0.0, min(100.0, score))
        for category, score in category_scores.items()
    }
    section_scores = [
        DnaSectionScore(
            section="face_gate",
            key=gate.gate,
            score=100 if gate.passed else 0,
            status=Status.OK if gate.passed else Status.FAIL,
            reason=gate.reason,
            evidence=gate.evidence,
            category="face_gate",
        )
        for gate in gates
    ]
    section_scores.extend([
        DnaSectionScore(
            section="face_weighted",
            key=category,
            score=score,
            status=status_for_score(score),
            reason="Weighted face rubric score.",
            category=category,
        )
        for category, score in category_scores.items()
    ])
    issues = [
        Issue(
            issue=f"Face binary gate failed: {gate.gate}",
            severity=Severity.HIGH,
            suggestion="Reject this character image and regenerate from the approved fictional Face DNA.",
        )
        for gate in failed_gates
    ]
    if failed_gates:
        return ScoreResult(
            overall_score=0,
            verdict=Recommendation.REJECT,
            recommendation=Recommendation.REJECT,
            dna_match_score=0,
            category_scores=category_scores,
            section_scores=section_scores,
            forbidden_violations=[],
            allowed_imperfections_check=[],
            issues=issues,
            kill_switch=KillSwitch(triggered=True, reason="face binary gate failed"),
        )

    overall = round(sum(category_scores[category] * weights[category] for category in weights), 2)
    verdict = verdict_for_score(overall)
    return ScoreResult(
        overall_score=overall,
        verdict=verdict,
        recommendation=verdict,
        dna_match_score=overall,
        category_scores=category_scores,
        section_scores=section_scores,
        forbidden_violations=[],
        allowed_imperfections_check=[],
        issues=issues,
        kill_switch=KillSwitch(triggered=False, reason=""),
    )
