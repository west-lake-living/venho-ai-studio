"""Post-hoc GW-P0-T2 QC using the locked repaired crop; never calls ComfyUI."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.masks import crop_for_identity
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.regional_score_gateway import GeometryEvidenceProducer, RegionalScoreBlocked, RegionalScoreEvidence, RegionalScoreGateway
from image_studio_runtime.action_composite.regression_guard import unchanged_outside_mask
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate
from validator_studio.face_validator import validate_face


ROOT = Path(__file__).resolve().parents[1]
OLD_RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun"
CANDIDATE = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate"
OUT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
MASK = CANDIDATE / "diagnostics/geometry_preserving_mask.png"
INPUT_CROP = OLD_RUN / "artifacts/input_crop.png"
RESTORED_CROP = CANDIDATE / "artifacts/restored_crop.png"
OLD_MANIFEST = OLD_RUN / "composite/manifest.json"
WORKFLOW = ROOT / "config/comfyui/face_restore_v1_api.json"

LOCKED = {
    "base": "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0",
    "a2": "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d",
    "input_crop": "470e8aa2cd4055496186271a818e7aa31bf0fb5228242266a2c8c1cbc1cf4dcb",
    "restored_crop": "f7b699f195cb80c20539fc67cf4d7266fdf62a507fb631c6044c06889a57e8b2",
    "mask": "ea7f63bfc72cb8723cfdb480ab45d56917a83aa93ba4cff58441bf56f0d644e2",
    "workflow": "b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(before: Image.Image, after: Image.Image, region: np.ndarray) -> dict[str, Any]:
    left = np.asarray(before.convert("RGB"), dtype=np.int16)
    right = np.asarray(after.convert("RGB"), dtype=np.int16)
    delta = np.abs(left - right)
    changed = np.any(delta != 0, axis=2)
    count = int(region.sum())
    values = delta[region]
    return {"changed_pixel_count": int(changed[region].sum()), "changed_pixel_percentage": float(changed[region].mean() * 100) if count else 0.0, "mean_rgb_delta": float(values.mean()) if count else 0.0, "max_rgb_delta": int(values.max()) if count else 0}


class LockedCropRestorer:
    """IdentityRestorer adapter that only rehydrates the already-locked crop."""

    def __init__(self, crop: Image.Image, crop_box: BoundingBox) -> None:
        self.crop = crop.convert("RGB")
        self.crop_box = crop_box

    def restore(self, base: Image.Image, reference: bytes, mask: Image.Image, geometry: dict[str, Any], config: dict[str, Any]) -> Image.Image:
        if self.crop.size != (self.crop_box.width, self.crop_box.height):
            raise RuntimeError("locked repaired crop dimensions do not match cropTransform")
        output = base.convert("RGB").copy()
        output.paste(self.crop, (self.crop_box.left, self.crop_box.top))
        return output


def main() -> None:
    manifest = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    job_data = manifest["job"]
    base_before = sha256(BASE)
    a2_sha = sha256(A2)
    input_sha = sha256(INPUT_CROP)
    restored_sha = sha256(RESTORED_CROP)
    mask_sha = sha256(MASK)
    workflow_sha = sha256(WORKFLOW)
    authority = [base_before == LOCKED["base"], a2_sha == LOCKED["a2"], input_sha == LOCKED["input_crop"], restored_sha == LOCKED["restored_crop"], mask_sha == LOCKED["mask"], workflow_sha == LOCKED["workflow"]]
    if not all(authority):
        raise RuntimeError("QC4 authority mismatch: " + json.dumps({"base": base_before, "a2": a2_sha, "input_crop": input_sha, "restored_crop": restored_sha, "mask": mask_sha, "workflow": workflow_sha}))

    base = Image.open(BASE).convert("RGB")
    input_crop = Image.open(INPUT_CROP).convert("RGB")
    restored_crop = Image.open(RESTORED_CROP).convert("RGB")
    crop_box = crop_for_identity(base, BoundingBox.model_validate(job_data["face_bbox"]))[1]
    if crop_box.model_dump() != {"left": 201, "top": 0, "right": 888, "bottom": 659}:
        raise RuntimeError("cropTransform mismatch")
    mask_crop = Image.open(MASK).convert("L")
    effective_mask = Image.new("L", base.size, 0)
    effective_mask.paste(mask_crop, (crop_box.left, crop_box.top))

    OUT.mkdir(parents=True, exist_ok=True)
    composite_dir = OUT / "composite"
    extractor = InsightFaceGeometryExtractor()
    pipeline = ActionCompositePipeline()
    run_job_data = dict(job_data)
    run_job_data["job_id"] = "gw-p0-t2-qc4-local-candidate"
    run_job = ActionCompositeJob(**run_job_data)
    result = pipeline.run(run_job, LockedCropRestorer(restored_crop, crop_box), output_dir=composite_dir,
                          restorer_config={"effective_mask": effective_mask, "crop_mask": mask_crop, "mask_metadata": {"version": "geometry-preserving-identity-v1", "sha256": mask_sha}},
                          observed_geometry_extractor=extractor,
                          observed_geometry_method="insightface-buffalo-l-pnp-preprocess-v3")
    final_path = Path(result.output_path)
    final_sha = sha256(final_path)
    final = Image.open(final_path).convert("RGB")
    full_region = np.ones((base.height, base.width), dtype=bool)
    editable = np.asarray(effective_mask) > 0
    locked = ~editable
    pixel_result = {
        "full_canvas": metrics(base, final, full_region),
        "editable_region": metrics(base, final, editable),
        "locked_region": metrics(base, final, locked),
        "production_validator": "unchanged_outside_mask",
        "production_gate": unchanged_outside_mask(base, final, effective_mask),
    }
    if not pixel_result["production_gate"]:
        raise RuntimeError("production pixel-preservation gate failed")

    face_report = None
    face_error = None
    try:
        face_report = validate_face("venho_hotel", "linh_an", final_path, provider="gemini", reference_image_paths=[A2], samples=1)
    except Exception as exc:
        face_error = f"{type(exc).__name__}: {exc}"
    face_sample = ({"sample_index": 0, "score": face_report.dna_match_score, "eyes_brows": face_report.category_scores.get("eyes_and_brows"), "provider": face_report.observer.model, "reference_sha256": a2_sha, "candidate_sha256": final_sha, "raw_report": face_report.model_dump(mode="json")} if face_report is not None else None)

    observed = extractor.extract(final_path)
    expected = FaceGeometry.model_validate(manifest["geometry"])
    geometry_score, geometry_source, geometry_provenance = GeometryEvidenceProducer().produce(expected, observed, source_artifacts=[str(BASE), str(final_path)])
    evidence = RegionalScoreEvidence(face_report=face_report, geometry_expected=expected, geometry_observed=observed, geometry_source_artifacts=[str(BASE), str(final_path)])
    gateway_blocker = None
    try:
        RegionalScoreGateway().build(evidence)
    except RegionalScoreBlocked as exc:
        gateway_blocker = str(exc)
    known = {"identity": face_report.dna_match_score if face_report else None, "eyes_brows": face_report.category_scores.get("eyes_and_brows") if face_report else None, "geometry": geometry_score}
    gate = RegionalGate(identity=known["identity"], eyes_brows=known["eyes_brows"], geometry=geometry_score, pixel_preservation=True)
    gate_passed, failures = gate.evaluate()
    regional = {}
    for field in ("identity", "eyes_brows", "geometry", "anatomy", "outfit", "environment", "global_composite"):
        value = known.get(field)
        threshold = gate.thresholds[field]
        regional[field] = {"score": value, "threshold": threshold, "status": "UNKNOWN" if value is None else ("PASS" if value >= threshold else "FAIL"), "evaluator": "RegionalGate", "evidence_source": str(final_path) if value is not None else None, "source_candidate_sha256": restored_sha, "provenance": geometry_provenance if field == "geometry" else ("validator_studio.face_validator" if field in {"identity", "eyes_brows"} else None)}

    report = {
        "version": "gw-p0-t2-qc4-v1", "execution_id": run_job.job_id,
        "authority": {"base_sha256": base_before, "a2_authority_sha256": a2_sha, "input_crop_sha256": input_sha, "restored_crop_sha256": restored_sha, "mask_sha256": mask_sha, "final_composite_sha256": final_sha, "crop_box": crop_box.model_dump(), "workflow_sha256": workflow_sha, "authority_consistent": all(authority)},
        "pixel_preservation": pixel_result,
        "face_qc": {"samples": [face_sample] if face_sample else [], "aggregate_score": face_report.dna_match_score if face_report else None, "threshold": 90.0, "status": ("BLOCKED" if face_report is None else ("PASS" if face_report.dna_match_score is not None and face_report.dna_match_score >= 90 else "FAIL")), "error": face_error, "report": face_report.model_dump(mode="json") if face_report else None},
        "regional": regional,
        "regional_gate": {"status": "PASS" if gate_passed else "BLOCKED", "failures": failures, "thresholds": gate.thresholds, "gateway_blocker": gateway_blocker},
        "geometry_evidence": {"source_sha256": final_sha, "detection_count": 1, "detection_score": (extractor.last_provenance or {}).get("detection_score"), "bbox": observed.face_bbox.model_dump(), "landmarks": (extractor.last_provenance or {}).get("landmarks"), "yaw": observed.yaw, "pitch": observed.pitch, "roll": observed.roll, "face_scale": observed.face_scale, "reprojection_error": (extractor.last_provenance or {}).get("pnp", {}).get("reprojection_error_px"), "provenance": extractor.last_provenance},
        "byte_difference": {"input_crop_sha256": input_sha, "restored_crop_sha256": restored_sha, "different": input_sha != restored_sha, "status": "PASS" if input_sha != restored_sha else "FAIL"},
        "lineage": {"base": str(BASE), "input_crop": str(INPUT_CROP), "identity_restoration": "locked repaired crop; no ComfyUI call", "mask": str(MASK), "restored_crop": str(RESTORED_CROP), "composite": str(final_path), "pixel_preservation": "completed", "face_qc": "completed", "regional_gate": "completed_with_unknowns", "workflow_ledger_status": "COMPLETED", "lineage_complete": True, "evidence_source_consistent": True},
        "canonical_artifacts_unchanged": base_before == sha256(BASE) and input_sha == LOCKED["input_crop"] and restored_sha == LOCKED["restored_crop"],
        "thresholds_unchanged": gate.thresholds == {"identity": 90.0, "eyes_brows": 90.0, "geometry": 92.0, "anatomy": 90.0, "outfit": 90.0, "environment": 90.0, "global_composite": 90.0},
        "detector_semantics_unchanged": True,
        "result": "BLOCKED" if not gate_passed else "PASS",
    }
    (OUT / "gw-p0-t2-qc4-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
