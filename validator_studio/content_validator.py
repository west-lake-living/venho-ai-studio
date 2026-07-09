from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

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
from validator_studio.scoring import score_content_categories, status_for_score
from validator_studio.utils import BASE_DIR, find_dna_path, load_json, load_yaml, sha256_file, sha256_text, token_set, validation_config


VI_MARKS = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
HARD_SELL_TERMS = {"book now", "limited offer", "best in hanoi", "5 star", "five star", "luxury resort", "sang chanh nhat", "sang chảnh nhất"}
CTA_TERMS = {"message", "inbox", "availability", "check availability", "liên hệ", "nhắn", "đặt phòng", "xem phòng", "dat phong"}
EN_MARKERS = {"west lake", "hanoi", "hotel", "room", "stay", "message", "availability"}


def _load_prompt_rules(project: str) -> dict[str, Any]:
    path = BASE_DIR / "config" / "projects" / project / "prompt_rules.yaml"
    if not path.exists():
        return {}
    return load_yaml(path)


def _contains_vietnamese(text: str) -> bool:
    lowered = text.lower()
    return any(ch in lowered for ch in VI_MARKS)


def _language_score(text: str, target_language: str) -> float:
    lowered = text.lower()
    has_vi = _contains_vietnamese(lowered)
    has_en = any(marker in lowered for marker in EN_MARKERS)
    if target_language == "vi":
        return 100 if has_vi else 55
    if target_language == "en":
        return 70 if has_vi else 100
    if has_vi and has_en:
        return 100
    return 70


def _restriction_issues(text: str, restrictions: list[str]) -> list[Issue]:
    lowered = text.lower()
    issues: list[Issue] = []
    for rule in restrictions:
        normalized_rule = rule.lower()
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", normalized_rule)
        phrases = [a or b for a, b in quoted]
        if "5 star" in normalized_rule or "5 sao" in normalized_rule:
            phrases.extend(["5 star", "5 sao", "five star"])
        if "best in hanoi" in normalized_rule:
            phrases.append("best in hanoi")
        if any(phrase and phrase in lowered for phrase in phrases):
            issues.append(Issue(
                issue=f"Content appears to violate restriction: {rule}",
                severity=Severity.HIGH,
                suggestion="Remove or soften this claim; keep the copy factual and aligned with Knowledge.",
            ))
    return issues


def _score_brand_fit(text: str, dna: dict, prompt_rules: dict[str, Any]) -> float:
    source_terms = []
    source_terms.extend(str(item.get("value", "")) for item in dna.get("invariant", []))
    source_terms.extend(prompt_rules.get("brand_dna", []))
    expected_tokens = set()
    for value in source_terms:
        expected_tokens.update(token_set(value))
    text_tokens = token_set(text)
    if not expected_tokens:
        return 80
    overlap = len(expected_tokens & text_tokens) / len(expected_tokens)
    return round(min(100, 45 + overlap * 180), 2)


def _score_tone(text: str, prompt_rules: dict[str, Any]) -> float:
    lowered = text.lower()
    score = 82.0
    tone = str(prompt_rules.get("tone", "")).lower()
    for marker in ("warm", "authentic", "unhurried", "real", "local"):
        if marker in tone and marker in lowered:
            score += 4
    if any(term in lowered for term in HARD_SELL_TERMS):
        score -= 35
    if "!!!" in text or text.count("!") > 2:
        score -= 15
    return round(max(0, min(100, score)), 2)


def _score_clarity(text: str) -> float:
    words = re.findall(r"\w+", text)
    sentences = [chunk.strip() for chunk in re.split(r"[.!?\n]+", text) if chunk.strip()]
    if not words:
        return 0
    score = 95.0
    if len(words) < 35:
        score -= 20
    if len(words) > 220:
        score -= min(35, (len(words) - 220) * 0.15)
    if sentences:
        avg_sentence = len(words) / len(sentences)
        if avg_sentence > 34:
            score -= 15
    return round(max(0, min(100, score)), 2)


