from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from shared.vision.client import MockVisionClient, VisionClient
from shared.vision.structured import extract_json

from validator_studio.schemas.image_validation import (
    AllowedImperfectionObservation,
    DnaMatchObservation,
    ForbiddenObservation,
    ImageObservation,
)
from validator_studio.schemas.validation_base import MatchState, Severity
from validator_studio.utils import BASE_DIR, normalize_text, token_set


CATEGORY_MAP = {
    "lighting_condition": "lighting",
    "wood_tone": "material",
    "floor": "material",
    "wall_color": "material",
    "style_category": "authenticity",
    "hotel_tier": "authenticity",
    "room_shape": "composition",
}


class ObservationSchemaError(ValueError):
    """Layer 1 observe returned data outside the enum-only Validator Studio contract."""


def _assert_no_ai_scores(payload: Any) -> None:
    """Image observe may return confidence, but never scoring fields."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"score", "overall_score", "dna_match_score", "verdict", "recommendation"}:
                raise ObservationSchemaError(f"AI observe must not return scoring field: {key}")
            _assert_no_ai_scores(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_ai_scores(item)


def _build_image_observe_prompt(dna: dict) -> str:
    prompt_path = BASE_DIR / "validator_studio" / "prompts" / "observe_image_against_dna.md"
    base_prompt = prompt_path.read_text(encoding="utf-8")
    payload = {
        "required_dna": [
            {
                "key": item.get("key"),
                "expected": item.get("value"),
                "category": CATEGORY_MAP.get(str(item.get("key", "")), "dna_match"),
                "confidence": item.get("confidence", 1.0),
                "evidence_count": item.get("evidence_count"),
            }
            for item in dna.get("invariant", [])
        ],
        "forbidden": [
            {
                "rule": item.get("rule"),
                "source": item.get("source", "curated"),
                "severity": _severity_for_rule(str(item.get("rule", ""))).value,
            }
            for item in dna.get("forbidden", [])
        ],
        "allowed_imperfections": [
            {"item": item.get("value"), "source": item.get("source", "curated")}
            for item in dna.get("allowed_imperfections", [])
        ],
    }
    return (
        f"{base_prompt}\n\n"
        "VALIDATION INPUT JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Remember: return observe enums/booleans only. Do not return any score, verdict, or recommendation."
    )


def _match_state(expected: str, observed: str) -> MatchState:
    observed_norm = normalize_text(observed)
    if observed_norm in {"", "not visible", "not_visible", "none"}:
        return MatchState.NOT_VISIBLE
    expected_tokens = token_set(expected)
    observed_tokens = token_set(observed)
    if not expected_tokens:
        return MatchState.MATCH
    overlap = len(expected_tokens & observed_tokens) / max(len(expected_tokens), 1)
    if overlap >= 0.55:
        return MatchState.MATCH
    if overlap > 0:
        return MatchState.PARTIAL
    return MatchState.MISMATCH


def _severity_for_rule(rule: str) -> Severity:
    text = normalize_text(rule)
    if any(term in text for term in ("no ", "floor to ceiling", "marble", "luxury", "resort", "generic")):
        return Severity.HIGH
    return Severity.MEDIUM


def _mock_observe_once(image_path: Path, dna: dict) -> ImageObservation:
    client = MockVisionClient()
    raw = client.analyze_image(image_path, "Validator Studio mock observe")
    features = {item["key"]: item for item in raw.get("features", []) if isinstance(item, dict) and "key" in item}
    dna_matches: list[DnaMatchObservation] = []
    for item in dna.get("invariant", []):
        key = item.get("key", "")
        expected = str(item.get("value", ""))
        feature = features.get(key, {})
        observed = str(feature.get("value", "not_visible"))
        state = _match_state(expected, observed)
        category = CATEGORY_MAP.get(key, "dna_match")
        dna_matches.append(DnaMatchObservation(
            key=key,
            expected=expected,
            observed=observed,
            category=category,
            match_state=state,
            confidence=float(feature.get("confidence", item.get("confidence", 1.0)) or 1.0),
            reason=f"Observed '{observed}' against expected '{expected}'.",
            evidence=observed,
        ))

    forced_bad = any(flag in image_path.stem.lower() for flag in ("bad", "forbidden", "wrong", "reject"))
    forbidden = [
        ForbiddenObservation(
            rule=str(item.get("rule", "")),
            source=str(item.get("source", "curated")),
            severity=_severity_for_rule(str(item.get("rule", ""))),
            violated=forced_bad and index == 0,
            confidence=1.0,
            reason="Mock forced violation from artifact filename." if forced_bad and index == 0 else "No violation observed by mock provider.",
        )
        for index, item in enumerate(dna.get("forbidden", []))
    ]
    allowed = [
        AllowedImperfectionObservation(
            item=str(item.get("value", "")),
            present=False,
            reason="Mock provider does not require allowed imperfections to be present.",
        )
        for item in dna.get("allowed_imperfections", [])
    ]
    return ImageObservation(
        dna_matches=dna_matches,
        forbidden=forbidden,
        allowed_imperfections=allowed,
        notes=["mock observation; no network calls"],
    )


def _majority_state(states: list[MatchState]) -> MatchState:
    order = [MatchState.MATCH, MatchState.PARTIAL, MatchState.MISMATCH, MatchState.NOT_VISIBLE]
    counts = Counter(states)
    return max(order, key=lambda state: (counts[state], -order.index(state)))


def _merge_samples(samples: list[ImageObservation]) -> ImageObservation:
    if len(samples) == 1:
        return samples[0]
    by_key: dict[str, list[DnaMatchObservation]] = {}
    for sample in samples:
        for item in sample.dna_matches:
            by_key.setdefault(item.key, []).append(item)
    merged: list[DnaMatchObservation] = []
    for key, items in by_key.items():
        first = items[0]
        merged.append(first.model_copy(update={
            "match_state": _majority_state([item.match_state for item in items]),
            "confidence": round(sum(item.confidence for item in items) / len(items), 3),
        }))
    forbidden: list[ForbiddenObservation] = []
    for index, item in enumerate(samples[0].forbidden):
        violated = any(sample.forbidden[index].violated for sample in samples if index < len(sample.forbidden))
        forbidden.append(item.model_copy(update={"violated": violated}))
    return samples[0].model_copy(update={"dna_matches": merged, "forbidden": forbidden})


def observe_image_against_dna(
    image_path: Path,
    dna: dict,
    provider: str = "mock",
    samples: int = 1,
) -> ImageObservation:
    samples = max(samples, 1)
    if provider == "mock":
        return _merge_samples([_mock_observe_once(image_path, dna) for _ in range(samples)])

    system_prompt = _build_image_observe_prompt(dna)
    client = VisionClient(image_provider=provider, temperature=0.0)
    observed = []
    for _ in range(samples):
        response = client.analyze_image(image_path, system_prompt)
        payload = response if isinstance(response, dict) and "dna_matches" in response else extract_json(str(response))
        _assert_no_ai_scores(payload)
        observed.append(ImageObservation.model_validate(payload))
    return _merge_samples(observed)
