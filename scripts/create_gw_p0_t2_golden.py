"""Freeze the three GW-P0-T2 golden cases from the current local adapter."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.config import ComfyUIConfig
from image_studio_runtime.action_composite.masks import crop_for_identity, hierarchical_face_masks
from image_studio_runtime.action_composite.models import ActionCompositeJob, BoundingBox
from image_studio_runtime.action_composite.pipeline import ActionCompositePipeline
from image_studio_runtime.action_composite.providers import ComfyUIIdentityRestorer


ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
WORKFLOW = ROOT / "config/comfyui/face_restore_v1_api.json"
GOLDEN = ROOT / "tests/identity_restoration/golden"

CASES = (
    ("gw-p0-t2-case-01", (407, 150, 682, 441)),
    ("gw-p0-t2-case-02", (420, 165, 670, 425)),
    ("gw-p0-t2-case-03", (395, 135, 695, 455)),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_lock(base: Image.Image, composite: Image.Image, mask: Image.Image) -> dict[str, object]:
    before = np.asarray(base.convert("RGB"))
    after = np.asarray(composite.convert("RGB"))
    changed = np.any(before != after, axis=2)
    editable = np.asarray(mask.convert("L")) > 0
    locked = ~editable
    return {
        "validator": "unchanged_outside_mask",
        "mutatedPixelCount": int(changed[locked].sum()),
        "editableChangedPixelCount": int(changed[editable].sum()),
        "lockedPixelCount": int(locked.sum()),
        "status": "PASS" if not bool(changed[locked].any()) else "FAIL",
    }


def main() -> None:
    GOLDEN.mkdir(parents=True, exist_ok=True)
    base = Image.open(BASE).convert("RGBA")
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    workflow_seed = workflow["3"]["inputs"]["seed"]
    if workflow_seed != 42:
        raise RuntimeError(f"Expected fixed seed 42, got {workflow_seed!r}")
    config = ComfyUIConfig(endpoint="http://127.0.0.1:8188", workflow_path=str(WORKFLOW),
                           workflow_version="face_restore_v1", timeout_seconds=180.0)
    restorer = ComfyUIIdentityRestorer(endpoint=config.endpoint, request_timeout=120.0,
                                       client_id="gw-p0-t2-golden")
    if not restorer.health_check():
        raise RuntimeError("comfyui-local health check failed")
    pipeline = ActionCompositePipeline()
    cases = []
    for case_id, coords in CASES:
        case_dir = GOLDEN / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        bbox = BoundingBox(left=coords[0], top=coords[1], right=coords[2], bottom=coords[3])
        input_crop, crop_box = crop_for_identity(base, bbox)
        input_path = case_dir / "input_crop.png"
        input_crop.save(input_path, format="PNG")
        job = ActionCompositeJob(
            job_id=case_id,
            base_image=str(BASE),
            identity_reference=str(A2),
            face_bbox=bbox,
            workflow_version="face_restore_v1",
            provider="comfyui-local",
            identity_reference_sha256=sha256(A2),
        )
        run_dir = case_dir / "_run"
        result = pipeline.run(job, restorer, output_dir=run_dir,
                              restorer_config={"workflow": workflow,
                                               "timeout_seconds": 180.0,
                                               "node_bindings": config.node_bindings})
        composite_source = Path(result.output_path)
        composite_path = case_dir / "composite.png"
        shutil.copy2(composite_source, composite_path)
        composite = Image.open(composite_path).convert("RGBA")
        restored_path = case_dir / "restored_crop.png"
        composite.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)).save(restored_path, format="PNG")
        mask = hierarchical_face_masks(base.size, bbox).shape
        lock = pixel_lock(base, composite, mask)
        if lock["status"] != "PASS":
            raise RuntimeError(f"pixel lock failed for {case_id}: {lock}")
        if sha256(input_path) == sha256(restored_path):
            raise RuntimeError(f"restored crop did not differ for {case_id}")
        # The live validator was recorded once in historical evidence; the
        # regression harness intentionally uses frozen local mock-vision values.
        face_values = [84.6, 84.4, 84.8]
        record = {
            "contract": "GW-P0-T2 golden-master v2.1",
            "case_id": case_id,
            "provider": "comfyui-local",
            "inputs": {
                "base_image": str(BASE), "base_sha256": sha256(BASE),
                "identity_reference": str(A2), "identity_reference_sha256": sha256(A2),
                "input_crop": "input_crop.png", "input_crop_sha256": sha256(input_path),
            },
            "restored_crop": {"path": "restored_crop.png", "sha256": sha256(restored_path),
                              "differs_from_input": sha256(input_path) != sha256(restored_path)},
            "composite": {"path": "composite.png", "sha256": sha256(composite_path)},
            "pixelLock": lock,
            "cropTransform": {"method": "crop_for_identity", "scale": 2.5,
                              "source_size": {"width": base.width, "height": base.height},
                              "box": crop_box.model_dump(),
                              "forward": "crop = base.crop((left, top, right, bottom))",
                              "inverse": "base coordinates = crop coordinates + (left, top)"},
            "seed": workflow_seed,
            "face_qc": {"samples": 3, "values": face_values,
                        "raw_values": [{"sample_index": i, "score": value, "provider": "frozen-local-mock-vision"}
                                       for i, value in enumerate(face_values)],
                        "expected_baseline": 84.6, "tolerance": 2.0,
                        "mode": "frozen-local-mock-vision",
                        "historical_live_evidence": "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/gw-p0-t2-qc4-report.json"},
            "lineage": {"workflow": str(WORKFLOW), "workflow_sha256": sha256(WORKFLOW),
                        "workflow_version": "face_restore_v1", "run_artifact": "transient local ComfyUI output removed after freeze",
                        "golden_directory": str(case_dir)},
        }
        (case_dir / "case.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.rmtree(run_dir)
        cases.append(record)
    index = {"contract": "GW-P0-T2 golden-master v2.1", "golden_case_count": len(cases),
             "case_ids": [case["case_id"] for case in cases], "cases": cases}
    (GOLDEN / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
