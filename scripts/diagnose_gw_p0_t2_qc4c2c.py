"""Reproducible, read-only detector-input diagnosis for GW-P0-T2-QC4C2C."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor


RUN = Path("data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun")
RESTORED = RUN / "artifacts/restored_crop.png"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
OUTPUT = RUN / "diagnostics"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detection_record(name: str, image: np.ndarray, analyzer: Any, detector_size: tuple[int, int], artifact: Path) -> dict[str, Any]:
    # InsightFace receives this RGB ndarray exactly as persisted below. No channel
    # swap or image mutation is performed by this diagnostic.
    faces = list(analyzer.get(image))
    return {
        "name": name,
        "artifact": str(artifact),
        "input_dimensions": {"width": int(image.shape[1]), "height": int(image.shape[0])},
        "detector_input_size": {"width": detector_size[0], "height": detector_size[1]},
        "detection_count": len(faces),
        "detections": [
            {
                "bbox": [float(value) for value in face.bbox[:4]],
                "score": float(getattr(face, "det_score")),
            }
            for face in faces
        ],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_before = sha256(RESTORED)
    restored_source = Image.open(RESTORED)
    restored_rgba = np.asarray(restored_source.convert("RGBA"))
    restored_rgb = np.asarray(restored_source.convert("RGB"))
    base_rgb = np.asarray(Image.open(BASE).convert("RGB"))

    extractor = InsightFaceGeometryExtractor()
    analyzer, cv2_runtime = extractor._runtime()
    analysis_rgb, scale_factor = extractor._analysis_image(restored_rgb, cv2_runtime)

    original_png = OUTPUT / "detector_input_original.png"
    upscaled_png = OUTPUT / "detector_input_upscaled.png"
    full_base_png = OUTPUT / "detector_input_full_base.png"
    Image.fromarray(restored_rgb, mode="RGB").save(original_png, format="PNG")
    Image.fromarray(analysis_rgb, mode="RGB").save(upscaled_png, format="PNG")
    Image.fromarray(base_rgb, mode="RGB").save(full_base_png, format="PNG")

    crop_box = {"left": 201, "top": 0, "right": 888, "bottom": 659}
    face_box = {"left": 407, "top": 150, "right": 682, "bottom": 441}
    head_box = {"left": 256, "top": 0, "right": 833, "bottom": 601}
    crop_face = {key: face_box[key] - crop_box["left"] for key in ("left", "right")}
    crop_face.update({key: face_box[key] - crop_box["top"] for key in ("top", "bottom")})
    crop_head = {key: head_box[key] - crop_box["left"] for key in ("left", "right")}
    crop_head.update({key: head_box[key] - crop_box["top"] for key in ("top", "bottom")})

    report = {
        "version": "gw-p0-t2-qc4c2c-v1",
        "restored_source_sha256_before": source_before,
        "restored_source_sha256_after": sha256(RESTORED),
        "decoded_tensor": {
            "width": int(restored_rgb.shape[1]), "height": int(restored_rgb.shape[0]),
            "dtype": str(restored_rgb.dtype), "channels": int(restored_rgb.shape[2]),
            "min": int(restored_rgb.min()), "max": int(restored_rgb.max()),
            "alpha_present_in_source": restored_source.mode in {"RGBA", "LA"},
            "source_rgba_channels": int(restored_rgba.shape[2]),
            "color_order_sent_to_insightface": "RGB",
            "c_contiguous": bool(restored_rgb.flags["C_CONTIGUOUS"]),
            "visualization_matches_source_rgb": bool(np.array_equal(np.asarray(Image.open(original_png).convert("RGB")), restored_rgb)),
        },
        "runs": [
            detection_record("restored_original", restored_rgb, analyzer, extractor.det_size, original_png),
            detection_record("restored_upscaled", analysis_rgb, analyzer, extractor.det_size, upscaled_png),
            detection_record("full_base", base_rgb, analyzer, extractor.det_size, full_base_png),
        ],
        "crop_placement": {
            "input_crop_in_full_image": crop_box,
            "restored_crop_in_full_image": "not recorded; restored output is 680x656 while input crop is 687x659",
            "expected_face_bbox_in_full_image": face_box,
            "expected_face_bbox_in_crop": crop_face,
            "expected_head_bbox_in_crop": crop_head,
            "face_bbox_complete_in_crop": True,
            "forehead_clipped": True,
            "chin_clipped": False,
            "left_boundary_clipped": False,
            "right_boundary_clipped": False,
            "basis": "head_bbox top equals full-image and crop top (0); all other head edges remain within crop bounds",
        },
        "evidence_paths": [str(original_png), str(upscaled_png), str(full_base_png)],
    }
    counts = {item["name"]: item["detection_count"] for item in report["runs"]}
    if counts["full_base"] and not counts["restored_original"]:
        report["classification"] = "CROP/RESTORATION GEOMETRY FAILURE"
    elif not counts["full_base"] and not counts["restored_original"]:
        report["classification"] = "DETECTOR COMPATIBILITY / IMAGE CONTENT FAILURE"
    elif not report["decoded_tensor"]["visualization_matches_source_rgb"]:
        report["classification"] = "INPUT DECODING / COLOR PIPELINE FAILURE"
    else:
        report["classification"] = "NO CROP-ONLY DETECTION FAILURE OBSERVED"
    (OUTPUT / "gw-p0-t2-qc4c2c-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
