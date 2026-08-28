"""Dedicated, evaluation-only Candidate v3 Phase 7 entry point.

This module is intentionally not imported by the normal composition root.  It
is the only boundary through which the approved Phase 7 GPU evaluation may
construct a Candidate v3 service while the production feature flag remains
OFF.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from ..domain.entities import A2Authority, MaskSet, RestorationRequest
from ..domain.value_objects import RestorationParams
from .benchmark_contract import load_benchmark_manifest, validate_frozen_dataset
from .candidate_v3_service import (
    V3_WORKFLOW_SHA256,
    CandidateV3BridgePort,
    CandidateV3BridgeResult,
    CandidateV3JobRequest,
    CandidateV3RestorationService,
)
from .dto.candidate_v3 import CandidateV3Request
from .face_observability import FaceObservabilityService
from .ports.identity_pack_repository import IdentityPackRepositoryPort


PHASE_7_EVALUATION_PURPOSE = "PHASE_7_CANDIDATE_V3_EVALUATION"
BENCHMARK_BRANCH = "candidate-v3"
IDENTITY_PACK_ID = "linh-an-production-v3-2026-08"
EVALUATION_PROFILE_ID = "candidate-v3-sd15-faceid-canonical-512"
PINNED_SEED = 42
PINNED_PARAMS = RestorationParams(
    denoise=0.35, steps=20, cfg=6.0, sampler="euler", scheduler="normal"
)
SCENARIO_PROFILE_HASHES = {
    "canonical_default": "71f839dff776ec6d6d085c5a1ab928295af8c32a9699f7929d78b04807ec0075",
    "action_full_body@1.0": "fe4a2b454a5868e9fc4dfbc4216e413a69a186cc8b4ab89c066943843c869b1c",
}


class Phase7EvaluationError(ValueError):
    """Raised when the dedicated evaluation boundary is used incorrectly."""


class CandidateV3EvaluationAdapter(Protocol):
    def restore(self, request: RestorationRequest): ...

    def execution_evidence(self) -> dict[str, Any]: ...


@dataclass
class ComfyUiCandidateV3EvaluationBridge(CandidateV3BridgePort):
    """Adapt the existing Candidate v3 adapter to the Phase 5 service port."""

    adapter: CandidateV3EvaluationAdapter
    identity_packs: IdentityPackRepositoryPort
    expected_workflow_sha256: str = V3_WORKFLOW_SHA256

    def execute(self, request: CandidateV3Request) -> CandidateV3BridgeResult:
        if not request.selected_identity_references:
            raise Phase7EvaluationError("IDENTITY_AUTHORITY_INVALID")
        primary = request.selected_identity_references[0]
        if not primary.path or not primary.sha256:
            raise Phase7EvaluationError("IDENTITY_AUTHORITY_INVALID")
        reference_bytes = _read_verified(primary.path, primary.sha256, "PRIMARY_FRONTAL")
        authority = A2Authority.from_bytes(reference_bytes)
        authority.verify(primary.sha256)
        crop = _read_verified(request.canonical_image.path, request.canonical_image.sha256, "canonical image")
        editable = _read_verified(
            request.canonical_editable_mask.path,
            request.canonical_editable_mask.sha256,
            "canonical editable mask",
        )
        feather = _read_verified(
            request.canonical_feather_mask.path,
            request.canonical_feather_mask.sha256,
            "canonical feather mask",
        )
        restored = self.adapter.restore(
            RestorationRequest(
                run_id=request.run_id,
                attempt_id=request.attempt_id,
                crop_png=crop,
                mask=MaskSet(editable=editable, feather=feather, version="candidate-v3-canonical-v1"),
                a2=authority,
                workflow_id="face_restore_win_sd15_ipadapter_v3",
                seed=request.seed,
                params=PINNED_PARAMS,
            )
        )
        evidence = self.adapter.execution_evidence()
        if evidence.get("workflowSha256") != self.expected_workflow_sha256:
            raise Phase7EvaluationError("WORKFLOW_AUTHORITY_INVALID")
        return CandidateV3BridgeResult(
            restored_canonical_png=restored.png_bytes,
            lineage={
                "evaluationPurpose": PHASE_7_EVALUATION_PURPOSE,
                "evaluationOnly": True,
                "productionEligible": False,
                "benchmarkBranch": BENCHMARK_BRANCH,
                "workflowSha256": self.expected_workflow_sha256,
                "candidateProfileId": request.candidate_profile_id,
                # CandidateV3Request's ArtifactRef intentionally carries
                # content identity only; the service records pack/reference
                # IDs in its own reports.
                "selectedReferenceHashes": [ref.sha256 for ref in request.selected_identity_references],
                "adapterEvidence": evidence,
            },
        )


@dataclass
class Phase7CandidateV3EvaluationEntrypoint:
    """Explicit-purpose boundary that is inaccessible to normal production traffic."""

    service: CandidateV3RestorationService

    def evaluate(self, request: CandidateV3JobRequest, *, purpose: str | None) -> dict[str, Any]:
        _require_evaluation_purpose(purpose)
        submitted = self.service.submit(request)
        result = self.service.run(str(submitted["jobId"]))
        result["evaluation"] = {
            "purpose": PHASE_7_EVALUATION_PURPOSE,
            "benchmarkBranch": BENCHMARK_BRANCH,
            "evaluationOnly": True,
            "productionEligible": False,
            "featureFlag": "OFF",
        }
        return result


def build_cpu_evaluation_entrypoint(
    *,
    artifact_root: Path,
    bridge: CandidateV3BridgePort,
    observability: FaceObservabilityService,
    identity_packs: IdentityPackRepositoryPort,
) -> Phase7CandidateV3EvaluationEntrypoint:
    """Build the same orchestration boundary with an injected CPU test bridge."""
    return _build_entrypoint(
        artifact_root=artifact_root,
        bridge=bridge,
        observability=observability,
        identity_packs=identity_packs,
    )


def run_frozen_candidate_v3_benchmark(
    *,
    entrypoint: Phase7CandidateV3EvaluationEntrypoint,
    repo_root: Path,
    artifact_root: Path,
    run_id: str,
    purpose: str,
) -> dict[str, Any]:
    """Evaluate every frozen B01–B10 row without substituting cases."""
    manifest_path = repo_root / "contracts/identity_restoration/benchmark_set.yaml"
    manifest = load_benchmark_manifest(manifest_path)
    validate_frozen_dataset(manifest, repo_root=repo_root, require_all=True)
    geometry_root = repo_root / "artifacts/identity-restoration/benchmark-geometry/v2.1"
    rows: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_id = str(case["id"])
        frame = case["baseFrame"]
        base_path = Path(str(frame["path"]))
        if not base_path.is_absolute():
            base_path = repo_root / base_path
        geometry_path = geometry_root / case_id / "geometry_manifest.json"
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        mask_meta = geometry["fullCanvasMask"]
        mask_path = Path(str(mask_meta["path"]))
        if not mask_path.is_absolute():
            mask_path = repo_root / mask_path
        mask = _read_verified(str(mask_path), str(mask_meta["sha256"]), f"{case_id} full canvas mask")
        image = _read_verified(str(base_path), str(frame["sha256"]), f"{case_id} base frame")
        request = CandidateV3JobRequest(
            job_id=f"{run_id}-{case_id}",
            run_id=run_id,
            attempt_id=f"{case_id}-attempt-1",
            identity_pack_id=IDENTITY_PACK_ID,
            scenario_id=case_id,
            image_bytes=image,
            editable_mask_bytes=mask,
            feather_mask_bytes=mask,
            base_canvas_bytes=image,
            candidate_profile_id=EVALUATION_PROFILE_ID,
            candidate_version="3.0.0",
            seed=PINNED_SEED,
        )
        row = entrypoint.evaluate(request, purpose=purpose)
        # Terminal route records occur before the service reaches the manifest
        # enrichment fields; retain the benchmark identity for every row.
        row.setdefault("scenarioId", case_id)
        row.setdefault("route", row.get("status"))
        rows.append(row)
    result = {
        "schemaVersion": "phase-7-candidate-v3-evaluation-1.0",
        "purpose": purpose,
        "benchmarkBranch": BENCHMARK_BRANCH,
        "evaluationOnly": True,
        "productionEligible": False,
        "runId": run_id,
        "benchmarkManifest": str(manifest_path),
        "benchmarkManifestSha256": _sha256_path(manifest_path),
        "cases": rows,
        "caseCount": len(rows),
        "featureFlag": "OFF",
    }
    report_path = artifact_root / run_id / "phase-7-evaluation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def _build_entrypoint(
    *,
    artifact_root: Path,
    bridge: CandidateV3BridgePort,
    observability: FaceObservabilityService,
    identity_packs: IdentityPackRepositoryPort,
):
    from .candidate_v3_service import CandidateV3RestorationService

    bindings = _scenario_bindings()
    return Phase7CandidateV3EvaluationEntrypoint(
        CandidateV3RestorationService(
            enabled=True,
            artifact_root=artifact_root,
            identity_packs=identity_packs,
            observability=observability,
            bridge=bridge,
            scenario_resolver=bindings.get,
            # Phase 7 provider calls are explicitly zero. Missing external
            # Face-QC/Scenario-QC evidence therefore remains UNVALIDATED.
            face_qc=None,
            scenario_validator=None,
        )
    )


def _scenario_bindings() -> dict[str, Mapping[str, Any]]:
    bindings: dict[str, Mapping[str, Any]] = {}
    for case_id in (f"B{i:02d}" for i in range(1, 11)):
        profile_id = "action_full_body@1.0" if case_id in {"B03", "B04"} else "canonical_default"
        slug = re.sub(r"[^a-z0-9]+", "-", profile_id, flags=re.IGNORECASE)
        bindings[case_id] = {
            "bindingId": f"candidate-v3-{case_id}-{slug}-v1",
            "scenarioId": case_id,
            "imageQcProfileId": profile_id,
            "sha256": SCENARIO_PROFILE_HASHES[profile_id],
            "allowedExclusions": ["shot_distance", "hairstyle"] if case_id in {"B03", "B04"} else [],
            "status": "APPROVED",
        }
    return bindings


def _require_evaluation_purpose(purpose: str | None) -> None:
    if purpose != PHASE_7_EVALUATION_PURPOSE:
        raise Phase7EvaluationError("PHASE_7_EVALUATION_PURPOSE_REQUIRED")


def _read_verified(path_text: str, expected_sha256: str, label: str) -> bytes:
    path = Path(path_text)
    if not path.is_file():
        raise Phase7EvaluationError(f"{label.upper().replace(' ', '_')}_MISSING")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise Phase7EvaluationError(f"{label.upper().replace(' ', '_')}_HASH_MISMATCH")
    return data


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
