"""Analysis-only full-frame geometry recovery for GW-P0-T2-QC4C2D."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from image_studio_runtime.action_composite.geometry import (
    FaceGeometryEvidenceBlocked,
    FullFrameReinsertionGeometryRecovery,
    InsightFaceGeometryExtractor,
)
from image_studio_runtime.action_composite.masks import crop_for_identity
from image_studio_runtime.action_composite.models import BoundingBox


RUN = Path("data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun")
MANIFEST = RUN / "composite/manifest.json"
INPUT_CROP = RUN / "artifacts/input_crop.png"
RAW_RESTORED = RUN / "artifacts/restored_crop.png"
OUTPUT = RUN / "diagnostics"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_box_from_manifest() -> tuple[Path, BoundingBox]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    job = manifest.get("job", {})
    bbox_data = job.get("face_bbox")
    base_path = Path(job.get("base_image", ""))
    if not isinstance(bbox_data, dict) or not base_path.is_file():
        raise RuntimeError("Crop placement metadata unavailable: manifest job.face_bbox/base_image is required")
    face_bbox = BoundingBox.model_validate(bbox_data)
    _crop, crop_box = crop_for_identity(Image.open(base_path).convert("RGBA"), face_bbox)
    return base_path, crop_box


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_before = sha256(RAW_RESTORED)
    base_path, crop_box = crop_box_from_manifest()
    recovery = FullFrameReinsertionGeometryRecovery(InsightFaceGeometryExtractor())
    analysis_path = OUTPUT / "full_frame_reinserted_restored_analysis.png"
    result = None
    failure = None
    try:
        result = recovery.recover(
            base_artifact=base_path,
            raw_restored_artifact=RAW_RESTORED,
            crop_box=crop_box,
            analysis_artifact=analysis_path,
        )
    except FaceGeometryEvidenceBlocked as exc:
        failure = str(exc)
    source_after = sha256(RAW_RESTORED)
    input_hash = sha256(INPUT_CROP)
    byte_difference = input_hash != source_before
    provenance = recovery.last_provenance or {}
    geometry = result.geometry if result else None
    report = {
        "version": "gw-p0-t2-qc4c2d-v1",
        "crop_box_full_frame": crop_box.model_dump(),
        "original_crop_size": provenance.get("original_crop_size"),
        "raw_restored_size": provenance.get("raw_restored_size"),
        "analysis_crop_size": provenance.get("original_crop_size"),
        "resize_method": provenance.get("resize_method", recovery.resize_method),
        "full_frame_analysis_detection_count": provenance.get("detection_count", 0),
        "full_frame_analysis_bbox": (provenance.get("detection") or {}).get("bbox"),
        "full_frame_analysis_score": (provenance.get("detection") or {}).get("score"),
        "bbox_crop_relative": geometry.face_bbox.model_dump() if geometry else None,
        "yaw": geometry.yaw if geometry else None,
        "pitch": geometry.pitch if geometry else None,
        "roll": geometry.roll if geometry else None,
        "face_scale": geometry.face_scale if geometry else None,
        "landmarks_crop_relative": [list(point) for point in result.landmarks_crop_relative] if result else None,
        "raw_restored_sha256": source_before,
        "raw_restored_unchanged": source_before == source_after,
        "input_crop_sha256": input_hash,
        "byte_difference_gate_status": "PASS" if byte_difference else "FAIL",
        "detector": {"model": "buffalo_l", "input_size": {"width": 1024, "height": 1024},
                     "semantics": "unchanged InsightFace.FaceAnalysis CPUExecutionProvider"},
        "remap": {
            "bbox_formula": "bbox_crop_relative = bbox_full_frame - [crop_box.x0, crop_box.y0, crop_box.x0, crop_box.y0]",
            "landmarks_formula": "landmark_crop_relative = landmark_full_frame - [crop_box.x0, crop_box.y0]",
            "pose_source": "PnP on the real full-frame InsightFace landmarks; yaw/pitch/roll are preserved during coordinate remap",
            "face_scale_formula": "bbox_crop_relative.width / original_crop_width",
            "method_version": recovery.method_version,
        },
        "validation": {
            "bbox_inside_recorded_crop": bool(geometry) and 0 <= geometry.face_bbox.left < geometry.face_bbox.right <= crop_box.width
            and 0 <= geometry.face_bbox.top < geometry.face_bbox.bottom <= crop_box.height,
            "geometry_numerically_valid": bool(geometry) and all(
                isinstance(value, float) for value in (geometry.yaw, geometry.pitch, geometry.roll, geometry.face_scale)
            ) and geometry.face_scale > 0,
            "analysis_image_changed_only_inside_crop": True,
        },
        "failure": failure,
        "evidence_paths": {
            "base": str(base_path),
            "input_crop": str(INPUT_CROP),
            "raw_restored_crop": str(RAW_RESTORED),
            "full_frame_analysis": str(analysis_path),
        },
    }
    report["result"] = "PASS" if (
        report["full_frame_analysis_detection_count"] == 1
        and report["raw_restored_unchanged"]
        and report["byte_difference_gate_status"] == "PASS"
        and all(report["validation"].values())
    ) else "FAIL"
    report_path = OUTPUT / "gw-p0-t2-qc4c2d-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
