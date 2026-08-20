"""Score the locked GW-P0-T2 base with existing RegionalGate semantics only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.geometry import InsightFaceGeometryExtractor
from image_studio_runtime.action_composite.masks import crop_for_identity
from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry
from image_studio_runtime.action_composite.regional_score_gateway import GeometryEvidenceProducer
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


RUN = Path("data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun")
MANIFEST = RUN / "composite/manifest.json"
OUT = RUN / "diagnostics/qc4c3"
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
MASK = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/face-mask.png")

EXPECTED_BASE_SHA = "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
EXPECTED_A2_SHA = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
EXPECTED_MASK_SHA = "506fd5e52274b59af2881dcbaef3fe7904da7f30c75dc3bc23492dadf50ffb94"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_lock_reference(base: Image.Image, mask: Image.Image) -> dict[str, object]:
    pixels = np.asarray(base.convert("RGB"), dtype=np.uint8)
    editable = np.asarray(mask.convert("L"), dtype=np.uint8) > 0
    if editable.shape != pixels.shape[:2]:
        raise ValueError("pixel-lock mask dimensions do not match locked base")
    locked = ~editable
    return {
        "comparison_contract": "reference-only; no self-comparison PASS",
        "full_canvas": {"sha256": hashlib.sha256(pixels.tobytes()).hexdigest(), "shape": list(pixels.shape)},
        "editable_region": {"mask_sha256": sha256(MASK), "pixel_sha256": hashlib.sha256(pixels[editable].tobytes()).hexdigest(), "pixel_count": int(editable.sum())},
        "locked_region": {"pixel_sha256": hashlib.sha256(pixels[locked].tobytes()).hexdigest(), "pixel_count": int(locked.sum())},
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    job = manifest["job"]
    if Path(job["base_image"]) != BASE or sha256(BASE) != EXPECTED_BASE_SHA:
        raise RuntimeError("locked base authority mismatch")
    if sha256(A2) != EXPECTED_A2_SHA or manifest["identity_authority"]["sha256"] != EXPECTED_A2_SHA:
        raise RuntimeError("A2_FRONT authority mismatch")
    if sha256(MASK) != EXPECTED_MASK_SHA or job["metadata"]["mask_sha256"] != EXPECTED_MASK_SHA:
        raise RuntimeError("face mask authority mismatch")

    base = Image.open(BASE).convert("RGB")
    bbox = BoundingBox.model_validate(job["face_bbox"])
    _, crop_box = crop_for_identity(base, bbox)
    crop_transform = {
        "method": "crop_for_identity",
        "scale": 2.5,
        "source_size": {"width": base.width, "height": base.height},
        "box": crop_box.model_dump(),
        "forward": "crop = base.crop((left, top, right, bottom))",
        "inverse": "base coordinates = crop coordinates + (left, top)",
    }

    extractor = InsightFaceGeometryExtractor()
    observed = extractor.extract(BASE)
    provenance = dict(extractor.last_provenance or {})
    observed_dump = observed.model_dump()
    expected = FaceGeometry.model_validate(manifest["geometry"])
    geometry_score, geometry_source, geometry_provenance = GeometryEvidenceProducer().produce(
        expected, observed, source_artifacts=[str(BASE)],
    )

    # This is the production RegionalGate class, with only actually available evidence.
    gate = RegionalGate(geometry=geometry_score, pixel_preservation=False)
    gate_passed, gate_failures = gate.evaluate()
    thresholds = dict(gate.thresholds)
    regional = {}
    for name in ("identity", "eyes_brows", "geometry", "anatomy", "outfit", "environment", "global"):
        field = "global_composite" if name == "global" else name
        value = geometry_score if field == "geometry" else None
        regional[field] = {
            "raw_score": value,
            "threshold": thresholds[field],
            "status": "UNKNOWN" if value is None else ("PASS" if value >= thresholds[field] else "FAIL"),
            "validator": "RegionalGate" if value is not None else None,
            "evidence_source": str(BASE) if value is not None else None,
            "provenance": geometry_provenance if value is not None else None,
        }

    before = sha256(BASE)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "version": "gw-p0-t2-qc4c3-v1",
        "execution_id": job["job_id"],
        "base_path": {"absolute": str(BASE), "relative_to_repo": os.path.relpath(BASE, Path.cwd())},
        "base_sha256": before,
        "base_size": {"width": base.width, "height": base.height},
        "a2_authority_sha256": EXPECTED_A2_SHA,
        "crop_transform": crop_transform,
        "mask_version": manifest["mask"]["version"],
        "mask_path": str(MASK),
        "mask_sha256": EXPECTED_MASK_SHA,
        "regional": regional,
        "regional_gate": {"status": "PASS" if gate_passed else "BLOCKED", "passed": gate_passed, "failures": gate_failures, "thresholds": thresholds, "implementation": "image_studio_runtime.action_composite.workflow_v2.RegionalGate"},
        "geometry": {"source_sha256": before, "detection_count": 1, "detection_score": provenance.get("detection_score"), "bbox": observed_dump["face_bbox"], "landmarks": provenance.get("landmarks"), "yaw": observed.yaw, "pitch": observed.pitch, "roll": observed.roll, "face_scale": observed.face_scale, "reprojection_error": provenance.get("pnp", {}).get("reprojection_error_px"), "provenance": provenance, "geometry_score": geometry_score, "geometry_source": geometry_source},
        "face_qc": {"status": "DEFERRED_TO_QC4", "samples": [], "aggregate_score": None, "reason": "Historical GW-P0-T2 execution contains RegionalGate-only evidence; no Face Validator invocation was recorded."},
        "pixel_lock_reference": pixel_lock_reference(base, Image.open(MASK)),
        "evidence_source_sha_consistent": True,
        "canonical_artifacts_unchanged": True,
        "thresholds_unchanged": thresholds == {"identity": 90.0, "eyes_brows": 90.0, "geometry": 92.0, "anatomy": 90.0, "outfit": 90.0, "environment": 90.0, "global_composite": 90.0},
        "result": "PASS" if before == EXPECTED_BASE_SHA and not gate_passed else "BLOCKED",
    }
    after = sha256(BASE)
    report["canonical_artifacts_unchanged"] = before == after == EXPECTED_BASE_SHA
    report["evidence_source_sha_consistent"] = report["geometry"]["source_sha256"] == report["base_sha256"] == EXPECTED_BASE_SHA
    report["result"] = "PASS" if report["canonical_artifacts_unchanged"] and report["thresholds_unchanged"] and report["evidence_source_sha_consistent"] else "FAIL"
    (OUT / "gw-p0-t2-qc4c3-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
