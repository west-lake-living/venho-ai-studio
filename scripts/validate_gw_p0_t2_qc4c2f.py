"""Revalidate an existing QC4C2F candidate without calling ComfyUI."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from execute_gw_p0_t2_qc4c2f import (
    BASE, DIAG, INPUT_CROP, OLD_RESTORED, OLD_RUN, OUT, _change_metrics,
    _detector_face_and_landmarks, _face_regions, _mask_stats,
)
from image_studio_runtime.action_composite.delta_localization import geometry_drift
from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.models import BoundingBox
from image_studio_runtime.action_composite.masks import crop_for_identity


def raw_detection(extractor: InsightFaceGeometryExtractor, path: Path) -> dict:
    analyzer, cv2 = extractor._runtime()
    source = np.asarray(Image.open(path).convert("RGB"))
    analysis, scale = extractor._analysis_image(source, cv2)
    faces = list(analyzer.get(analysis))
    records = []
    for face in faces:
        records.append({
            "bbox": (np.asarray(face.bbox, dtype="float64") / scale).tolist(),
            "score": float(getattr(face, "det_score", 0.0)),
            "landmarks": (np.asarray(face.kps, dtype="float64") / scale).tolist()
            if getattr(face, "kps", None) is not None else None,
        })
    return {"count": len(records), "detections": records,
            "input_dimensions": {"width": int(source.shape[1]), "height": int(source.shape[0])},
            "analysis_dimensions": {"width": int(analysis.shape[1]), "height": int(analysis.shape[0])},
            "scale_factor": scale, "detector": "InsightFace.FaceAnalysis", "model": extractor.model_name}


def geometry_attempt(extractor: InsightFaceGeometryExtractor, path: Path) -> dict:
    try:
        geometry = extractor.extract(path)
        return {"status": "PASS", "geometry": geometry.model_dump(),
                "provenance": extractor.last_provenance}
    except Exception as exc:
        return {"status": "BLOCKED", "geometry": None, "error": str(exc),
                "provenance": extractor.last_provenance}


def main() -> None:
    report_path = OUT / "qc4c2f-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_crop = OUT / "artifacts/restored_crop.png"
    candidate_full = OUT / "composite/image.png"
    manifest = json.loads((OLD_RUN / "composite/manifest.json").read_text(encoding="utf-8"))
    base = Image.open(BASE).convert("RGBA")
    crop_box = crop_for_identity(base, BoundingBox.model_validate(manifest["job"]["face_bbox"]))[1]
    extractor = InsightFaceGeometryExtractor()
    original_bbox, _landmarks, _ = _detector_face_and_landmarks(extractor, BASE)
    original_geometry = geometry_attempt(extractor, BASE)
    candidate_image = Image.open(candidate_crop).convert("RGB")
    regions = _face_regions(candidate_image.size, original_bbox, crop_box)
    old_resized = Image.open(OLD_RESTORED).convert("RGB").resize(candidate_image.size, Image.Resampling.BICUBIC)
    candidate = candidate_image
    mask = Image.open(DIAG / "geometry_preserving_mask.png").convert("L")
    old_mask = np.asarray(Image.open(DIAG / "current_restoration_mask.png").convert("L")) > 0
    face_region = np.zeros(old_mask.shape, dtype=bool)
    face_region[236:370, 274:374] = True
    report["old_mask"]["mask_coverage_outside_authoritative_face_bbox_pct"] = float(
        old_mask[~face_region].mean() * 100
    )
    report["new_mask"]["mask_coverage_outside_authoritative_face_bbox_pct"] = float(
        (np.asarray(mask) > 0)[~face_region].mean() * 100
    )
    changes = _change_metrics(Image.open(INPUT_CROP), candidate,
                              regions={"inside_mask": np.asarray(mask) > 0,
                                       "outside_mask": np.asarray(mask) == 0, **regions})
    old_changes = _change_metrics(Image.open(INPUT_CROP), old_resized, regions=regions)
    direct_raw = raw_detection(extractor, candidate_crop)
    full_raw = raw_detection(extractor, candidate_full)
    direct_geometry = geometry_attempt(extractor, candidate_crop)
    full_geometry = geometry_attempt(extractor, candidate_full)
    report["geometry_extraction_audit"] = {
        "opencv_version": __import__("cv2").__version__,
        "old_pnp_method": "cv2.SOLVEPNP_ITERATIVE",
        "old_failure": "OpenCV solvePnP DLT algorithm needs at least 6 points; provided 5",
        "old_use_extrinsic_guess": False,
        "current_initial_pnp_method": InsightFaceGeometryExtractor.pnp_initial_method,
        "current_refinement_method": InsightFaceGeometryExtractor.pnp_refinement_method,
        "landmark_count": 5,
        "landmark_order": list(InsightFaceGeometryExtractor.landmark_order),
        "original": original_geometry,
        "repaired_candidate": full_geometry,
    }
    report["old_change_regions"] = old_changes
    report["candidate"]["changes"] = changes
    report["candidate"]["direct_detection"] = {**direct_raw, "geometry_attempt": direct_geometry}
    report["candidate"]["full_frame_detection"] = {**full_raw, "geometry_attempt": full_geometry}
    report["candidate"]["geometry"] = {"direct": direct_geometry, "full_frame": full_geometry}
    observed_bbox = tuple(full_raw["detections"][0]["bbox"]) if full_raw["count"] == 1 else None
    report["geometry_drift"] = (
        geometry_drift(tuple(float(v) for v in report["original_face_bbox"]), observed_bbox)
        if observed_bbox is not None else None
    )
    report["direct_detection_count"] = direct_raw["count"]
    report["direct_detection_bbox"] = direct_raw["detections"][0]["bbox"] if direct_raw["count"] == 1 else None
    report["direct_detection_score"] = direct_raw["detections"][0]["score"] if direct_raw["count"] == 1 else None
    report["full_frame_detection_count"] = full_raw["count"]
    report["full_frame_detection_bbox"] = full_raw["detections"][0]["bbox"] if full_raw["count"] == 1 else None
    report["full_frame_detection_score"] = full_raw["detections"][0]["score"] if full_raw["count"] == 1 else None
    full_geometry_values = full_geometry.get("geometry") or {}
    report["yaw"] = full_geometry_values.get("yaw")
    report["pitch"] = full_geometry_values.get("pitch")
    report["roll"] = full_geometry_values.get("roll")
    report["face_scale"] = full_geometry_values.get("face_scale")
    original_values = original_geometry.get("geometry") or {}
    if full_geometry["status"] == "PASS" and original_geometry["status"] == "PASS":
        report["drift"] = geometry_drift(
            tuple(float(v) for v in report["original_face_bbox"]),
            tuple(float(v) for v in full_raw["detections"][0]["bbox"]),
            reference_angles=(original_values["yaw"], original_values["pitch"], original_values["roll"]),
            observed_angles=(full_geometry_values["yaw"], full_geometry_values["pitch"], full_geometry_values["roll"]),
            reference_face_scale=original_values["face_scale"],
            observed_face_scale=full_geometry_values["face_scale"],
        )
    else:
        report["drift"] = report.get("geometry_drift")
    report["geometry_values_finite"] = full_geometry["status"] == "PASS" and original_geometry["status"] == "PASS"
    report["comparison_old_vs_repaired"] = {
        "old_restored_direct_detection_count": 0,
        "old_restored_full_frame_detection_count": 0,
        "repaired_direct_detection_count": direct_raw["count"],
        "repaired_full_frame_detection_count": full_raw["count"],
        "old_total_changed_pixel_pct": old_changes["total_changed_pixel_pct"],
        "repaired_total_changed_pixel_pct": changes["total_changed_pixel_pct"],
        "repaired_outside_mask_changed_pixel_pct": changes["outside_mask"]["changed_pixel_pct"],
        "geometry_available": full_geometry["status"] == "PASS",
    }
    report["classification"] = (
        "RECOVERED" if full_raw["count"] == 1 and full_geometry["status"] == "PASS" and changes["outside_mask"]["changed_pixel_pct"] == 0.0
        else "GEOMETRY_EXTRACTION_FAILURE" if full_raw["count"] == 1
        else "MODEL_OUTPUT_GEOMETRY_FAILURE"
    )
    report["pass"] = report["classification"] == "RECOVERED" and report["canonical_artifacts_unchanged"] and report["byte_difference_gate_status"] == "PASS"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "audit.json").write_text(json.dumps({"execution_id": report["execution_id"], "state": "FINALIZE",
        "provider": report["provider"], "candidate": report["candidate"],
        "classification": report["classification"], "status": "PASS" if report["pass"] else "FAIL"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
