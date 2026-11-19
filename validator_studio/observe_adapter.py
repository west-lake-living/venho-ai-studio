from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import ValidationError

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


def _assert_no_ai_scores(payload: Any, path: str = "$") -> None:
    """Image observe may return confidence, but never scoring fields."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"score", "overall_score", "dna_match_score", "verdict", "recommendation"}:
                raise ObservationSchemaError(f"field {path}.{key}: scoring fields are not allowed in observe output")
            _assert_no_ai_scores(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _assert_no_ai_scores(item, f"{path}[{index}]")


def parse_image_observation_response(response: object) -> ImageObservation:
    """Parse the model's observe-only JSON and normalize only unambiguous variants."""
    if isinstance(response, str):
        try:
            payload = extract_json(response)
        except ValueError as error:
            raise ObservationSchemaError(f"field $: invalid JSON response ({type(error).__name__})") from None
    else:
        payload = response
    if not isinstance(payload, dict):
        raise ObservationSchemaError("field $: expected a JSON object")
    _assert_no_ai_scores(payload)
    _reject_unknown_fields(payload, {"dna_matches", "forbidden", "allowed_imperfections", "notes"}, "$")
    if "dna_matches" not in payload:
        raise ObservationSchemaError("field $.dna_matches: required field is missing")
    normalized = dict(payload)
    normalized.setdefault("forbidden", [])
    normalized.setdefault("allowed_imperfections", [])
    normalized.setdefault("notes", [])
    for key in ("dna_matches", "forbidden", "allowed_imperfections", "notes"):
        if not isinstance(normalized[key], list):
            raise ObservationSchemaError(f"field $.{key}: expected an array")

    normalized["dna_matches"] = [
        _normalize_dna_match(item, index) for index, item in enumerate(normalized["dna_matches"])
    ]
    normalized["forbidden"] = [
        _normalize_forbidden(item, index) for index, item in enumerate(normalized["forbidden"])
    ]
    normalized["allowed_imperfections"] = [
        _normalize_allowed_imperfection(item, index)
        for index, item in enumerate(normalized["allowed_imperfections"])
    ]
    for index, note in enumerate(normalized["notes"]):
        if not isinstance(note, str):
            raise ObservationSchemaError(f"field $.notes[{index}]: expected a string")
    try:
        return ImageObservation.model_validate(normalized)
    except ValidationError as error:
        details = []
        for item in error.errors(include_input=False)[:8]:
            path = _field_path(item.get("loc", ()))
            details.append(f"{path}: {item.get('msg', 'invalid value')}")
        raise ObservationSchemaError("image observation schema invalid; " + "; ".join(details)) from None


def _normalize_dna_match(item: object, index: int) -> dict[str, Any]:
    path = f"$.dna_matches[{index}]"
    row = _mapping(item, path)
    _reject_unknown_fields(
        row,
        {"key", "expected", "observed", "category", "match_state", "confidence", "reason", "evidence"},
        path,
    )
    for required in ("key", "match_state"):
        if required not in row:
            raise ObservationSchemaError(f"field {path}.{required}: required field is missing")
    result = dict(row)
    result["match_state"] = _normalize_enum(result["match_state"], MatchState, f"{path}.match_state")
    if "confidence" in result:
        result["confidence"] = _normalize_confidence(result["confidence"], f"{path}.confidence")
    return result


def _normalize_forbidden(item: object, index: int) -> dict[str, Any]:
    path = f"$.forbidden[{index}]"
    row = _mapping(item, path)
    _reject_unknown_fields(row, {"rule", "source", "severity", "violated", "confidence", "reason"}, path)
    if "rule" not in row:
        raise ObservationSchemaError(f"field {path}.rule: required field is missing")
    result = dict(row)
    if "severity" in result:
        result["severity"] = _normalize_enum(result["severity"], Severity, f"{path}.severity")
    if "violated" in result:
        result["violated"] = _normalize_bool(result["violated"], f"{path}.violated")
    if "confidence" in result:
        result["confidence"] = _normalize_confidence(result["confidence"], f"{path}.confidence")
    return result


def _normalize_allowed_imperfection(item: object, index: int) -> dict[str, Any]:
    path = f"$.allowed_imperfections[{index}]"
    row = _mapping(item, path)
    _reject_unknown_fields(row, {"item", "present", "reason"}, path)
    if "item" not in row:
        raise ObservationSchemaError(f"field {path}.item: required field is missing")
    result = dict(row)
    if "present" in result:
        result["present"] = _normalize_bool(result["present"], f"{path}.present")
    return result


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationSchemaError(f"field {path}: expected an object")
    return value


