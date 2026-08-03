from __future__ import annotations


def validate_derivatives(artifacts: list[dict], *, critical_text_in_image: bool = False, require_ocr_pass: bool = True) -> dict:
    kill_switches: list[str] = []
    bad = [item for item in artifacts if not item.get("path") or item.get("crop_safe") is False]
    if bad:
        kill_switches.append("critical_text_error" if critical_text_in_image else "crop_safety_failed")
    if require_ocr_pass:
        ocr_failed = [item for item in artifacts if item.get("ocr_pass") is False]
        if ocr_failed and "critical_text_error" not in kill_switches:
            kill_switches.append("critical_text_error")
    return {
        "validator": "derivative_validator",
        "status": "completed",
        "verdict": "NEEDS_REVISION" if kill_switches else "READY_FOR_REVIEW",
        "invalid_artifacts": bad,
        "kill_switches": kill_switches,
    }
