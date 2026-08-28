"""Phase 5 Candidate v3 service, bridge, job, and API boundaries.

The service composes the already approved Phase 1–4 authorities.  It is a
mockable control-plane boundary: the default feature flag is OFF and this
module performs no provider or network work itself.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from PIL import Image

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows worker uses atomic replace; tests run on macOS.
    fcntl = None  # type: ignore[assignment]

from .candidate_v3_route_policy import load_candidate_v3_route_policy
from ..domain.policies.candidate_v3_route_policy import evaluate_candidate_v3_route
from .canonical_transform import CanonicalizationResult, CanonicalFaceTransformService
from .dto.candidate_v3 import ArtifactRef, CandidateV3Request
from .face_observability import FaceObservability, FaceObservabilityService
from .identity_pack import IdentityPack
from .phase4_quality import (
    BoundaryQcResult,
    QualityBundleMerger,
    ScopedQcResult,
    evaluate_boundary_qc,
    evaluate_correctness_qc,
    face_local_qc_candidate_v3,
    inverse_composite_candidate_v3,
    load_candidate_v3_quality_policy,
    manifest_1_4_enrichment,
    write_immutable_qc_report,
    append_qc_history,
)
from .ports.identity_pack_repository import IdentityPackRepositoryPort


V3_WORKFLOW_SHA256 = "53dc090691b8feac2a8b8a4309d43af737e304b09330e072b4ab5632ed5aad91"


class CandidateV3ServiceError(ValueError):
    """A stable, client-safe Phase 5 boundary error."""


class CandidateV3BridgePort(Protocol):
    def execute(self, request: CandidateV3Request) -> "CandidateV3BridgeResult": ...


@dataclass(frozen=True)
class CandidateV3BridgeResult:
    restored_canonical_png: bytes
    lineage: Mapping[str, Any]


@dataclass(frozen=True)
class CandidateV3JobRequest:
    job_id: str
    run_id: str
    attempt_id: str
    identity_pack_id: str
    scenario_id: str
    image_bytes: bytes
    editable_mask_bytes: bytes
    feather_mask_bytes: bytes
    base_canvas_bytes: bytes
    candidate_profile_id: str = "candidate-v3-sd15-faceid-canonical-512"
    candidate_version: str = "3.0.0"
    effective_config_sha256: str = ""
    seed: int = 0
    timeout_seconds: int = 600

    def fingerprint(self) -> str:
        payload = {
            "jobId": self.job_id,
            "runId": self.run_id,
            "identityPackId": self.identity_pack_id,
            "scenarioId": self.scenario_id,
            "imageSha256": hashlib.sha256(self.image_bytes).hexdigest(),
            "editableMaskSha256": hashlib.sha256(self.editable_mask_bytes).hexdigest(),
            "featherMaskSha256": hashlib.sha256(self.feather_mask_bytes).hexdigest(),
            "baseCanvasSha256": hashlib.sha256(self.base_canvas_bytes).hexdigest(),
            "candidateProfileId": self.candidate_profile_id,
            "candidateVersion": self.candidate_version,
            "effectiveConfigSha256": self.effective_config_sha256,
            "seed": self.seed,
            "timeoutSeconds": self.timeout_seconds,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class CandidateV3JobStore:
    root: Path
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def _path(self, job_id: str) -> Path:
        if not job_id or Path(job_id).name != job_id or ".." in Path(job_id).parts:
            raise CandidateV3ServiceError("INVALID_JOB_ID")
        return self.root / "jobs" / f"{job_id}.json"

    def get(self, job_id: str) -> dict[str, Any] | None:
        path = self._path(job_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateV3ServiceError("JOB_RECORD_INVALID") from exc

    def save(self, record: Mapping[str, Any]) -> None:
        path = self._path(str(record.get("jobId", "")))
        data = json.dumps(dict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            with tmp.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)

    def create_or_replay(self, request: CandidateV3JobRequest) -> dict[str, Any]:
        fingerprint = request.fingerprint()
        with self._lock:
            with self._process_lock():
                existing = self.get(request.job_id)
                if existing is not None:
                    if existing.get("requestFingerprint") != fingerprint:
                        raise CandidateV3ServiceError("IDEMPOTENCY_CONFLICT")
                    return existing
                record = {
                    "jobId": request.job_id,
                    "runId": request.run_id,
                    "attemptId": request.attempt_id,
                    "requestFingerprint": fingerprint,
                    "status": "QUEUED",
                    "createdAt": _now(),
                    "updatedAt": _now(),
                }
                self.save(record)
                return record

    @contextmanager
    def _process_lock(self):
        """Serialize cross-process first-writer idempotency decisions."""
        lock_path = self.root / "jobs" / ".candidate-v3.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+")
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


@dataclass
class CandidateV3RestorationService:
    """Single Candidate v3 orchestration path for Phase 5 mocked execution."""

    enabled: bool
    artifact_root: Path
    identity_packs: IdentityPackRepositoryPort
    observability: FaceObservabilityService
    bridge: CandidateV3BridgePort
    scenario_resolver: Callable[[str], Mapping[str, Any] | None]
    scenario_validator: Callable[[Mapping[str, Any], bytes], bool | None] | None = None
    face_qc: Callable[[bytes, Sequence[str]], float | None] | None = None
    expected_workflow_sha256: str = V3_WORKFLOW_SHA256
    transform_service: CanonicalFaceTransformService = field(default_factory=CanonicalFaceTransformService)
    jobs: CandidateV3JobStore | None = None
    _requests: dict[str, CandidateV3JobRequest] = field(default_factory=dict, init=False, repr=False)
    _cancelled: set[str] = field(default_factory=set, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.artifact_root = Path(self.artifact_root)
        self.jobs = self.jobs or CandidateV3JobStore(self.artifact_root)

    def submit(self, request: CandidateV3JobRequest) -> dict[str, Any]:
        if not self.enabled:
            raise CandidateV3ServiceError("CANDIDATE_V3_DISABLED")
        if request.timeout_seconds < 1 or not request.attempt_id:
            raise CandidateV3ServiceError("INVALID_REQUEST")
        with self._lock:
            self._requests[request.job_id] = request
            return self.jobs.create_or_replay(request)

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._require(job_id)
            self._cancelled.add(job_id)
            if record["status"] in {"QUEUED", "RUNNING"}:
                record["status"] = "CANCELLED"
                self._save(record)
            return record

    def retry(self, job_id: str, *, attempt_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._require(job_id)
            if record["status"] not in {"FAILED", "CANCELLED", "ORPHANED", "REVIEW_REQUIRED"}:
                raise CandidateV3ServiceError("RETRY_NOT_ALLOWED")
            request = self._requests.get(job_id)
            if request is None:
                raise CandidateV3ServiceError("RETRY_INPUT_UNAVAILABLE")
            self._requests[job_id] = CandidateV3JobRequest(**{**request.__dict__, "attempt_id": attempt_id})
            record.update({"attemptId": attempt_id, "status": "QUEUED", "updatedAt": _now(), "error": None})
            self._save(record)
            self._cancelled.discard(job_id)
            return record

    def run(self, job_id: str) -> dict[str, Any]:
        if not self.enabled:
            raise CandidateV3ServiceError("CANDIDATE_V3_DISABLED")
        with self._lock:
            record = self._require(job_id)
            request = self._requests.get(job_id)
            if request is None:
                return self._fail(record, "REQUEST_INPUT_UNAVAILABLE")
            if record["status"] == "COMPLETED":
                return record
            if record["status"] == "RUNNING":
                raise CandidateV3ServiceError("JOB_ALREADY_RUNNING")
            if record["status"] == "CANCELLED" or job_id in self._cancelled:
                return record
            record.update({"status": "RUNNING", "startedAt": _now(), "updatedAt": _now()})
            self._save(record)

        try:
            result = self._execute(request, record)
        except CandidateV3ServiceError as exc:
            with self._lock:
                return self._fail(record, str(exc))
        except Exception:
            with self._lock:
                return self._fail(record, "UNEXPECTED_PHASE5_FAILURE")
        with self._lock:
            record.update(result)
            if record.get("status") not in {
                "FAILED", "CANCELLED", "BASE_REGEN_REQUIRED", "REVIEW_REQUIRED", "REJECTED_INVALID_INPUT"
            }:
                record["status"] = "COMPLETED"
            record["updatedAt"] = _now()
            self._save(record)
            return record

    def recover_orphaned(self, *, max_runtime_seconds: int) -> list[dict[str, Any]]:
        now = time.time()
        recovered: list[dict[str, Any]] = []
        jobs_dir = self.artifact_root / "jobs"
        for path in sorted(jobs_dir.glob("*.json")) if jobs_dir.is_dir() else ():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") != "RUNNING":
                continue
            started = _parse_time(record.get("startedAt"))
            if started is not None and now - started > max_runtime_seconds:
                record.update({"status": "ORPHANED", "updatedAt": _now(), "error": "ORPHANED_JOB_RECOVERED"})
                self._save(record)
                recovered.append(record)
        return recovered

    def _execute(self, request: CandidateV3JobRequest, record: dict[str, Any]) -> dict[str, Any]:
        pack = self._load_pack(request.identity_pack_id)
        binding = self.scenario_resolver(request.scenario_id)
        if not binding:
            return {"status": "FAILED", "error": "MISSING_SCENARIO_AUTHORITY_BINDING", "route": None}
        observation = self.observability.observe(request.image_bytes, request.editable_mask_bytes)
        route = evaluate_candidate_v3_route(observation, load_candidate_v3_route_policy())
        self._write_json(request, "observability.json", observation.as_dict())
        self._write_json(request, "route.json", route.as_dict())
        record["route"] = route.route_code
        record["routeReasons"] = list(route.reasons)
        if route.route_code != "ELIGIBLE":
            return {"status": route.route_code, "observability": observation.as_dict()}
        canonical = self.transform_service.canonicalize(
            observation=observation,
            route_result=route,
            image_bytes=request.image_bytes,
            editable_mask_bytes=request.editable_mask_bytes,
            feather_mask_bytes=request.feather_mask_bytes,
        )
        canonical_refs = self._persist_canonical(request, canonical)
        selected = tuple(pack.references)
        if not selected:
            raise CandidateV3ServiceError("IDENTITY_PACK_HAS_NO_REFERENCES")
        refs = tuple(
            ArtifactRef(reference.artifact_path, reference.artifact_sha256, 1, 1, "image/png")
            for reference in selected
        )
        bridge_request = CandidateV3Request(
            contract_version="1.0",
            run_id=request.run_id,
            attempt_id=request.attempt_id,
            canonical_image=canonical_refs[0],
            canonical_editable_mask=canonical_refs[1],
            canonical_feather_mask=canonical_refs[2],
            transform=canonical.transform,
            selected_identity_references=refs,
            candidate_profile_id=request.candidate_profile_id,
            seed=request.seed,
            effective_config_sha256=request.effective_config_sha256,
            timeout_seconds=request.timeout_seconds,
        )
        if request.job_id in self._cancelled:
            return {"status": "CANCELLED"}
        bridge_result = self.bridge.execute(bridge_request)
        self._validate_bridge_output(bridge_result, expected_workflow_sha256=self.expected_workflow_sha256)
        composite = inverse_composite_candidate_v3(
            base_canvas_png=request.base_canvas_bytes,
            restored_canonical_crop_png=bridge_result.restored_canonical_png,
            canonical_editable_mask_png=canonical.canonical_editable_mask_png,
            canonical_feather_mask_png=canonical.canonical_feather_mask_png,
            full_canvas_editable_mask_png=request.editable_mask_bytes,
            transform=canonical.transform,
        )
        correctness = evaluate_correctness_qc(
            transform=canonical.transform,
            composite=composite,
            full_canvas_editable_mask_png=request.editable_mask_bytes,
            lineage_valid=bool(bridge_result.lineage),
        )
        boundary = evaluate_boundary_qc(
            before_canvas_png=request.base_canvas_bytes,
            final_composite_png=composite.final_composite_png,
            full_canvas_editable_mask_png=request.editable_mask_bytes,
        )
        face_score = self.face_qc(canonical.canonical_image_png, tuple(ref.reference_id for ref in selected)) if self.face_qc else None
        report_refs: dict[str, dict[str, Any]] = {}
        face_report = {"scope": "FACE_LOCAL", "score": face_score, "selectedReferenceIds": [ref.reference_id for ref in selected]}
        report_refs["FACE_LOCAL"] = self._write_report(request, "FACE_LOCAL", face_report)
        face_scope = face_local_qc_candidate_v3(
            canonical_crop_png=canonical.canonical_image_png,
            selected_reference_ids=[ref.reference_id for ref in selected],
            score=face_score,
            authority_ref={"id": request.identity_pack_id, "sha256": pack.sha256},
            report_ref=report_refs["FACE_LOCAL"],
        )
        boundary_report = boundary.as_dict()
        report_refs["BOUNDARY"] = self._write_report(request, "BOUNDARY", boundary_report)
        boundary_scope = self._boundary_scope(boundary, report_refs["BOUNDARY"])
        global_pass = self.scenario_validator(binding, composite.final_composite_png) if self.scenario_validator else None
        global_report = {"scope": "SCENARIO_GLOBAL", "binding": dict(binding), "passed": global_pass}
        report_refs["SCENARIO_GLOBAL"] = self._write_report(request, "SCENARIO_GLOBAL", global_report)
        global_scope = ScopedQcResult(
            "SCENARIO_GLOBAL", "PASS" if global_pass is True else "FAIL" if global_pass is False else "UNVALIDATED",
            "candidate-v3-scenario-global-qc", load_candidate_v3_quality_policy()["policySha256"],
            {"id": str(binding.get("bindingId", request.scenario_id)), "sha256": str(binding.get("sha256", ""))},
            report_refs["SCENARIO_GLOBAL"], {}, (),
            () if global_pass is not None else ("MISSING_SCENARIO_QC_EVIDENCE",),
        )
        merged = QualityBundleMerger.merge((face_scope, boundary_scope, global_scope))
        policy = load_candidate_v3_quality_policy()
        manifest = manifest_1_4_enrichment(report_refs=report_refs, quality_policy_sha256=policy["policySha256"], merged=merged)
        manifest_ref = self._write_report(request, "manifest-1-4", manifest)
        append_qc_history(self.artifact_root / request.run_id / "qc-history.jsonl", {"attemptId": request.attempt_id, "manifest": manifest_ref})
        return {
            "status": "COMPLETED",
            "qualityStatus": merged.status,
            "manifest": manifest_ref,
            "correctness": correctness.as_dict(),
            "qualityScopes": {
                "FACE_LOCAL": face_scope.as_dict(),
                "BOUNDARY": boundary_scope.as_dict(),
                "SCENARIO_GLOBAL": global_scope.as_dict(),
            },
            "quality": merged.as_dict(),
            "preflight": {"status": "PASS", "reasons": []},
            "candidateProfileId": request.candidate_profile_id,
            "identityPackId": request.identity_pack_id,
            "scenarioId": request.scenario_id,
            "lineage": {"route": route.as_dict(), "transform": canonical.as_dict(), "bridge": dict(bridge_result.lineage)},
        }

    def _load_pack(self, identity_pack_id: str) -> IdentityPack:
        try:
            return self.identity_packs.get_approved(identity_pack_id)
        except Exception as exc:
            raise CandidateV3ServiceError("IDENTITY_AUTHORITY_INVALID") from exc

    def _persist_canonical(self, request: CandidateV3JobRequest, result: CanonicalizationResult) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef]:
        image = self._write_bytes(request, "canonical-input.png", result.canonical_image_png)
        editable = self._write_bytes(request, "canonical-editable-mask.png", result.canonical_editable_mask_png)
        feather = self._write_bytes(request, "canonical-feather-mask.png", result.canonical_feather_mask_png)
        return image, editable, feather

    def _write_bytes(self, request: CandidateV3JobRequest, name: str, data: bytes) -> ArtifactRef:
        path = self.artifact_root / request.run_id / request.attempt_id / name
        self._write_raw(path, data)
        try:
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
        except Exception as exc:
            raise CandidateV3ServiceError("ARTIFACT_IMAGE_INVALID") from exc
        return ArtifactRef(str(path), hashlib.sha256(data).hexdigest(), width, height, "image/png")

    @staticmethod
    def _write_raw(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)

    def _write_json(self, request: CandidateV3JobRequest, name: str, payload: Mapping[str, Any]) -> None:
        self._write_raw(
            self.artifact_root / request.run_id / request.attempt_id / name,
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
        )

    def _write_report(self, request: CandidateV3JobRequest, scope: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        path = self.artifact_root / request.run_id / request.attempt_id / "qc" / f"{scope}.json"
        digest = write_immutable_qc_report(path, payload)
        return {"path": str(path), "sha256": digest}

    @staticmethod
    def _boundary_scope(result: BoundaryQcResult, report_ref: Mapping[str, Any]) -> ScopedQcResult:
        return ScopedQcResult(
            "BOUNDARY", result.status, "candidate-v3-boundary-qc", load_candidate_v3_quality_policy()["policySha256"],
            {"id": result.policy_id, "sha256": result.policy_id and load_candidate_v3_quality_policy()["policySha256"]},
            report_ref, {key: float(value) for key, value in {
                "maxChannelSeamDelta": result.max_channel_seam_delta,
                "meanSeamDelta": result.mean_seam_delta,
                "localTextureDiscontinuity": result.local_texture_discontinuity,
            }.items() if value is not None}, (), result.reasons,
        )

    @staticmethod
    def _validate_bridge_output(result: CandidateV3BridgeResult, *, expected_workflow_sha256: str) -> None:
        if not result.lineage:
            raise CandidateV3ServiceError("BRIDGE_LINEAGE_MISSING")
        if result.lineage.get("workflowSha256") != expected_workflow_sha256:
            raise CandidateV3ServiceError("BRIDGE_LINEAGE_MISMATCH")
        try:
            size = Image.open(BytesIO(result.restored_canonical_png)).size
        except Exception as exc:
            raise CandidateV3ServiceError("BRIDGE_OUTPUT_INVALID") from exc
        if size != (512, 512):
            raise CandidateV3ServiceError("BRIDGE_OUTPUT_GEOMETRY_INVALID")

    def _require(self, job_id: str) -> dict[str, Any]:
        record = self.jobs.get(job_id) if self.jobs else None
        if record is None:
            raise CandidateV3ServiceError("JOB_NOT_FOUND")
        return record

    def _save(self, record: dict[str, Any]) -> None:
        if self.jobs is None:
            raise CandidateV3ServiceError("JOB_STORE_UNAVAILABLE")
        self.jobs.save(record)

    def _fail(self, record: dict[str, Any], reason: str) -> dict[str, Any]:
        record.update({"status": "FAILED", "error": reason, "updatedAt": _now()})
        self._save(record)
        return record


class CandidateV3ApiBoundary:
    """Authenticated, redacted API façade with controlled actions only."""

    def __init__(self, service: CandidateV3RestorationService, *, token: str) -> None:
        self._service = service
        self._token = token

    def handle(self, action: str, payload: Mapping[str, Any], *, authorization: str | None) -> dict[str, Any]:
        if not authorization or not secrets.compare_digest(authorization, f"Bearer {self._token}"):
            raise CandidateV3ServiceError("UNAUTHORIZED")
        if action == "submit":
            result = self._service.submit(payload["request"])
        elif action == "run":
            result = self._service.run(str(payload["jobId"]))
        elif action == "cancel":
            result = self._service.cancel(str(payload["jobId"]))
        elif action == "retry":
            result = self._service.retry(str(payload["jobId"]), attempt_id=str(payload["attemptId"]))
        elif action == "approve":
            raise CandidateV3ServiceError("PRODUCTION_PROMOTION_NOT_AUTHORIZED")
        else:
            raise CandidateV3ServiceError("UNKNOWN_ACTION")
        return self._redact(result)

    @staticmethod
    def _redact(result: Mapping[str, Any]) -> dict[str, Any]:
        from ..interface.candidate_v3_frontend import redact_candidate_v3_client_result

        return redact_candidate_v3_client_result(result)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None
