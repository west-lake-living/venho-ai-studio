"""Execute the opt-in geometry-preserving local restoration candidate.

This script never writes any source or prior-run artifact.  The effective mask
override is deliberately passed only for this QC candidate; normal production
calls retain the existing hierarchical mask.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops

from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.masks import (
    crop_for_identity,
    geometry_preserving_identity_mask,
    hierarchical_face_masks,
)
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.providers import ComfyUIIdentityRestorer
from image_studio_runtime.action_composite.regression_guard import unchanged_outside_mask
from image_studio_runtime.action_composite.config import ComfyUIConfig


ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
REFERENCE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
OLD_MASK_SOURCE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/face-mask.png")
OLD_RUN = ROOT / "data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun"
INPUT_CROP = OLD_RUN / "artifacts/input_crop.png"
OLD_RESTORED = OLD_RUN / "artifacts/restored_crop.png"
OLD_MANIFEST = OLD_RUN / "composite/manifest.json"
WORKFLOW = ROOT / "config/comfyui/face_restore_v1_api.json"
OUT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate"
DIAG = OUT / "diagnostics"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detector_face_and_landmarks(extractor: InsightFaceGeometryExtractor, path: Path) -> tuple[Any, np.ndarray, dict[str, Any]]:
    analyzer, cv2 = extractor._runtime()
    source = np.asarray(Image.open(path).convert("RGB"))
    analysis, scale = extractor._analysis_image(source, cv2)
    faces = list(analyzer.get(analysis))
    if len(faces) != 1:
        raise RuntimeError(f"authoritative full-base detector requires exactly one face, got {len(faces)}")
    face = faces[0]
    bbox = np.asarray(face.bbox, dtype="float64") / scale
    landmarks = np.asarray(face.kps, dtype="float64") / scale
    if landmarks.shape != (5, 2):
        raise RuntimeError("authoritative detector did not expose five landmarks")
    return bbox, landmarks, {
        "detector": "InsightFace.FaceAnalysis",
        "model": extractor.model_name,
        "det_size": list(extractor.det_size),
        "analysis_dimensions": {"width": int(analysis.shape[1]), "height": int(analysis.shape[0])},
        "scale_factor": scale,
        "detection_count": len(faces),
        "bbox": [float(v) for v in bbox],
        "score": float(getattr(face, "det_score", 0.0)),
        "landmarks": landmarks.tolist(),
    }


def _mask_stats(mask: Image.Image) -> dict[str, Any]:
    array = np.asarray(mask.convert("L"))
    bbox = mask.getbbox()
    return {
        "dimensions": {"width": mask.width, "height": mask.height},
        "bbox": {"left": bbox[0], "top": bbox[1], "right": bbox[2], "bottom": bbox[3]} if bbox else None,
        "nonzero_pixel_count": int((array > 0).sum()),
        "coverage_ratio": float((array > 0).mean()),
        "max_value": int(array.max()),
        "min_value": int(array.min()),
    }


def _change_metrics(before: Image.Image, after: Image.Image, *, regions: dict[str, np.ndarray]) -> dict[str, Any]:
    left = np.asarray(before.convert("RGB"), dtype=np.int16)
    right = np.asarray(after.convert("RGB"), dtype=np.int16)
    delta = np.abs(left - right)
    changed = np.any(delta != 0, axis=2)
    result: dict[str, Any] = {
        "total_changed_pixel_pct": float(changed.mean() * 100),
        "mean_rgb_delta": float(delta.mean()),
    }
    for name, region in regions.items():
        count = int(region.sum())
        result[name] = {
            "pixel_count": count,
            "changed_pixel_pct": float(changed[region].mean() * 100) if count else 0.0,
            "mean_rgb_delta": float(delta[region].mean()) if count else 0.0,
        }
    return result


def _face_regions(size: tuple[int, int], bbox_full: np.ndarray, crop_box: BoundingBox) -> dict[str, np.ndarray]:
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width]
    left = max(0, float(bbox_full[0] - crop_box.left))
    top = max(0, float(bbox_full[1] - crop_box.top))
    right = min(width, float(bbox_full[2] - crop_box.left))
    bottom = min(height, float(bbox_full[3] - crop_box.top))
    face = (xx >= left) & (xx < right) & (yy >= top) & (yy < bottom)
    y = (yy - top) / max(1.0, bottom - top)
    x = (xx - left) / max(1.0, right - left)
    interior = face & (x > 0.10) & (x < 0.90) & (y > 0.10) & (y < 0.90)
    perimeter = face & ~interior
    context = ~face
    upper_boundary = context & (yy < max(0, top + 0.15 * (bottom - top)))
    background = context & ~upper_boundary
    return {"face_interior": interior, "face_perimeter": perimeter,
            "surrounding_context": context, "top_head_boundary": upper_boundary,
            "background": background}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DIAG.mkdir(parents=True, exist_ok=True)
    old_manifest = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    job_data = old_manifest["job"]
    job_bbox = BoundingBox.model_validate(job_data["face_bbox"])
    base = Image.open(BASE).convert("RGBA")
    input_crop, crop_box = crop_for_identity(base, job_bbox)
    if sha256(INPUT_CROP) != "470e8aa2cd4055496186271a818e7aa31bf0fb5228242266a2c8c1cbc1cf4dcb":
        raise RuntimeError("locked input crop artifact hash changed")
    if input_crop.convert("RGB") != Image.open(INPUT_CROP).convert("RGB"):
        raise RuntimeError("manifest-derived input crop does not match locked input crop artifact")

    extractor = InsightFaceGeometryExtractor()
    original_bbox, landmarks, detector_evidence = _detector_face_and_landmarks(extractor, BASE)
    face_bbox = BoundingBox(left=round(float(original_bbox[0] - crop_box.left)),
                            top=round(float(original_bbox[1] - crop_box.top)),
                            right=round(float(original_bbox[2] - crop_box.left)),
                            bottom=round(float(original_bbox[3] - crop_box.top)))
    crop_landmarks = [(float(x - crop_box.left), float(y - crop_box.top)) for x, y in landmarks]

    old_mask_full = hierarchical_face_masks(base.size, job_bbox).shape
    old_mask = old_mask_full.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom))
    old_mask.save(DIAG / "current_restoration_mask.png")
    new_mask, new_mask_meta = geometry_preserving_identity_mask(input_crop.size, face_bbox, crop_landmarks)
    new_mask.save(DIAG / "geometry_preserving_mask.png")
    effective_mask = Image.new("L", base.size, 0)
    effective_mask.paste(new_mask, (crop_box.left, crop_box.top))

    old_resized = Image.open(OLD_RESTORED).convert("RGB").resize(input_crop.size, Image.Resampling.BICUBIC)
    old_regions = _face_regions(input_crop.size, original_bbox, crop_box)
    old_changes = _change_metrics(input_crop, old_resized, regions=old_regions)
    authoritative_face_full = np.zeros((base.height, base.width), dtype=bool)
    authoritative_face_full[round(original_bbox[1]):round(original_bbox[3]), round(original_bbox[0]):round(original_bbox[2])] = True
    old_restored_full = base.copy()
    old_restored_full.paste(old_resized, (crop_box.left, crop_box.top))
    old_outside = np.asarray(ImageChops.difference(base.convert("RGB"), old_restored_full.convert("RGB"))).any(axis=2)
    outside_face_change_ratio = float(old_outside[~authoritative_face_full].mean() * 100)

    workflow_config = ComfyUIConfig(
        endpoint="http://127.0.0.1:8188",
        workflow_path=str(WORKFLOW),
        workflow_version="face_restore_v1",
        timeout_seconds=180.0,
    )
    restorer = ComfyUIIdentityRestorer(endpoint=workflow_config.endpoint, request_timeout=120.0,
                                        client_id="gw-p0-t2-qc4c2f")
    if not restorer.health_check():
        raise RuntimeError("ComfyUI endpoint health check failed")
    run_job_data = dict(job_data)
    run_job_data["job_id"] = "gw-p0-t2-qc4c2f-local-candidate"
    run_job = ActionCompositeJob(**run_job_data)
    output_dir = OUT / "composite"
    result = ActionCompositePipeline().run(
        run_job, restorer, output_dir=output_dir,
        restorer_config={
            "workflow": workflow_config.load_workflow(),
            "timeout_seconds": 180.0,
            "node_bindings": workflow_config.node_bindings,
            "effective_mask": effective_mask,
            "crop_mask": new_mask,
            "mask_metadata": {"old": _mask_stats(old_mask), "new": new_mask_meta,
                              "source": "geometry_preserving_identity_mask"},
        },
    )
    candidate_full_path = Path(result.output_path)
    candidate_crop = Image.open(candidate_full_path).convert("RGBA").crop(
        (crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)
    )
    candidate_crop_path = OUT / "artifacts/restored_crop.png"
    input_artifact_path = OUT / "artifacts/input_crop.png"
    candidate_crop_path.parent.mkdir(parents=True, exist_ok=True)
    Image.open(INPUT_CROP).convert("RGBA").save(input_artifact_path)
    candidate_crop.save(candidate_crop_path)
    candidate_geometry = None
    candidate_geometry_error = None
    try:
        candidate_geometry = extractor.extract(candidate_crop_path)
    except Exception as exc:
        candidate_geometry_error = str(exc)
    full_geometry = None
    full_geometry_error = None
    try:
        full_geometry = extractor.extract(candidate_full_path)
    except Exception as exc:
        full_geometry_error = str(exc)

    candidate_changes = _change_metrics(Image.open(INPUT_CROP), candidate_crop,
                                        regions={"inside_mask": np.asarray(new_mask) > 0,
                                                 "outside_mask": np.asarray(new_mask) == 0,
                                                 **old_regions})
    candidate_full_array = np.asarray(Image.open(candidate_full_path).convert("RGB"))
    base_array = np.asarray(base.convert("RGB"))
    outside_effective = np.asarray(effective_mask) == 0
    effective_change = np.any(candidate_full_array != base_array, axis=2)
    if np.any(effective_change & outside_effective):
        raise RuntimeError("MASK_APPLICATION_FAILURE: candidate changed pixels outside effective mask")
    workflow_sha = sha256(WORKFLOW)
    report = {
        "task": "GW-P0-T2-QC4C2F",
        "execution_id": run_job.job_id,
        "provider": "comfyui-local",
        "implementation": "ComfyUIIdentityRestorer",
        "endpoint": workflow_config.endpoint,
        "workflow": {"path": str(WORKFLOW), "sha256": workflow_sha, "seed": 42,
                      "sampler": "dpmpp_2m", "scheduler": "sgm_uniform", "steps": 4,
                      "cfg": 1.2, "denoise": 0.6, "pulid_weight": 0.8},
        "original_face_bbox": [float(v) for v in original_bbox],
        "original_face_landmarks": landmarks.tolist(),
        "crop_box": crop_box.model_dump(),
        "old_mask": {"source": "hierarchical_face_masks.shape crop", **_mask_stats(old_mask),
                     "feather_method": "PIL.ImageFilter.GaussianBlur", "feather_radius": 6,
                     "face_bbox_relative_to_mask": face_bbox.model_dump(),
                     "mask_coverage_outside_authoritative_face_pct": float((np.asarray(old_mask) > 0)[~old_regions["face_interior"]].mean() * 100)},
        "old_total_changed_pixel_pct": old_changes["total_changed_pixel_pct"],
        "old_outside_face_change_ratio": outside_face_change_ratio,
        "old_change_regions": old_changes,
        "new_mask": {**new_mask_meta, "sha256": sha256(DIAG / "geometry_preserving_mask.png")},
        "candidate": {
            "input_size": list(input_crop.size), "output_size": list(candidate_crop.size),
            "input_sha256": sha256(input_artifact_path), "restored_crop_sha256": sha256(candidate_crop_path),
            "final_composite_sha256": sha256(candidate_full_path),
            "byte_difference_gate": bool(np.any(np.asarray(Image.open(INPUT_CROP).convert("RGB")) != np.asarray(candidate_crop.convert("RGB")))),
            "changes": candidate_changes,
            "direct_detection": {"count": 1 if candidate_geometry else 0,
                                  "geometry": candidate_geometry.model_dump() if candidate_geometry else None,
                                  "error": candidate_geometry_error,
                                  "provenance": extractor.last_provenance},
            "full_frame_detection": {"count": 1 if full_geometry else 0,
                                      "geometry": full_geometry.model_dump() if full_geometry else None,
                                      "error": full_geometry_error},
        },
        "artifacts": {
            "input_crop": str(input_artifact_path), "restored_crop": str(candidate_crop_path),
            "final_composite": str(candidate_full_path),
            "current_restoration_mask": str(DIAG / "current_restoration_mask.png"),
            "geometry_preserving_mask": str(DIAG / "geometry_preserving_mask.png"),
        },
        "canonical_artifacts_unchanged": sha256(OLD_RESTORED) == "8a347eceb1d481234a97905eb1fc3a5c26809f9823614b0f9175b3b32f272f3e",
        "byte_difference_gate_status": "PASS" if np.any(
            np.asarray(Image.open(INPUT_CROP).convert("RGB")) != np.asarray(candidate_crop.convert("RGB"))
        ) else "FAIL",
        "classification": None,
    }
    if not report["candidate"]["full_frame_detection"]["count"]:
        report["classification"] = "MODEL_OUTPUT_GEOMETRY_FAILURE"
    elif candidate_changes["outside_mask"]["changed_pixel_pct"] > 0.0:
        report["classification"] = "MASK_APPLICATION_FAILURE"
    else:
        report["classification"] = "RECOVERED"
    (OUT / "qc4c2f-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "audit.json").write_text(json.dumps({"execution_id": run_job.job_id, "state": "FINALIZE",
        "provider": "comfyui-local", "workflow_sha256": workflow_sha,
        "mask": report["new_mask"], "candidate": report["candidate"],
        "status": "PASS" if report["classification"] == "RECOVERED" else "FAIL"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
