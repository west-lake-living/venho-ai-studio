"""GW-P0-T2-QC4E: bounded local identity/eyes restoration search.

The existing ComfyUI workflow is copied in memory and only its existing
identity-related inputs are varied. Every candidate is written to a unique
diagnostic run; locked historical artifacts are read-only.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.config import ComfyUIConfig
from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.masks import crop_for_identity, geometry_preserving_identity_mask
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.providers import ComfyUIIdentityRestorer
from image_studio_runtime.action_composite.regression_guard import unchanged_outside_mask
from image_studio_runtime.action_composite.regional_score_gateway import GeometryEvidenceProducer
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate
from validator_studio.face_validator import validate_face

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
OLD_RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun"
CURRENT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate"
CURRENT_FINAL = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/composite/image.png"
WORKFLOW = ROOT / "config/comfyui/face_restore_v1_api.json"
OUT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search"

LOCKED = {
    "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
    "a2": "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d",
    "workflow": "b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_existing_inputs(workflow: dict[str, Any], *, weight: float, denoise: float) -> dict[str, Any]:
    prepared = copy.deepcopy(workflow)
    pulid = [node for node in prepared.values() if node.get("_meta", {}).get("title") == "apply_pulid"]
    sampler = [node for node in prepared.values() if node.get("_meta", {}).get("title") == "ksampler"]
    if len(pulid) != 1 or len(sampler) != 1:
        raise RuntimeError("QC4E expected exactly one existing ApplyPulid and KSampler node")
    pulid[0]["inputs"]["weight"] = weight
    sampler[0]["inputs"]["denoise"] = denoise
    return prepared


def detect(extractor: InsightFaceGeometryExtractor, path: Path) -> tuple[int, FaceGeometry | None, dict[str, Any]]:
    try:
        geometry = extractor.extract(path)
    except Exception as exc:
        return 0, None, {"error": f"{type(exc).__name__}: {exc}", "provenance": extractor.last_provenance}
    return 1, geometry, {"provenance": extractor.last_provenance}


def candidate_metrics(before: Image.Image, after: Image.Image, mask: Image.Image) -> dict[str, Any]:
    a = np.asarray(before.convert("RGB"))
    b = np.asarray(after.convert("RGB"))
    changed = np.any(a != b, axis=2)
    effective = np.asarray(mask.convert("L")) > 0
    outside = ~effective
    return {
        "total_changed_pixel_pct": float(changed.mean() * 100),
        "outside_mask_changed_pct": float(changed[outside].mean() * 100) if outside.any() else 0.0,
        "locked_region_changed_pixels": int(changed[outside].sum()),
        "inside_mask_changed_pct": float(changed[effective].mean() * 100) if effective.any() else 0.0,
    }


def main() -> None:
    if sha256(BASE) != LOCKED["base"] or sha256(A2) != LOCKED["a2"] or sha256(WORKFLOW) != LOCKED["workflow"]:
        raise RuntimeError("QC4E locked authority mismatch")
    old_manifest = json.loads((OLD_RUN / "composite/manifest.json").read_text(encoding="utf-8"))
    job_data = dict(old_manifest["job"])
    base = Image.open(BASE).convert("RGBA")
    job_bbox = BoundingBox.model_validate(job_data["face_bbox"])
    input_crop, crop_box = crop_for_identity(base, job_bbox)
    extractor = InsightFaceGeometryExtractor(model_name="buffalo_l")
    _, reference_geometry, ref_meta = detect(extractor, BASE)
    if reference_geometry is None:
        raise RuntimeError("locked base does not provide exactly one geometry")
    face_bbox = reference_geometry.face_bbox.model_copy(update={
        "left": reference_geometry.face_bbox.left - crop_box.left,
        "top": reference_geometry.face_bbox.top - crop_box.top,
        "right": reference_geometry.face_bbox.right - crop_box.left,
        "bottom": reference_geometry.face_bbox.bottom - crop_box.top,
    })
    landmarks = [(x - crop_box.left, y - crop_box.top) for x, y in (
        (reference_geometry.eye_line or 0, reference_geometry.eye_line or 0),
    )]
    # The production mask builder needs real InsightFace landmarks. Rehydrate
    # them from its persisted provenance, never from synthetic geometry.
    ref_landmarks = ref_meta["provenance"].get("landmarks") if ref_meta.get("provenance") else None
    if not ref_landmarks or len(ref_landmarks) != 5:
        raise RuntimeError("locked base provenance lacks five real landmarks")
    crop_landmarks = [(float(x) - crop_box.left, float(y) - crop_box.top) for x, y in ref_landmarks]
    mask, mask_meta = geometry_preserving_identity_mask(input_crop.size, face_bbox, crop_landmarks)
    effective_mask = Image.new("L", base.size, 0)
    effective_mask.paste(mask, (crop_box.left, crop_box.top))
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    workflow_config = ComfyUIConfig(endpoint="http://127.0.0.1:8188", workflow_path=str(WORKFLOW), workflow_version="face_restore_v1", timeout_seconds=180.0)
    restorer = ComfyUIIdentityRestorer(endpoint=workflow_config.endpoint, request_timeout=120.0, client_id="gw-p0-t2-qc4e")
    if not restorer.health_check():
        raise RuntimeError("ComfyUI endpoint health check failed")
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = [
        {"candidate_id": "qc4e-baseline-w080-d060", "weight": 0.8, "denoise": 0.6, "changed": {}},
        {"candidate_id": "qc4e-w065-d060", "weight": 0.65, "denoise": 0.6, "changed": {"apply_pulid.weight": 0.65}},
        {"candidate_id": "qc4e-w070-d060", "weight": 0.70, "denoise": 0.6, "changed": {"apply_pulid.weight": 0.70}},
        {"candidate_id": "qc4e-w090-d060", "weight": 0.90, "denoise": 0.6, "changed": {"apply_pulid.weight": 0.90}},
        {"candidate_id": "qc4e-w100-d060", "weight": 1.00, "denoise": 0.6, "changed": {"apply_pulid.weight": 1.00}},
        {"candidate_id": "qc4e-w080-d050", "weight": 0.8, "denoise": 0.5, "changed": {"ksampler.denoise": 0.5}},
        {"candidate_id": "qc4e-w080-d070", "weight": 0.8, "denoise": 0.7, "changed": {"ksampler.denoise": 0.7}},
        {"candidate_id": "qc4e-w080-d080", "weight": 0.8, "denoise": 0.8, "changed": {"ksampler.denoise": 0.8}},
    ]
    results: list[dict[str, Any]] = []
    for spec in candidates:
        cdir = OUT / spec["candidate_id"]
        cdir.mkdir(parents=True, exist_ok=True)
        if spec["candidate_id"] == "qc4e-baseline-w080-d060":
            # The supplied baseline is authoritative and is not regenerated.
            source = CURRENT_FINAL
            final_path = cdir / "composite/image.png"
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_bytes(source.read_bytes())
            restored_source = CURRENT / "artifacts/restored_crop.png"
            restored_path = cdir / "artifacts/restored_crop.png"
            restored_path.parent.mkdir(parents=True, exist_ok=True)
            restored_path.write_bytes(restored_source.read_bytes())
            execution = "existing-qc4c2f-baseline"
        else:
            prepared = set_existing_inputs(workflow, weight=spec["weight"], denoise=spec["denoise"])
            run_data = dict(job_data)
            run_data["job_id"] = spec["candidate_id"]
            result = ActionCompositePipeline().run(
                ActionCompositeJob(**run_data), restorer, output_dir=cdir / "composite",
                restorer_config={"workflow": prepared, "timeout_seconds": 180.0,
                                 "node_bindings": workflow_config.node_bindings,
                                 "effective_mask": effective_mask, "crop_mask": mask,
                                 "mask_metadata": {**mask_meta, "sha256": None}},
            )
            final_path = Path(result.output_path)
            restored_path = cdir / "artifacts/restored_crop.png"
            restored_path.parent.mkdir(parents=True, exist_ok=True)
            Image.open(final_path).convert("RGBA").crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)).save(restored_path)
            execution = spec["candidate_id"]
            spec["effective_workflow_sha256"] = hashlib.sha256(json.dumps(prepared, sort_keys=True).encode()).hexdigest()
        final = Image.open(final_path).convert("RGB")
        restored = Image.open(restored_path).convert("RGB")
        input_rgb = input_crop.convert("RGB")
        byte_diff = not np.array_equal(np.asarray(input_rgb), np.asarray(restored))
        pixel_pass = unchanged_outside_mask(base.convert("RGB"), final, effective_mask)
        count, observed, observed_meta = detect(extractor, final_path)
        geometry_score = None
        geometry_detail: dict[str, Any] = {}
        if observed is not None:
            geometry_score, geometry_detail["source"], geometry_detail["provenance"] = GeometryEvidenceProducer().produce(reference_geometry, observed, source_artifacts=[str(BASE), str(final_path)])
        hard = byte_diff and pixel_pass and count == 1 and geometry_score is not None and geometry_score >= 92
        gate = RegionalGate(geometry=geometry_score, pixel_preservation=pixel_pass)
        gate_pass, gate_failures = gate.evaluate()
        face_report = None
        face_error = None
        if hard:
            try:
                face_report = validate_face("venho_hotel", "linh_an", final_path, provider="gemini", reference_image_paths=[A2], samples=1)
            except Exception as exc:
                face_error = f"{type(exc).__name__}: {exc}"
        identity_score = face_report.dna_match_score if face_report else None
        eyes_brows_score = face_report.category_scores.get("eyes_and_brows") if face_report else None
        identity_pass = identity_score is not None and identity_score >= 90.0
        eyes_pass = eyes_brows_score is not None and eyes_brows_score >= 90.0
        eligible = hard and identity_pass and eyes_pass
        result = {"candidate_id": spec["candidate_id"], "execution": execution, "changed_parameters": spec["changed"],
                  "parameter_set": {"seed": 42, "pulid_weight": spec["weight"], "denoise": spec["denoise"], "steps": 4, "cfg": 1.2, "sampler": "dpmpp_2m", "scheduler": "sgm_uniform"},
                  "mask_sha256": sha256(CURRENT / "diagnostics/geometry_preserving_mask.png") if (CURRENT / "diagnostics/geometry_preserving_mask.png").exists() else None,
                  "mask_coverage": mask_meta["coverage_ratio"], "restored_sha256": sha256(restored_path), "composite_sha256": sha256(final_path),
                  "metrics": candidate_metrics(input_rgb, restored, mask), "detector_count": count,
                  "detector_score": observed_meta.get("provenance", {}).get("detection_score") if observed_meta.get("provenance") else None,
                  "geometry_score": geometry_score, "geometry": geometry_detail, "identity_score": identity_score, "eyes_brows_score": eyes_brows_score,
                  "face_validator": {"provider": "gemini", "reference_sha256": sha256(A2), "samples": 1, "error": face_error, "raw_report": face_report.model_dump(mode="json") if face_report else None},
                  "byte_difference_status": "PASS" if byte_diff else "FAIL", "pixel_lock_status": "PASS" if pixel_pass and not candidate_metrics(input_rgb, restored, mask)["locked_region_changed_pixels"] else "FAIL",
                  "geometry_status": "PASS" if geometry_score is not None and geometry_score >= 92 else "FAIL", "gate_status": "PASS" if (identity_pass and eyes_pass and gate_pass) else "FAIL",
                  "regional_gate_failures": gate_failures, "eligibility": "ELIGIBLE" if eligible else "REJECTED",
                  "rejection_reason": None if eligible else ("hard preservation/detection/geometry gate failed" if not hard else (face_error or "identity/eyes threshold failed")),
                  "artifacts": {"composite": str(final_path), "restored_crop": str(restored_path)}}
        results.append(result)
        (cdir / "candidate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"candidate_id": spec["candidate_id"], "eligibility": result["eligibility"], "geometry": geometry_score, "sha": result["restored_sha256"]}, ensure_ascii=False))
        if eligible:
            break
    report = {"task": "GW-P0-T2-QC4E", "workflow_sha256": LOCKED["workflow"], "base_sha256": LOCKED["base"], "a2_sha256": LOCKED["a2"], "mask": mask_meta, "candidates": results, "stopped_on_pass": any(x["eligibility"] == "ELIGIBLE" for x in results), "canonical_historical_artifacts_unchanged": sha256(OLD_RUN / "artifacts/restored_crop.png") == "8a347eceb1d481234a97905eb1fc3a5c26809f9823614b0f9175b3b32f272f3e"}
    (OUT / "qc4e-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
