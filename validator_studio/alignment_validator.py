from __future__ import annotations


def validate_alignment(brief: dict, copy_scene: dict, image_scene: dict | None = None, *, min_score: float = 0.95) -> dict:
    required = set(brief.get("visual", {}).get("required_entities", []))
    forbidden = set(brief.get("visual", {}).get("forbidden_entities", []))
    copy_entities = set(copy_scene.get("entities", []))
    image_entities = set((image_scene or {}).get("entities", []))
    present = copy_entities | image_entities
    missing = sorted(required - present)
    forbidden_found = sorted(forbidden & present)
    kill_switches = []
    if missing:
        kill_switches.append("missing_required_subject")
    if forbidden_found:
        kill_switches.append("location_mismatch")
    total_required = max(len(required), 1)
    alignment_score = (total_required - len(missing)) / total_required
    verdict = "READY_FOR_REVIEW"
    if kill_switches or alignment_score < min_score:
        verdict = "NEEDS_REVISION"
    return {
        "validator": "alignment_validator",
        "status": "completed",
        "verdict": verdict,
        "alignment_score": alignment_score,
        "alignment_min": min_score,
        "missing_required_entities": missing,
        "forbidden_entities_found": forbidden_found,
        "kill_switches": kill_switches,
    }
