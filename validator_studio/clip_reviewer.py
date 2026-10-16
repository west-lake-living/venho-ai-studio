"""AI review of a generated motion clip from timestamped contact sheets (clip-review-v1).

Adapted from FlowKit's video reviewer for a realistic Linh An lakeside clip: six weighted
dimensions, errors by severity with time ranges, and the usable segments free of CRITICAL and
HIGH errors (so a clip broken after second 5 can still be cut instead of regenerated). Any
CRITICAL error fails the clip. The vision call goes through the guarded Gemini provider.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "clip-review-v1"
WEIGHTS = {
    "identity_consistency": 0.25,
    "prompt_adherence": 0.20,
    "motion_quality": 0.20,
    "location_fidelity": 0.15,
    "visual_fidelity": 0.10,
    "temporal_coherence": 0.10,
}
SEVERITIES = ("CRITICAL", "HIGH", "MINOR")

SYSTEM_PROMPT = """You review one AI-generated vertical video clip of a real-looking woman (Linh An)
at West Lake (Ho Tay), Hanoi. You see contact sheets: frames in time order, each labelled t=Ns.
Judge only what is visible. Score each dimension 0.0-10.0.

DIMENSIONS
- identity_consistency: same woman, same face, hair, outfit and earrings in every frame
- prompt_adherence: she does the requested action; nothing unrequested happens
- motion_quality: smooth, natural motion; no jitter, reverse motion, teleporting
- location_fidelity: Hanoi's Ho Tay (white curved-blade railing, flat lake, low skyline);
  never pagodas, mountains or Chinese classical architecture
- visual_fidelity: sharp, no artifacts, no text, logos or watermarks
- temporal_coherence: lighting, background and scale stay consistent

ERRORS (give severity, time_range "Xs-Ys", category, description)
CRITICAL: identity_drift (face becomes another person), person_count (extra or missing person
in the foreground), outfit_change, location_swap (pagodas, mountains, non-Hanoi scenery),
text_or_logo, body_distortion (extra limbs, melted face).
HIGH: camera_drift (unrequested zoom/rotation/angle jump), reverse_motion, object_morph
(railing or props change shape), scale_break, hand_distortion.
MINOR: background_flicker, prop_change, texture_shift.
If any CRITICAL error exists, identity_consistency or location_fidelity (whichever it hurts)
must be 3.0 or lower.

USABLE SEGMENTS: continuous time ranges free of CRITICAL and HIGH errors, as start_sec/end_sec.
Return JSON only."""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimensions": {
            "type": "object",
            "properties": {name: {"type": "number"} for name in WEIGHTS},
            "required": list(WEIGHTS),
        },
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "category": {"type": "string"},
                    "time_range": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["severity", "category", "time_range", "description"],
            },
        },
        "usable_segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"start_sec": {"type": "number"}, "end_sec": {"type": "number"}},
                "required": ["start_sec", "end_sec"],
            },
        },
    },
    "required": ["dimensions", "errors", "usable_segments"],
}

Analyzer = Callable[[Sequence[Path], str, str, dict[str, Any]], dict[str, Any]]


def _gemini_analyzer(
    sheets: Sequence[Path], system_prompt: str, text: str, schema: dict[str, Any]
) -> dict[str, Any]:
    from shared.vision.providers.gemini_vision import GeminiVisionProvider

    return GeminiVisionProvider().analyze_many(
        list(sheets), system_prompt, text, response_schema=schema, sample_index=1
    )


def _clamp(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, number))


def review_clip(
    sheets: Sequence[Path],
    brief: Mapping[str, Any],
    *,
    analyzer: Analyzer = _gemini_analyzer,
) -> dict[str, Any]:
    if not sheets:
        raise ValueError("at least one contact sheet is required")
    duration = float(brief["duration_sec"])
    text = (
        f"Requested shot: {brief.get('prompt', '')}\n"
        f"Expected people in the foreground: {brief.get('expected_people', 1)}\n"
        f"Clip duration: {duration:.1f}s. Frames are labelled with their time."
    )
    raw = analyzer(sheets, SYSTEM_PROMPT, text, RESPONSE_SCHEMA)
    dimensions = {name: _clamp((raw.get("dimensions") or {}).get(name)) for name in WEIGHTS}
    errors = [
        {
            "severity": str(item.get("severity", "")).upper(),
            "category": str(item.get("category", "")),
            "time_range": str(item.get("time_range", "")),
            "description": str(item.get("description", "")),
        }
        for item in raw.get("errors") or []
        if isinstance(item, Mapping) and str(item.get("severity", "")).upper() in SEVERITIES
    ]
    segments = []
    for item in raw.get("usable_segments") or []:
        if not isinstance(item, Mapping):
            continue
        start = max(0.0, min(duration, float(item.get("start_sec", 0.0))))
        end = max(0.0, min(duration, float(item.get("end_sec", 0.0))))
        if end - start > 0.0:
            segments.append({"start_sec": round(start, 3), "end_sec": round(end, 3)})
    segments.sort(key=lambda segment: segment["start_sec"])
    critical = any(error["severity"] == "CRITICAL" for error in errors)
    overall = round(sum(dimensions[name] * weight for name, weight in WEIGHTS.items()), 2)
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sheets": [
            {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in sheets
        ],
        "dimensions": dimensions,
        "overall_score": overall,
        "errors": errors,
        "usable_segments": segments,
        "verdict": "FAIL" if critical else "PASS",
    }


def write_clip_review(report: Mapping[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(report["sheets"], sort_keys=True).encode()).hexdigest()
    path = output_dir / f"clip_review_{digest[:16]}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
