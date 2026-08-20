"""Rehydrate the existing QC4E candidates with production Face Validator evidence.

No ComfyUI call is made here.  The only configuration bridge is the existing
production dotenv source; the credential is never printed or persisted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from validator_studio.face_validator import validate_face

ROOT = Path(__file__).resolve().parents[1]
SOCIAL_AGENT = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent")
AI_STUDIO = ROOT
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
SEARCH = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"
OUT = SEARCH / "qc4e1"
REPORT = SEARCH / "qc4e-report.json"
EXPECTED_A2 = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def presence(name: str) -> dict[str, Any]:
    value = os.environ.get(name)
    return {"status": "PRESENT" if value else "ABSENT", "length_gt_zero": bool(value and len(value) > 0)}


def sanitized_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    for secret in (os.environ.get("GEMINI_API_KEY"), os.environ.get("GOOGLE_API_KEY")):
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def main() -> None:
    before = {name: presence(name) for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
    if not before["GEMINI_API_KEY"]["length_gt_zero"] and not before["GOOGLE_API_KEY"]["length_gt_zero"]:
        # Same precedence as the production resolver: social-agent .env.local,
        # then social-agent .env, then the current project's dotenv files.
        paths = [
            SOCIAL_AGENT / ".env.local", SOCIAL_AGENT / ".env",
            AI_STUDIO / ".env.local", AI_STUDIO / ".env",
        ]
        loaded = None
        for path in paths:
            if path.exists():
                load_dotenv(path, override=False)
                if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                    loaded = str(path)
                    break
    after = {name: presence(name) for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
    if not after["GEMINI_API_KEY"]["length_gt_zero"] and not after["GOOGLE_API_KEY"]["length_gt_zero"]:
        raise RuntimeError("KEY_NOT_CONFIGURED: no supported Gemini credential visible")
    if sha256(A2) != EXPECTED_A2:
        raise RuntimeError("A2 authority mismatch")
    source_report = json.loads(REPORT.read_text(encoding="utf-8"))
    candidates = source_report["candidates"]
    OUT.mkdir(parents=True, exist_ok=True)
    prior = json.loads((OUT / "qc4e1-report.json").read_text(encoding="utf-8")) if (OUT / "qc4e1-report.json").exists() else None

    smoke = {"status": "BLOCKED", "provider": "gemini", "samples": 1, "model": None, "error": None}
    first_path = Path(candidates[0]["artifacts"]["composite"])
    try:
        prior_smoke = prior.get("validator", {}).get("smoke_test", {}) if prior else {}
        if prior_smoke.get("status") == "PASS" and prior_smoke.get("candidate_sha256") == sha256(first_path):
            smoke_report = None
            smoke.update(prior_smoke)
        else:
            smoke_report = validate_face("venho_hotel", "linh_an", first_path, provider="gemini", reference_image_paths=[A2], samples=1)
            smoke.update({"status": "PASS", "model": smoke_report.observer.model, "score": smoke_report.dna_match_score,
                          "eyes_brows": smoke_report.category_scores.get("eyes_and_brows"), "candidate_sha256": sha256(first_path)})
    except Exception as exc:
        smoke["error"] = sanitized_error(exc)
        (OUT / "qc4e1-report.json").write_text(json.dumps({"task": "GW-P0-T2-QC4E1", "credential": {"before": before, "after": after, "source": "existing production dotenv search", "secret_exposed": False}, "smoke_test": smoke}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError(smoke["error"])

    scored: list[dict[str, Any]] = []
    for item in candidates:
        composite = Path(item["artifacts"]["composite"])
        composite_sha = sha256(composite)
        if composite_sha != item["composite_sha256"]:
            raise RuntimeError(f"candidate artifact hash mismatch: {item['candidate_id']}")
        prior_item = next((x for x in (prior or {}).get("candidates", []) if x.get("composite_sha256") == composite_sha), None)
        if prior_item is not None and prior_item.get("face_validator", {}).get("raw_report") is not None:
            identity = prior_item["identity_score"]
            eyes = prior_item["eyes_brows_score"]
            face_data = prior_item["face_validator"]
            error = prior_item.get("error")
        else:
            try:
                face = smoke_report if composite == first_path and smoke_report is not None else validate_face("venho_hotel", "linh_an", composite, provider="gemini", reference_image_paths=[A2], samples=1)
                identity = face.dna_match_score
                eyes = face.category_scores.get("eyes_and_brows")
                face_data = {"provider": face.observer.provider, "model": face.observer.model, "samples": face.observer.samples,
                             "reference_sha256": sha256(A2), "raw_report": face.model_dump(mode="json")}
                error = None
            except Exception as exc:
                identity = eyes = None
                face_data = {"provider": "gemini", "model": None, "samples": 1, "reference_sha256": sha256(A2), "raw_report": None}
                error = sanitized_error(exc)
        identity_status = "PASS" if identity is not None and identity >= 90 else ("FAIL" if identity is not None else "UNKNOWN")
        eyes_status = "PASS" if eyes is not None and eyes >= 90 else ("FAIL" if eyes is not None else "UNKNOWN")
        hard_gates = (item["byte_difference_status"] == "PASS" and item["pixel_lock_status"] == "PASS" and
                      item["metrics"]["locked_region_changed_pixels"] == 0 and item["detector_count"] == 1 and
                      item["geometry_score"] >= 92)
        eligible = hard_gates and identity_status == "PASS" and eyes_status == "PASS"
        scored.append({"candidate_id": item["candidate_id"], "composite_sha256": composite_sha,
                       "restored_sha256": item["restored_sha256"], "parameter_set": item["parameter_set"],
                       "identity_score": identity, "identity_status": identity_status,
                       "eyes_brows_score": eyes, "eyes_brows_status": eyes_status,
                       "geometry_score": item["geometry_score"], "geometry_status": item["geometry_status"],
                       "pixel_lock_status": item["pixel_lock_status"], "byte_difference_status": item["byte_difference_status"],
                       "detector_count": item["detector_count"], "eligibility": "ELIGIBLE" if eligible else "REJECTED",
                       "face_validator": face_data, "error": error,
                       "source_candidate_record": str(SEARCH / item["candidate_id"] / "candidate.json")})

    eligible = [item for item in scored if item["eligibility"] == "ELIGIBLE"]
    eligible.sort(key=lambda item: (-item["identity_score"], -item["eyes_brows_score"], item["candidate_id"]))
    report = {"task": "GW-P0-T2-QC4E1", "credential": {"gemini_api_key_visible_before": before["GEMINI_API_KEY"], "google_api_key_visible_before": before["GOOGLE_API_KEY"], "gemini_api_key_visible_after": after["GEMINI_API_KEY"], "google_api_key_visible_after": after["GOOGLE_API_KEY"], "expected_env_name": "GEMINI_API_KEY", "root_cause": "ENV_NOT_INHERITED + SCRIPT_RUNTIME_CONFIG_BYPASS", "source": "existing production dotenv search; selected source redacted", "secret_exposed": False}, "validator": {"provider": "gemini", "model": smoke["model"], "samples": 1, "smoke_test": smoke}, "candidates": scored, "best_candidate": eligible[0] if eligible else None, "thresholds": {"identity": 90, "eyes_brows": 90, "geometry": 92}, "comfyui_rerun": False, "thresholds_unchanged": True, "validator_semantics_unchanged": True, "canonical_historical_artifacts_unchanged": source_report["canonical_historical_artifacts_unchanged"], "secret_persisted": False}
    (OUT / "qc4e1-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task": report["task"], "credential": report["credential"], "validator": report["validator"], "candidate_count": len(scored), "best_candidate": report["best_candidate"], "report": str(OUT / "qc4e1-report.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
