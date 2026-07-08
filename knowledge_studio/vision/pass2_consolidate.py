from __future__ import annotations

"""Pass 2: Deterministic Consolidation (2A) + Canonical Wording (2B).

2A is pure code — no AI calls. It computes coverage and consistency for each
fixed key and classifies them as INVARIANT / VARIABLE / WEAK FEATURE.

2B is a single LLM call at temperature=0, only for wording canonicalization.
It cannot change classification or add/remove keys.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from shared.logging import log
from shared.vision.client import VisionClient
from knowledge_studio.vision.schemas.base import (
    BaseObservation,
    BaseDNA,
    InvariantFeature,
    VariableFeature,
    WeakFeature,
    AllowedImperfection,
    ForbiddenRule,
    EvidenceSummary,
    CONTRACT_VERSION,
)
from knowledge_studio.vision.subject_resolver import SubjectDef


# ---------------------------------------------------------------------------
# Pass 2A — Deterministic Consolidation
# ---------------------------------------------------------------------------

def _normalize_value(value: str) -> str:
    return value.strip().lower()


def _pass2a(
    observations: list[BaseObservation],
    aggregation_keys: list[dict],
    forbidden_defaults: list[str],
    thresholds: dict,
) -> dict:
    """Pure deterministic consolidation using coverage + consistency per §4.

    Returns a dict with:
      invariant_raw:   {key: {"mode_value": str, "evidence_count": int, "coverage": float, "consistency": float}}
      variable_raw:    {key: {"value_set": set[str]}}
      weak_raw:        {key: {"evidence_count": int}}
      forbidden:       list[str]
      future_capture:  list[str]
      total_images:    int
    """
    C_THRESH = thresholds.get("consolidation_threshold", 0.6)
    K_THRESH = thresholds.get("consistency_threshold", 0.7)
    W_THRESH = thresholds.get("weak_threshold", 0.3)

    total = len(observations)
    declared_keys = {k["key"] for k in aggregation_keys}
    key_types = {k["key"]: k.get("type", "free") for k in aggregation_keys}

    # Build per-key value lists (excluding "not_visible")
    key_values: dict[str, list[str]] = defaultdict(list)
    for obs in observations:
        seen_keys_this_obs: set[str] = set()
        for feat in obs.features:
            if feat.key not in declared_keys:
                continue
            if feat.key in seen_keys_this_obs:
                continue
            seen_keys_this_obs.add(feat.key)
            if feat.value and feat.value != "not_visible" and feat.confidence > 0:
                key_values[feat.key].append(feat.value)

    invariant_raw: dict[str, dict] = {}
    variable_raw: dict[str, dict] = {}
    weak_raw: dict[str, dict] = {}

    for key in declared_keys:
        values = key_values.get(key, [])
        evidence_count = len(values)
        coverage = evidence_count / total if total > 0 else 0.0

        if coverage < W_THRESH:
            if evidence_count > 0:
                weak_raw[key] = {"evidence_count": evidence_count}
            continue

        # Normalize for consistency measurement
        normalized = [_normalize_value(v) for v in values]
        counter = Counter(normalized)
        mode_normalized, mode_count = counter.most_common(1)[0]
        consistency = mode_count / evidence_count if evidence_count > 0 else 0.0

        if coverage >= C_THRESH and consistency >= K_THRESH:
            # Find the most common raw value (before normalization)
            mode_raw = max(
                (v for v in values if _normalize_value(v) == mode_normalized),
                key=lambda v: Counter(values)[v],
                default=mode_normalized,
            )
            invariant_raw[key] = {
                "mode_value": mode_raw,
                "evidence_count": evidence_count,
                "coverage": round(coverage, 4),
                "consistency": round(consistency, 4),
            }
        else:
            # VARIABLE: unique normalized values as value_range
            unique_normalized = sorted(set(normalized))
            variable_raw[key] = {"value_set": unique_normalized}

    # FORBIDDEN observed: union of all forbidden_hints from observations + defaults
    all_forbidden: list[str] = list(forbidden_defaults)
    for obs in observations:
        for hint in obs.forbidden_hints:
            if hint not in all_forbidden:
                all_forbidden.append(hint)

    # ALLOWED IMPERFECTIONS observed: collect all non-null values of key 'allowed_imperfection'
    ai_seen: list[str] = []
    if "allowed_imperfection" in declared_keys:
        for v in key_values.get("allowed_imperfection", []):
            if v and v != "not_visible" and v not in ai_seen:
                ai_seen.append(v)
        # Remove 'allowed_imperfection' from classification (handled separately)
        for mapping in (invariant_raw, variable_raw, weak_raw):
            mapping.pop("allowed_imperfection", None)

    # FUTURE CAPTURE from WEAK FEATURES
    future_capture = [
        f"Need more images showing '{k}' to confirm invariant status"
        for k in weak_raw
    ]

    return {
        "invariant_raw": invariant_raw,
        "variable_raw": variable_raw,
        "weak_raw": weak_raw,
        "forbidden": all_forbidden,
        "allowed_imperfections_observed": ai_seen,
        "future_capture": future_capture,
        "total_images": total,
    }


# ---------------------------------------------------------------------------
# Pass 2B — Canonical Wording (single LLM call)
# ---------------------------------------------------------------------------

def _pass2b(
    invariant_raw: dict[str, dict],
    client: VisionClient,
    consolidate_prompt_path: Path,
) -> dict[str, str]:
    """Single LLM call to canonicalize invariant value strings.

    Returns {key: canonical_value}. Falls back to raw value if LLM fails or
    returns invalid output.
    """
    if not invariant_raw:
        return {}

    prompt = consolidate_prompt_path.read_text(encoding="utf-8")
    input_payload = [
        {"key": k, "values": [v["mode_value"]]}
        for k, v in invariant_raw.items()
    ]

    user_content = json.dumps(input_payload, ensure_ascii=False, indent=2)
    try:
        raw = client.synthesize(prompt, user_content)
    except Exception as exc:
        log(f"  [WARN] Pass 2B LLM call failed: {exc}. Using raw values.")
        return {k: v["mode_value"] for k, v in invariant_raw.items()}

    # Parse result — expects list of {key, canonical}
    canonical_map: dict[str, str] = {}

    if isinstance(raw, list):
        result_list = raw
    elif isinstance(raw, dict):
        result_list = raw.get("canonical_values", raw.get("result", []))
        if not isinstance(result_list, list):
            result_list = []
    else:
        result_list = []

    for item in result_list:
        if isinstance(item, dict) and "key" in item and "canonical" in item:
            key = item["key"]
            canonical = item["canonical"]
            # Validate: key must exist in invariant_raw, canonical must be a string
            if key in invariant_raw and isinstance(canonical, str) and canonical.strip():
                canonical_map[key] = canonical.strip()

    # Fall back to raw value for any key not returned by LLM
    for key, data in invariant_raw.items():
        if key not in canonical_map:
            log(f"  [WARN] Pass 2B missing canonical for '{key}', using raw value")
            canonical_map[key] = data["mode_value"]

    return canonical_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def consolidate(
    observations: list[BaseObservation],
    client: VisionClient,
    schema_version: str,
    prompt_version: str,
    dna_version: str,
    subject_def: SubjectDef,
    project: str = "",
    thresholds: dict | None = None,
) -> BaseDNA:
    """Pass 2: Consolidate observations into DNA.

    2A is deterministic code. 2B is a single LLM call for wording only.
    """
    if thresholds is None:
        thresholds = {
            "consolidation_threshold": 0.6,
            "consistency_threshold": 0.7,
            "weak_threshold": 0.3,
        }

    log(f"Pass 2A — deterministic consolidation ({len(observations)} observations)…")

    # --- Pass 2A ---
    p2a = _pass2a(
        observations=observations,
        aggregation_keys=subject_def.aggregation_keys,
        forbidden_defaults=subject_def.forbidden_defaults,
        thresholds=thresholds,
    )

    log(f"  2A: {len(p2a['invariant_raw'])} invariant, {len(p2a['variable_raw'])} variable, {len(p2a['weak_raw'])} weak")

    # --- Pass 2B (wording only, one call) ---
    log("Pass 2B — canonical wording (1 LLM call)…")
    canonical_map = _pass2b(
        invariant_raw=p2a["invariant_raw"],
        client=client,
        consolidate_prompt_path=subject_def.consolidate_prompt,
    )

    # --- Assemble DNA ---
    invariant = [
        InvariantFeature(
            key=key,
            value=canonical_map.get(key, data["mode_value"]),
            evidence_count=data["evidence_count"],
            coverage=data["coverage"],
            consistency=data["consistency"],
        )
        for key, data in p2a["invariant_raw"].items()
    ]

    variable = [
        VariableFeature(key=key, value_range=data["value_set"])
        for key, data in p2a["variable_raw"].items()
    ]

    weak_features = [
        WeakFeature(key=key, evidence_count=data["evidence_count"])
        for key, data in p2a["weak_raw"].items()
    ]

    # FORBIDDEN: observed hints wrapped as ForbiddenRule (source = "observed")
    # Curated forbidden is added later by overlay_merge at render time
    forbidden = [
        ForbiddenRule(rule=r, source="observed")
        for r in p2a["forbidden"]
    ]

    # ALLOWED IMPERFECTIONS: observed values from key 'allowed_imperfection'
    allowed_imperfections = [
        AllowedImperfection(value=v, source="observed")
        for v in p2a["allowed_imperfections_observed"]
    ]

    source_hashes = [obs.image_hash for obs in observations]

    return subject_def.dna_cls(
        project=project,
        subject=subject_def.name,
        dna_version=dna_version,
        schema_id=subject_def.schema_id,
        schema_version=schema_version,
        prompt_version=prompt_version,
        provider=client.synthesis_provider_name,
        model=client.synthesis_model,
        generated_at=datetime.now().isoformat(),
        source_images=source_hashes,
        invariant=invariant,
        variable=variable,
        allowed_imperfections=allowed_imperfections,
        forbidden=forbidden,
        evidence=EvidenceSummary(
            total_images=p2a["total_images"],
            weak_features=weak_features,
        ),
        future_capture_notes=p2a["future_capture"],
    )
