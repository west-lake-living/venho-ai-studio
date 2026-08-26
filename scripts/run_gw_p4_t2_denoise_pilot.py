#!/usr/bin/env python3
"""Run the bounded GW-P4-T2 denoise pilot through the existing IDR ports.

This runner deliberately performs no Validator/Nano call.  It records the
local evidence that is available after each real Remote restoration and keeps
semantic Regional fields fail-closed when no paid Validator report exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml
from PIL import Image

from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.regional_score_gateway import (
    GeometryEvidenceProducer,
    StagePreservationEvidenceAdapter,
)
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate

from identity_restoration.application.benchmark_orchestration import BenchmarkCaseContextFactory
from identity_restoration.application.benchmark_contract import EXPECTED_A2_SHA256
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)
from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient
from identity_restoration.infrastructure.comfyui.workflow_repository import FileWorkflowRepository
from identity_restoration.infrastructure.restorers.comfyui_remote_restorer import ComfyUIRemoteRestorer


ROOT = Path(__file__).resolve().parents[1]
REMOTE_URL = os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "https://harry-rog.taila40de0.ts.net")
PILOT_ROOT = Path(os.environ.get(
    "GW_P4_T2_PILOT_ROOT",
    str(ROOT / "artifacts/identity-restoration/gw-p4-t2-denoise-pilot-20260825-r9"),
))
WORKFLOW_PATH = ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json"
PIN_PATH = ROOT / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
A2_PATH = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def candidate_graph(denoise: float) -> tuple[str, str, dict[str, Any]]:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    sampler = workflow["12"]
    if sampler.get("class_type") != "KSampler":
        raise RuntimeError("v2 topology changed: node 12 is not KSampler")
    frozen = {key: sampler["inputs"].get(key) for key in ("steps", "cfg", "sampler_name", "scheduler", "seed")}
    if frozen != {"steps": 20, "cfg": 6.0, "sampler_name": "euler", "scheduler": "normal", "seed": 123456}:
        # The exported graph seed is not the benchmark seed; the request binder
        # overwrites it with 42. All other frozen fields must remain exact.
        expected = {"steps": 20, "cfg": 6.0, "sampler_name": "euler", "scheduler": "normal", "seed": 123456}
        if any(frozen[key] != expected[key] for key in expected if key != "seed"):
            raise RuntimeError(f"v2 frozen sampler fields changed: {frozen}")
    sampler["inputs"]["denoise"] = denoise
    graph_bytes = json.dumps(workflow, sort_keys=True, separators=(",", ":")).encode()
    graph_sha = sha_bytes(graph_bytes)
    candidate_id = f"face_restore_win_sd15_ipadapter_v2_candidate_d{int(denoise * 100):02d}"
    return candidate_id, graph_sha, workflow


def main() -> int:
    if sha_path(A2_PATH) != EXPECTED_A2_SHA256:
        raise RuntimeError("A2 authority hash mismatch")
    manifest = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
    cases = {item["id"]: item for item in manifest["cases"]}
    context_factory = BenchmarkCaseContextFactory(repo_root=ROOT, canonical_a2_path=A2_PATH, geometry_backend="yunet")
    pin_repo = FileWorkflowRepository(WORKFLOW_PATH.parent, PIN_PATH)
    parent_workflow, parent_descriptor = pin_repo.load("face_restore_win_sd15_ipadapter_v2")
    if sha_path(WORKFLOW_PATH) != parent_descriptor.sha256:
        raise RuntimeError("frozen v2 workflow SHA mismatch")

    PILOT_ROOT.mkdir(parents=True, exist_ok=False)
    env = RestorationEnv(
        default_restorer="comfyui-remote", comfyui_enabled=True,
        comfyui_base_url=REMOTE_URL, comfyui_remote_enabled=True,
        comfyui_remote_base_url=REMOTE_URL, comfyui_timeout_seconds=900,
        comfyui_remote_timeout_seconds=900, health_ttl_seconds=0, workflow_root="identity_restoration/workflows",
        artifact_root=str(PILOT_ROOT / "restoration-artifacts"),
        ledger_path=str(PILOT_ROOT / "restoration-ledger.jsonl"), a2_path=str(A2_PATH),
        geometry_backend="yunet",
    )
    module = build_identity_restoration_module(env, repo_root=ROOT)
    results: list[dict[str, Any]] = []
    denoise_values = tuple(float(value) for value in os.environ.get("GW_P4_T2_DENOISES", "0.30,0.25,0.20").split(","))
    pilot_cases = tuple(value for value in os.environ.get("GW_P4_T2_CASES", "B03,B04").split(",") if value)
    for denoise in denoise_values:
        candidate_id, candidate_sha, workflow = candidate_graph(denoise)
        candidate_dir = PILOT_ROOT / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=False)
        candidate_manifest = {
            "candidateId": candidate_id, "parentWorkflowId": "face_restore_win_sd15_ipadapter_v2",
            "parentWorkflowSha256": parent_descriptor.sha256, "candidateWorkflowSha256": candidate_sha,
            "changed": {"denoise": denoise},
            "frozen": {"steps": 20, "cfg": 6.0, "sampler": "euler", "scheduler": "normal", "seed": 42,
                       "a2Sha256": EXPECTED_A2_SHA256, "maskVersion": "hierarchical_face_v1"},
            "topologyChanged": False, "validatorCalls": 0, "nanoCalls": 0,
        }
        (candidate_dir / "candidate.json").write_text(json.dumps(candidate_manifest, indent=2) + "\n")
        candidate_restorer = ComfyUIRemoteRestorer(
            client=ComfyUIHttpClient(base_url=REMOTE_URL, timeout_s=900), workflow=workflow,
            workflow_id=candidate_id, workflow_sha256=candidate_sha,
            model_identifiers=parent_descriptor.models, timeout_seconds=900,
        )
        module.registry.restorers["comfyui-remote"] = candidate_restorer
        for case_id in pilot_cases:
            context = context_factory.build(cases[case_id])
            run_id = f"{candidate_id}-{case_id.lower()}"
            attempt_id = "attempt-1"
            command = context.remote_command(run_id, attempt_id, 42)
            command = replace(command, workflow_id=candidate_id, params=RestorationParams(
                denoise=denoise, steps=20, cfg=6.0, sampler="euler", scheduler="normal"))
            health = module.health.probe() if module.health is not None else None
            if health is None or health.status.value != "HEALTHY":
                raise RuntimeError(f"health gate failed before {case_id}/{candidate_id}: {health}")
            result = module.use_case.execute(command)
            if result.composite_path is None or result.restored_crop_path is None:
                raise RuntimeError(f"missing output for {case_id}/{candidate_id}: {result}")
            output = Path(result.composite_path)
            restored = Path(result.restored_crop_path)
            with Image.open(output) as image:
                image.load()
                dimensions = image.size
            expected = json.loads(context.geometry_path.read_text())
            extractor = create_geometry_extractor("yunet")
            expected_geometry = extractor(Path(expected["sourcePath"]))
            observed_geometry = extractor(output)
            geometry_score, _, geometry_provenance = GeometryEvidenceProducer().produce(
                expected_geometry, observed_geometry, source_artifacts=[str(context.geometry_path), str(output)])
            box = {"left": context.crop_transform.source_x, "top": context.crop_transform.source_y,
                   "right": context.crop_transform.source_x + context.crop_transform.source_w,
                   "bottom": context.crop_transform.source_y + context.crop_transform.source_h}
            preservation = StagePreservationEvidenceAdapter().produce(
                source_artifact=context.base_path, candidate_artifact=output,
                mask_artifact=context.crop_mask_path, crop_box=box)
            pixel_pass = result.pixel_lock is not None and result.pixel_lock.passed
            anatomy_pass = pixel_pass and all(item.status == "PASS" for item in preservation)
            gate = RegionalGate(identity=None, eyes_brows=None, geometry=geometry_score,
                                anatomy=100.0 if anatomy_pass else 0.0,
                                outfit=100.0 if anatomy_pass else 0.0,
                                environment=100.0 if anatomy_pass else 0.0,
                                global_composite=None, pixel_preservation=pixel_pass)
            regional_pass, regional_failures = gate.evaluate()
            results.append({
                "candidateId": candidate_id, "denoise": denoise, "caseId": case_id,
                "status": result.status, "outputPath": str(output), "restoredCropPath": str(restored),
                "outputSha256": sha_path(output), "restoredCropSha256": sha_path(restored),
                "dimensions": dimensions, "runtimeMs": result.lineage.get("runtimeMs"),
                "pixel": "PASS" if pixel_pass else "FAIL", "anatomy": "PASS" if anatomy_pass else "FAIL",
                "geometryScore": geometry_score, "geometry": geometry_provenance,
                "regional": "PASS" if regional_pass else "UNVALIDATED",
                "regionalFailures": regional_failures, "lineageComplete": bool(result.lineage),
                "health": {"status": health.status.value, "vramFreeMb": health.vram_free_mb,
                           "torchVramFreeMb": health.torch_vram_free_mb},
            })
            (PILOT_ROOT / "pilot-results.partial.json").write_text(json.dumps(results, indent=2) + "\n")
    (PILOT_ROOT / "pilot-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"pilotRoot": str(PILOT_ROOT), "jobs": len(results), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
