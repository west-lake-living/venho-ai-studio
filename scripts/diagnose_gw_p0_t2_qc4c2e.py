"""Analysis-only delta localization for GW-P0-T2-QC4C2E."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.delta_localization import (
    diagnostic_zone_masks,
    mask_bounds,
    region_delta_metrics,
    replace_crop_regions,
    resize_restored_for_analysis,
    rgb_delta,
)
from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.masks import crop_for_identity
from image_studio_runtime.action_composite.models import BoundingBox


RUN = Path("data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun")
MANIFEST = RUN / "composite/manifest.json"
INPUT_CROP = RUN / "artifacts/input_crop.png"
RAW_RESTORED = RUN / "artifacts/restored_crop.png"
OUTPUT = RUN / "diagnostics/qc4c2e"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_metadata() -> tuple[Path, BoundingBox]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    job = manifest.get("job", {})
    base_path = Path(job.get("base_image", ""))
    bbox = job.get("face_bbox")
    if not base_path.is_file() or not isinstance(bbox, dict):
        raise RuntimeError("Crop placement metadata unavailable: manifest job.base_image and job.face_bbox are required")
    _crop, crop_box = crop_for_identity(Image.open(base_path).convert("RGBA"), BoundingBox.model_validate(bbox))
    return base_path, crop_box


def save_array(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array.astype(np.uint8), mode="RGB").save(path, format="PNG")


def detector_record(analyzer: Any, array: np.ndarray, *, name: str, artifact: Path, zones: list[str]) -> dict[str, Any]:
    faces = list(analyzer.get(array))
    detections = []
    for face in faces:
        detections.append({
            "bbox": [float(value) for value in face.bbox[:4]],
            "score": float(getattr(face, "det_score")),
            "landmarks": [[float(value) for value in point] for point in getattr(face, "kps", [])],
        })
    return {
        "name": name,
        "artifact": str(artifact),
        "artifact_sha256": sha256(artifact),
        "replaced_zones": zones,
        "detector": {"model": "buffalo_l", "input_size": [1024, 1024], "semantics": "unchanged"},
        "detection_count": len(faces),
        "detections": detections,
    }


def render_variant(base: np.ndarray, restored: np.ndarray, crop_box: BoundingBox, masks: dict[str, np.ndarray],
                   zones: list[str], artifact: Path, *, extra_mask: np.ndarray | None = None,
                   reverse: bool = False) -> np.ndarray:
    image = replace_crop_regions(base, restored, crop_box, masks, zones)
    if extra_mask is not None:
        crop = image[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right]
        source = base[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right] if reverse else restored
        crop[extra_mask] = source[extra_mask]
    save_array(image, artifact)
    return image


def submasks(mask: np.ndarray) -> list[np.ndarray]:
    bounds = mask_bounds(mask)
    if bounds is None or bounds.width <= 16 or bounds.height <= 16:
        return []
    mid_x = bounds.left + bounds.width // 2
    mid_y = bounds.top + bounds.height // 2
    pieces = []
    for top, bottom in ((bounds.top, mid_y), (mid_y, bounds.bottom)):
        for left, right in ((bounds.left, mid_x), (mid_x, bounds.right)):
            part = mask.copy()
            part[:top, :] = False
            part[bottom:, :] = False
            part[:, :left] = False
            part[:, right:] = False
            if part.any():
                pieces.append(part)
    return pieces


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_before = sha256(RAW_RESTORED)
    base_path, crop_box = crop_metadata()
    extractor = InsightFaceGeometryExtractor()
    analyzer, _cv2_runtime = extractor._runtime()
    base = np.asarray(Image.open(base_path).convert("RGB"))
    original_crop = np.asarray(Image.open(INPUT_CROP).convert("RGB"))
    derived_original_crop = base[crop_box.top:crop_box.bottom, crop_box.left:crop_box.right]
    if original_crop.shape != derived_original_crop.shape or not np.array_equal(original_crop, derived_original_crop):
        raise RuntimeError("Input crop does not byte-for-pixel match the crop derived from locked base/placement")
    restored = resize_restored_for_analysis(Image.open(RAW_RESTORED), (crop_box.width, crop_box.height))
    restored_array = np.asarray(restored)
    absolute, normalized = rgb_delta(Image.fromarray(original_crop), restored)
    save_array(absolute, OUTPUT / "absolute_rgb_difference.png")
    heatmap = cv2.cvtColor(cv2.applyColorMap(normalized, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    save_array(heatmap, OUTPUT / "normalized_difference_heatmap.png")

    base_artifact = OUTPUT / "original_full_base_detector_input.png"
    save_array(base, base_artifact)
    original_detection = detector_record(analyzer, base, name="original_base", artifact=base_artifact, zones=[])
    if original_detection["detection_count"] != 1:
        raise RuntimeError(f"Untouched original full base must detect exactly one face; got {original_detection['detection_count']}")
    face = original_detection["detections"][0]
    face_bbox = tuple(face["bbox"])
    masks = diagnostic_zone_masks(crop_size=(crop_box.width, crop_box.height),
                                  face_bbox_full_frame=face_bbox, crop_box=crop_box)
    metrics = region_delta_metrics(absolute, masks)
    zone_order = sorted(masks, key=lambda name: metrics[name].mean_absolute_rgb_delta, reverse=True)

    variants: list[dict[str, Any]] = [original_detection]
    for zone in masks:
        artifact = OUTPUT / "variants" / f"single-{zone}.png"
        image = render_variant(base, restored_array, crop_box, masks, [zone], artifact)
        variants.append(detector_record(analyzer, image, name=f"single-{zone}", artifact=artifact, zones=[zone]))

    cumulative: list[str] = []
    first_failure: dict[str, Any] | None = None
    previous = original_detection
    for index, zone in enumerate(zone_order, start=1):
        cumulative.append(zone)
        artifact = OUTPUT / "variants" / f"cumulative-{index:02d}.png"
        image = render_variant(base, restored_array, crop_box, masks, cumulative, artifact)
        current = detector_record(analyzer, image, name=f"cumulative-{index:02d}", artifact=artifact, zones=list(cumulative))
        variants.append(current)
        if first_failure is None and previous["detection_count"] == 1 and current["detection_count"] == 0:
            first_failure = {"prior_zones": list(cumulative[:-1]), "trigger_zone": zone,
                             "prior_record": previous, "record": current}
        previous = current

    suspect_mask = None
    binary_records: list[dict[str, Any]] = []
    if first_failure is not None:
        candidate = masks[first_failure["trigger_zone"]]
        prior_zones = first_failure["prior_zones"]
        depth = 0
        while depth < 5:
            pieces = submasks(candidate)
            if not pieces:
                break
            failing_piece = None
            for piece_index, piece in enumerate(pieces):
                artifact = OUTPUT / "variants" / f"binary-{depth}-{piece_index}.png"
                image = render_variant(base, restored_array, crop_box, masks, prior_zones, artifact, extra_mask=piece)
                record = detector_record(analyzer, image, name=f"binary-{depth}-{piece_index}", artifact=artifact,
                                         zones=prior_zones + [f"{first_failure['trigger_zone']}:subregion"])
                binary_records.append(record)
                if record["detection_count"] == 0 and failing_piece is None:
                    failing_piece = piece
            if failing_piece is None:
                break
            candidate = failing_piece
            depth += 1
        suspect_mask = candidate

    reverse_records: list[dict[str, Any]] = []
    reverse_recovery = None
    recovery_mask = None
    recovery_components: list[dict[str, Any]] = []
    if suspect_mask is not None:
        all_zones = list(masks)
        artifact = OUTPUT / "variants" / "reverse-suspect-region.png"
        image = render_variant(base, restored_array, crop_box, masks, all_zones, artifact,
                               extra_mask=suspect_mask, reverse=True)
        record = detector_record(analyzer, image, name="reverse-suspect-region", artifact=artifact,
                                 zones=["all_restored_minus_suspect_original"])
        reverse_records.append(record)
        if record["detection_count"] == 1:
            reverse_recovery = record
            recovery_mask = suspect_mask
            recovery_components = [{"name": "suspect_region", "bounds": mask_bounds(suspect_mask).model_dump()}]
        elif first_failure is not None:
            trigger = first_failure["trigger_zone"]
            artifact = OUTPUT / "variants" / "reverse-trigger-zone.png"
            image = render_variant(base, restored_array, crop_box, masks, all_zones, artifact,
                                   extra_mask=masks[trigger], reverse=True)
            record = detector_record(analyzer, image, name="reverse-trigger-zone", artifact=artifact,
                                     zones=[f"all_restored_minus_{trigger}_original"])
            reverse_records.append(record)
            if record["detection_count"] == 1:
                reverse_recovery = record
                recovery_mask = masks[trigger]
                recovery_components = [{"name": trigger, "bounds": mask_bounds(masks[trigger]).model_dump()}]
            else:
                # The full restored frame includes changed surrounding context.
                # Search every deterministic mouth subregion together with that
                # context, smallest combination first, to establish whether a
                # smaller original-pixel set can recover the one real face.
                context = masks["surrounding_context"]
                pieces = submasks(masks[trigger])
                candidates = [()] + [combo for size in range(1, len(pieces) + 1)
                                    for combo in itertools.combinations(range(len(pieces)), size)]
                for combo in candidates:
                    candidate_mask = context.copy()
                    for piece_index in combo:
                        candidate_mask |= pieces[piece_index]
                    artifact = OUTPUT / "variants" / f"reverse-context-mouth-{'-'.join(map(str, combo)) or 'none'}.png"
                    image = render_variant(base, restored_array, crop_box, masks, all_zones, artifact,
                                           extra_mask=candidate_mask, reverse=True)
                    record = detector_record(analyzer, image,
                                             name=f"reverse-context-mouth-{'-'.join(map(str, combo)) or 'none'}",
                                             artifact=artifact,
                                             zones=["original:surrounding_context", f"original:{trigger}:subregions={list(combo)}"])
                    reverse_records.append(record)
                    if record["detection_count"] == 1:
                        reverse_recovery = record
                        recovery_mask = candidate_mask
                        recovery_components = [
                            {"name": "surrounding_context", "bounds": mask_bounds(context).model_dump(),
                             "pixel_count": int(context.sum())},
                            *[{"name": f"{trigger}:subregion:{piece_index}",
                               "bounds": mask_bounds(pieces[piece_index]).model_dump(),
                               "pixel_count": int(pieces[piece_index].sum())} for piece_index in combo],
                        ]
                        break

    suspect_bounds = mask_bounds(suspect_mask) if suspect_mask is not None else None
    suspect_metrics = region_delta_metrics(absolute, {"suspect": suspect_mask})["suspect"] if suspect_mask is not None else None
    classification = "OTHER"
    if first_failure is not None:
        mapping = {
            "left_eye": "EYE_STRUCTURE_FAILURE", "right_eye": "EYE_STRUCTURE_FAILURE",
            "nose": "NOSE_STRUCTURE_FAILURE", "mouth": "MOUTH_STRUCTURE_FAILURE",
            "jaw_chin": "FACE_CONTOUR_FAILURE", "forehead_upper_head": "FOREHEAD_HEAD_BOUNDARY_FAILURE",
        }
        classification = mapping.get(first_failure["trigger_zone"], "OTHER")
        if not any(record["detection_count"] == 0 for record in binary_records):
            classification = "MULTI_REGION_GEOMETRY_FAILURE"
    report = {
        "version": "gw-p0-t2-qc4c2e-v1",
        "original_detection_bbox": face["bbox"],
        "original_detection_score": face["score"],
        "face_reference_geometry": {
            "landmarks": face["landmarks"],
            "center": [(face_bbox[0] + face_bbox[2]) / 2, (face_bbox[1] + face_bbox[3]) / 2],
            "width": face_bbox[2] - face_bbox[0], "height": face_bbox[3] - face_bbox[1],
            "zone_method": "deterministic non-overlapping bbox-relative partitions; five landmarks are insufficient for exact forehead/cheek/jaw contours",
        },
        "delta_summary": {
            "global_mean_absolute_rgb_delta": float(absolute.mean()),
            "global_changed_pixel_percentage": float((normalized > 0).mean() * 100),
            "zone_order_descending_delta": zone_order,
            "resize_method": "PIL.Resampling.BICUBIC",
        },
        "zone_results": {name: vars(metric) for name, metric in metrics.items()},
        "variants": variants,
        "binary_variants": binary_records,
        "reverse_variants": reverse_records,
        "first_failure_variant": first_failure["record"]["name"] if first_failure else None,
        "first_failure_zones": first_failure["record"]["replaced_zones"] if first_failure else None,
        "reverse_recovery_variant": reverse_recovery["name"] if reverse_recovery else None,
        "minimum_recovery_region": (
            {"crop_bounds": mask_bounds(recovery_mask).model_dump() if mask_bounds(recovery_mask) else None,
             "pixel_count": int(recovery_mask.sum()),
             "reverse_variant": reverse_recovery["name"], "components": recovery_components}
            if reverse_recovery and recovery_mask is not None else None
        ),
        "root_cause_classification": classification if reverse_recovery else None,
        "suspect_region_full_frame": (
            {"left": crop_box.left + suspect_bounds.left, "top": crop_box.top + suspect_bounds.top,
             "right": crop_box.left + suspect_bounds.right, "bottom": crop_box.top + suspect_bounds.bottom}
            if suspect_bounds else None
        ),
        "suspect_region_crop_relative": suspect_bounds.model_dump() if suspect_bounds else None,
        "suspect_region_delta_metrics": (
            {**vars(suspect_metrics),
             "detector_score_before_failure": first_failure["prior_record"]["detections"][0]["score"] if first_failure else None,
             "detector_outcome_after_replacement": first_failure["record"]["detection_count"] if first_failure else None}
            if suspect_metrics else None
        ),
        "canonical_artifacts_unchanged": source_before == sha256(RAW_RESTORED),
        "byte_difference_gate_status": "PASS" if sha256(INPUT_CROP) != source_before else "FAIL",
        "evidence_paths": {
            "absolute_rgb_difference": str(OUTPUT / "absolute_rgb_difference.png"),
            "normalized_difference_heatmap": str(OUTPUT / "normalized_difference_heatmap.png"),
            "variants": str(OUTPUT / "variants"),
            "report": str(OUTPUT / "gw-p0-t2-qc4c2e-report.json"),
        },
    }
    report["result"] = "PASS" if first_failure and reverse_recovery and report["canonical_artifacts_unchanged"] else "FAIL"
    (OUTPUT / "gw-p0-t2-qc4c2e-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
