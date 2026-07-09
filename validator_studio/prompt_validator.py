from __future__ import annotations

from pathlib import Path
from typing import Optional

from validator_studio.schemas.validation_base import (
    ArtifactRef,
    DnaSectionScore,
    Issue,
    PromptRef,
    Severity,
    SourceKnowledgeRef,
    Status,
    ValidationReport,
)
from validator_studio.scoring import score_prompt_categories, status_for_score
from validator_studio.utils import find_dna_path, load_json, normalize_text, sha256_file, sha256_text, token_set, validation_config


def _coverage_score(required: list[dict], prompt_text: str) -> tuple[float, list[Issue], list[DnaSectionScore]]:
    text_tokens = token_set(prompt_text)
    issues: list[Issue] = []
    sections: list[DnaSectionScore] = []
    if not required:
        return 100, issues, sections
    scores = []
    for item in required:
        expected = str(item.get("value", ""))
        expected_tokens = token_set(expected)
        if not expected_tokens:
            score = 100
        else:
            score = round(100 * len(expected_tokens & text_tokens) / len(expected_tokens), 2)
        scores.append(score)
        sections.append(DnaSectionScore(
            section="dna_coverage",
            key=str(item.get("key", "")),
            score=score,
            status=status_for_score(score),
            reason=f"Prompt covers {score:.1f}% of key tokens for expected DNA value.",
            evidence=expected,
            category="dna_coverage",
        ))
        if score < 60:
            issues.append(Issue(
                issue=f"Prompt under-specifies required DNA key: {item.get('key')}",
                severity=Severity.MEDIUM,
                suggestion=f"Add concrete wording for: {expected}",
            ))
    return round(sum(scores) / len(scores), 2), issues, sections


def build_prompt_validation_report(
    project: str,
    subject: str,
    prompt: dict,
    dna: dict,
    prompt_file: str,
    dna_file: str,
    dna_hash: str,
) -> ValidationReport:
    config = validation_config()
    final_prompt = str(prompt.get("final_prompt", ""))
    normalized_prompt = normalize_text(final_prompt)
    required = list(prompt.get("required_dna") or dna.get("invariant", []))
    dna_coverage, issues, sections = _coverage_score(required, final_prompt)

    forbidden = list(prompt.get("forbidden") or dna.get("forbidden", []))
    conflicts = []
    for item in forbidden:
        rule = str(item.get("rule", ""))
        rule_positive = normalize_text(rule.replace("no ", "").replace("No ", ""))
        if rule_positive and rule_positive in normalized_prompt:
            conflicts.append(rule)
    forbidden_conflict = 0 if conflicts else 100
    for rule in conflicts:
        issues.append(Issue(
            issue=f"Prompt may include forbidden concept: {rule}",
            severity=Severity.HIGH,
            suggestion="Move this concept into negative constraints or remove it from the positive prompt body.",
        ))

    words = [word for word in normalized_prompt.split() if word]
    word_count = len(words)
    clarity = 95 if 35 <= word_count <= 220 else max(45, 100 - abs(word_count - 120) * 0.35)
    token_efficiency = max(45, min(100, 115 - word_count * 0.12))
    specificity_terms = {"realistic", "photo", "window", "material", "light", "room", "hotel", "texture", "lens", "composition"}
    specificity = min(100, 45 + len(specificity_terms & set(words)) * 8)
    production_readiness = round((dna_coverage * 0.45 + forbidden_conflict * 0.35 + clarity * 0.20), 2)

    category_scores = {
        "dna_coverage": dna_coverage,
        "forbidden_conflict": forbidden_conflict,
        "clarity": round(clarity, 2),
        "token_efficiency": round(token_efficiency, 2),
        "output_specificity": round(specificity, 2),
        "production_readiness": production_readiness,
    }
    overall, verdict = score_prompt_categories(category_scores, config)
    report = ValidationReport(
        project=project,
        subject=subject,
        validation_type="prompt",
        artifact_ref=ArtifactRef(type="prompt", file=prompt_file, hash=sha256_text(final_prompt)),
        source_knowledge=[SourceKnowledgeRef(
            file=dna_file,
            dna_version=dna.get("dna_version"),
            dna_contract_version=dna.get("contract_version"),
            hash=dna_hash,
        )],
        prompt_ref=PromptRef(file=prompt_file, prompt_version=prompt.get("prompt_version")),
        overall_score=overall,
        verdict=verdict,
        dna_match_score=dna_coverage,
        section_scores=sections,
        category_scores=category_scores,
        issues=issues,
        recommendation=verdict,
        validation_notes=[
            "Prompt validation is advisory; Module 02 remains the pass/fail build gate.",
            "Scores are deterministic heuristics over prompt.json and DNA JSON.",
        ],
    )
    return report


def validate_prompt(project: str, subject: str, prompt_path: Path) -> ValidationReport:
    prompt = load_json(prompt_path)
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    return build_prompt_validation_report(
        project=project,
        subject=subject,
        prompt=prompt,
        dna=dna,
        prompt_file=str(prompt_path),
        dna_file=str(dna_path),
        dna_hash=sha256_file(dna_path),
    )


def validate_prompt_contract(
    project: str,
    subject: str,
    prompt_contract: dict,
    dna: Optional[dict] = None,
    prompt_file: str = "(in-memory prompt contract)",
) -> ValidationReport:
    dna_path = find_dna_path(project, subject)
    resolved_dna = dna or load_json(dna_path)
    return build_prompt_validation_report(
        project=project,
        subject=subject,
        prompt=prompt_contract,
        dna=resolved_dna,
        prompt_file=prompt_file,
        dna_file=str(dna_path),
        dna_hash=sha256_file(dna_path),
    )