def _reject_unknown_fields(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ObservationSchemaError(f"field {path}.{unknown[0]}: unknown field")


def _normalize_enum(value: object, enum_type: type[MatchState] | type[Severity], path: str) -> str:
    if not isinstance(value, str):
        raise ObservationSchemaError(f"field {path}: expected one of {', '.join(item.value for item in enum_type)}")
    normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
    allowed = {item.value for item in enum_type}
    if normalized not in allowed:
        raise ObservationSchemaError(f"field {path}: unsupported value; expected one of {', '.join(sorted(allowed))}")
    return normalized


def _normalize_confidence(value: object, path: str) -> float:
    if isinstance(value, bool):
        raise ObservationSchemaError(f"field {path}: expected a number from 0 to 1")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ObservationSchemaError(f"field {path}: expected a number from 0 to 1") from None
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ObservationSchemaError(f"field {path}: number must be finite and between 0 and 1")
    return number


def _normalize_bool(value: object, path: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().casefold() in {"true", "false"}:
        return value.strip().casefold() == "true"
    raise ObservationSchemaError(f"field {path}: expected boolean true or false")


def _field_path(location: object) -> str:
    parts = [str(item) for item in location] if isinstance(location, (list, tuple)) else []
    path = "$"
    for part in parts:
        path += f"[{part}]" if part.isdigit() else f".{part}"
    return path


def _forbidden_rules_for_validation(dna: dict) -> list[dict]:
    """Curated rules only, whenever the subject has any.

    "FORBIDDEN = policy (curated)" is the documented contract, but every rule in the DNA
    was being sent to the validator — including machine-observed ones that merely record
    what one photo happened to lack. For `outside` those included "No visible lake or
    cityscape" and "No visible railing": the lake and the railing are the subject. A
    violation there scores severity=high, which trips the kill-switch and forces a
    regenerate, so junk policy costs a full extra image. Subjects with no curated rules
    (no overlay) keep the observed list rather than validating against nothing.
    """
    rules = dna.get("forbidden", [])
    curated = [item for item in rules if item.get("source", "curated") == "curated"]
    return curated or rules


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
            for item in _forbidden_rules_for_validation(dna)
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
        for index, item in enumerate(_forbidden_rules_for_validation(dna))
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
    raw_response_sink: Optional[Callable[[dict[str, Any]], None]] = None,
    transport_event_sink: Optional[Callable[[dict[str, Any]], None]] = None,
) -> ImageObservation:
    samples = max(samples, 1)
    if provider == "mock":
        return _merge_samples([_mock_observe_once(image_path, dna) for _ in range(samples)])

    system_prompt = _build_image_observe_prompt(dna)
    client = VisionClient(image_provider=provider, temperature=0.0)
    client.transport_event_sink = transport_event_sink
    observed = []
    for sample_index in range(samples):
        try:
            if raw_response_sink is not None:
                client.raw_response_sink = lambda raw, index=sample_index + 1: raw_response_sink({
                    "validator": "image", "sampleIndex": index, "rawResponse": raw,
                    "parseStatus": "raw_captured",
                })
            try:
                response = client.analyze_image(
                    image_path, system_prompt,
                    response_schema=ImageObservation.model_json_schema(),
                    sample_index=sample_index + 1,
                )
            except TypeError as exc:
                # Preserve compatibility with injected legacy test doubles;
                # the production VisionClient supports the structured contract.
                if "unexpected keyword" not in str(exc):
                    raise
                response = client.analyze_image(image_path, system_prompt)
            raw = getattr(client, "last_raw_response", None)
            if raw_response_sink is not None:
                raw_response_sink({"validator": "image", "sampleIndex": sample_index + 1,
                                   "rawResponse": raw, "parseStatus": "before_contract"})
            observation = parse_image_observation_response(response)
            if raw_response_sink is not None:
                raw_response_sink({"validator": "image", "sampleIndex": sample_index + 1,
                                   "rawResponse": raw, "parseStatus": "parsed",
                                   "parsedEvidence": observation.model_dump(mode="json")})
            observed.append(observation)
        except Exception as exc:
            if raw_response_sink is not None:
                raw_response_sink({"validator": "image", "sampleIndex": sample_index + 1,
                                   "rawResponse": getattr(client, "last_raw_response", None),
                                   "parseStatus": "failed", "parseError": str(exc)})
            raise
    return _merge_samples(observed)
