from __future__ import annotations

from pathlib import Path

from validator_studio.naturalness.dna_leak_check import check_dna_leak
from validator_studio.naturalness.emoji_check import check_emoji
from validator_studio.naturalness.lexical_check import check_lexical
from validator_studio.naturalness.repetition_guard import check_repetition
from validator_studio.naturalness.rhythm_check import check_rhythm
from validator_studio.naturalness.specificity_check import check_specificity
from validator_studio.naturalness.structural_check import check_structure
from validator_studio.naturalness.voice_distance import voice_distance_violations
from validator_studio.naturalness.report import NaturalnessReport, Violation


def evaluate_naturalness(
    text: str,
    *,
    recent_posts: list[str] | tuple[str, ...] = (),
    concrete_details: list[str] | tuple[str, ...] = (),
    voice_corpus_root: Path | None = None,
    lexical_rules_path: Path | None = None,
    rewrite_round: int = 0,
) -> NaturalnessReport:
    """Run the complete deterministic M03 naturalness sub-gate.

    ``rewrite_round`` is zero-based.  A failing third pass is escalated when
    the caller submits ``rewrite_round=2``; no threshold is relaxed to make a
    draft pass.
    """
    if not isinstance(text, str) or not text.strip():
        return NaturalnessReport(
            verdict="REWRITE" if rewrite_round < 2 else "ESCALATE_HUMAN",
            violations=[Violation(
                rule_id="TX-EMPTY",
                message="Nội dung trống.",
                suggestion="Sinh lại một bản có hook, thân bài và kết cụ thể.",
            )],
            specificity_score=0.0,
            rewrite_round=rewrite_round,
        )

    violations: list[Violation] = []
    violations.extend(check_dna_leak(text))
    violations.extend(check_lexical(text, rules_path=lexical_rules_path))
    violations.extend(check_structure(text))
    specificity, specificity_violations = check_specificity(text, concrete_details=list(concrete_details))
    violations.extend(specificity_violations)
    violations.extend(check_rhythm(text))
    violations.extend(check_emoji(text))
    violations.extend(check_repetition(text, list(recent_posts)))
    distance, voice_violations = voice_distance_violations(text, voice_corpus_root)
    violations.extend(voice_violations)

    hard_failures = [item for item in violations if item.severity == "error"]
    if not hard_failures:
        verdict = "PASS"
    elif rewrite_round >= 2:
        verdict = "ESCALATE_HUMAN"
    else:
        verdict = "REWRITE"
    return NaturalnessReport(
        verdict=verdict,
        violations=violations,
        specificity_score=specificity,
        rewrite_round=rewrite_round,
        voice_distance=distance,
    )