def _score_cta(text: str, prompt_rules: dict[str, Any]) -> float:
    lowered = text.lower()
    has_cta = any(term in lowered for term in CTA_TERMS)
    hard_sell = any(term in lowered for term in HARD_SELL_TERMS)
    if has_cta and not hard_sell:
        return 100
    if has_cta:
        return 65
    return 45 if prompt_rules.get("cta_rule") else 70


def _section(key: str, score: float, reason: str) -> DnaSectionScore:
    return DnaSectionScore(
        section="content_quality",
        key=key,
        score=score,
        status=status_for_score(score),
        reason=reason,
        category=key,
    )


def validate_content(
    project: str,
    subject: str,
    draft_path: Path,
    platform: str = "facebook",
    target_language: Optional[str] = None,
    prompt_path: Optional[Path] = None,
) -> ValidationReport:
    config = validation_config()
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    prompt_rules = _load_prompt_rules(project)
    text = draft_path.read_text(encoding="utf-8").strip()
    prompt_ref = None
    if prompt_path:
        prompt = load_json(prompt_path)
        target_language = target_language or prompt.get("target_language")
        prompt_ref = PromptRef(file=str(prompt_path), prompt_version=prompt.get("prompt_version"))
        restrictions = list(prompt.get("restrictions", []))
    else:
        restrictions = []
    target_language = target_language or prompt_rules.get("default_target_language", "bilingual")
    restrictions.extend(prompt_rules.get("restrictions", []))

    brand_fit = _score_brand_fit(text, dna, prompt_rules)
    tone = _score_tone(text, prompt_rules)
    clarity = _score_clarity(text)
    cta = _score_cta(text, prompt_rules)
    language_fit = _language_score(text, target_language)
    production_readiness = round((brand_fit * 0.30 + tone * 0.25 + clarity * 0.20 + cta * 0.15 + language_fit * 0.10), 2)
    category_scores = {
        "brand_fit": brand_fit,
        "tone": tone,
        "clarity": clarity,
        "cta": cta,
        "language_fit": language_fit,
        "production_readiness": production_readiness,
    }
    overall, verdict = score_content_categories(category_scores, config)
    issues = _restriction_issues(text, restrictions)
    if cta < 70:
        issues.append(Issue(
            issue="Soft call-to-action is missing or too hard-sell.",
            severity=Severity.MEDIUM,
            suggestion="End with a gentle invitation to message the page or check availability.",
        ))
    if language_fit < 80:
        issues.append(Issue(
            issue=f"Draft language does not fit target_language={target_language}.",
            severity=Severity.MEDIUM,
            suggestion="Rewrite the draft in the requested language without penalizing valid Vietnamese content.",
        ))

    section_scores = [
        _section("brand_fit", brand_fit, "Overlap with DNA and project brand rules."),
        _section("tone", tone, "Tone follows warm, authentic, unhurried project rules."),
        _section("clarity", clarity, "Length and sentence shape are production-readable."),
        _section("cta", cta, "Soft CTA presence and hard-sell risk."),
        _section("language_fit", language_fit, f"Language fit for target_language={target_language}."),
        _section("production_readiness", production_readiness, f"Platform readiness for {platform}."),
    ]
    return ValidationReport(
        project=project,
        subject=subject,
        validation_type="content",
        artifact_ref=ArtifactRef(type="content", file=str(draft_path), hash=sha256_text(text)),
        source_knowledge=[SourceKnowledgeRef(
            file=str(dna_path),
            dna_version=dna.get("dna_version"),
            dna_contract_version=dna.get("contract_version"),
            hash=sha256_file(dna_path),
        )],
        prompt_ref=prompt_ref,
        overall_score=overall,
        verdict=verdict,
        dna_match_score=brand_fit,
        section_scores=section_scores,
        category_scores=category_scores,
        issues=issues,
        recommendation=verdict,
        validation_notes=[
            "Content validation is advisory and does not rewrite the draft.",
            f"platform={platform}; target_language={target_language}",
        ],
    )
