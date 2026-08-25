from __future__ import annotations

"""Small benchmark-executor primitives that do not create a second pipeline."""

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from PIL import Image

from .benchmark_runner import BenchmarkExecutionError
from .dto.restore_command import RestoreCommand
from .dto.restoration_result import RestorationResult
from .ports.worker_health import WorkerHealthPort, WorkerStatus
from .use_cases.restore_face_crop import RestoreFaceCropUseCase
from .benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_REMOTE_PARAMS,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
)


REQUIRED_EVIDENCE_KEYS = (
    "outputPath",
    "outputSha256",
    "executorStatus",
    "error",
    "provider",
    "providerRequestId",
    "providerRunId",
    "backend",
    "host",
)

LOCAL_EVIDENCE_KEYS = REQUIRED_EVIDENCE_KEYS + (
    "a2Path", "cropTransform", "maskVersion", "maskSha256", "lineage",
    "restoredCropPath", "restoredCropSha256",
)
REMOTE_EVIDENCE_KEYS = LOCAL_EVIDENCE_KEYS
NANO_BANANA_EVIDENCE_KEYS = REQUIRED_EVIDENCE_KEYS + (
    "operation", "model", "seedSupported", "lineage", "evidencePath",
)


@dataclass(frozen=True)
class NanoBananaEditRequest:
    """Already-resolved request for the existing Nano Banana masked-edit path.

    The benchmark boundary does not crop, resize, build masks, or construct a
    provider request. ``request_factory`` is the composition seam to the
    existing action-composite/Nano Banana path and must return its resolved
    base, A2, mask, and transform lineage.
    """

    base_path: Path
    a2_path: Path
    mask_path: Path | None
    crop_transform: Mapping[str, Any] | None
    mask_version: str | None
    seed_supported: bool
    operation: str = "masked_edit"
    lineage: Mapping[str, Any] | None = None
    geometry_authority_path: Path | None = None


@dataclass(frozen=True)
class NanoBananaEditResult:
    """Sanitized result returned by the existing provider path.

    Raw SDK responses and credentials never cross this boundary. The adapter
    supplies only sanitized provider metadata and explicit fallback flags.
    """

    image_bytes: bytes
    provider_id: str
    model_id: str
    provider_request_id: str | None
    provider_run_id: str | None
    runtime_ms: int
    retry_count: int
    seed_supported: bool
    backend: str | None
    host: Mapping[str, Any] | None
    mock_used: bool
    local_fallback: bool
    silent_fallback: bool
    provider_metadata: Mapping[str, Any] | None = None


class NanoBananaEditPort(Protocol):
    """Port implemented by the existing Nano Banana/action-composite path."""

    def masked_edit(
        self, request: NanoBananaEditRequest, *, run_id: str, attempt_id: str
    ) -> NanoBananaEditResult:
        ...

    def capabilities(self) -> Mapping[str, Any]:
        ...


@dataclass
class NanoBananaEditBenchmarkExecutor:
    """Benchmark adapter around the existing Nano Banana masked-edit path.

    This class owns authority checks, result validation, and evidence writing
    only. It deliberately has no Gemini SDK, image-generation logic, retry
    logic, crop/mask algorithm, or fallback provider. A production composition
    root must inject the existing provider path through ``edit_path``.
    """

    edit_path: NanoBananaEditPort
    request_factory: Callable[[Mapping[str, Any], str, str, int], NanoBananaEditRequest]
    repo_root: Path | None = None
    canonical_a2_path: Path | None = None
    evidence_root: Path | None = None
    restorer_id: str = "nano-banana-edit"
    reusable_evidence: Mapping[str, Path] | None = None

    def capabilities(self) -> Mapping[str, Mapping[str, Any]]:
        capability = self.edit_path.capabilities()
        if not isinstance(capability, Mapping):
            return {"nano-banana-edit": self._blocked_capability("provider capability response is malformed")}
        provider_ready = bool(capability.get("ready", False))
        blockers = [str(item) for item in capability.get("blockers", ())]
        if not capability.get("providerConfigured", False):
            blockers.append("Nano Banana provider configuration is unavailable")
        if capability.get("fallbackEnabled", False):
            blockers.append("Nano Banana fallback path is enabled")
        if self.evidence_root is None:
            blockers.append("Nano Banana evidence_root is not configured")
        return {
            "nano-banana-edit": {
                "executorPath": f"{__name__}.NanoBananaEditBenchmarkExecutor",
                "adapterPath": capability.get(
                    "adapterPath", "existing Nano Banana/action-composite production path"
                ),
                "registered": True,
                "physicalCallable": provider_ready and not blockers,
                "evidenceWriter": self.evidence_root is not None,
                "evidenceFields": list(NANO_BANANA_EVIDENCE_KEYS),
                "provider": capability.get("provider", "nano-banana-2"),
                "model": capability.get("model", "gemini-3.1-flash-image"),
                "providerConfigured": bool(capability.get("providerConfigured", False)),
                "fallbackEnabled": bool(capability.get("fallbackEnabled", False)),
                "productionPathReused": bool(capability.get("productionPathReused", False)),
                "ready": provider_ready and not blockers,
                "blockers": list(dict.fromkeys(blockers)),
                "bootstrapSmokeAllowed": False,
            }
        }

    @staticmethod
    def _blocked_capability(reason: str) -> dict[str, Any]:
        return {
            "executorPath": f"{__name__}.NanoBananaEditBenchmarkExecutor",
            "registered": True,
            "physicalCallable": False,
            "evidenceWriter": False,
            "evidenceFields": list(NANO_BANANA_EVIDENCE_KEYS),
            "ready": False,
            "blockers": [reason],
            "bootstrapSmokeAllowed": False,
        }

    def execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        if branch != self.restorer_id:
            raise BenchmarkExecutionError(
                f"Nano Banana executor cannot execute branch {branch!r}; no branch substitution is allowed"
            )
        if seed != 42:
            raise BenchmarkExecutionError("Nano Banana benchmark seed must be exactly 42")
        reused = self._reuse_existing_evidence(case)
        if reused is not None:
            return reused
        base_path, base_sha = _base_frame(case, self.repo_root)
        actual_base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
        if actual_base_sha != base_sha:
            raise BenchmarkExecutionError(
                f"Nano Banana base frame SHA-256 mismatch: expected {base_sha}, got {actual_base_sha}"
            )
        if self.canonical_a2_path is None or not self.canonical_a2_path.is_file():
            raise BenchmarkExecutionError("Nano Banana canonical A2 path is missing")
        a2_sha = hashlib.sha256(self.canonical_a2_path.read_bytes()).hexdigest()
        if a2_sha != EXPECTED_A2_SHA256:
            raise BenchmarkExecutionError(
                f"Nano Banana A2 SHA-256 mismatch: expected {EXPECTED_A2_SHA256}, got {a2_sha}"
            )
        if self.evidence_root is None:
            raise BenchmarkExecutionError("Nano Banana evidence_root is not configured")

        try:
            request = self.request_factory(case, run_id, attempt_id, seed)
        except Exception as exc:
            raise BenchmarkExecutionError(f"Nano Banana request construction failed: {exc}") from exc
        self._validate_request(request, base_path=base_path, a2_path=self.canonical_a2_path, seed=seed)

        try:
            result = self.edit_path.masked_edit(request, run_id=run_id, attempt_id=attempt_id)
        except Exception as exc:
            self._write_failure(run_id, attempt_id, {"status": "FAILED", "error": str(exc)})
            raise BenchmarkExecutionError(f"Nano Banana provider execution failed: {exc}") from exc
        if not isinstance(result, NanoBananaEditResult):
            self._write_failure(run_id, attempt_id, {"status": "FAILED", "error": "malformed provider result"})
            raise BenchmarkExecutionError("Nano Banana provider returned a malformed result")
        if result.mock_used or result.local_fallback or result.silent_fallback:
            raise BenchmarkExecutionError("Nano Banana provider result indicates mock or fallback use")
        if result.provider_id != "nano-banana-2":
            raise BenchmarkExecutionError(
                f"unexpected Nano Banana provider {result.provider_id!r}; provider substitution is forbidden"
            )
        if not result.model_id:
            raise BenchmarkExecutionError("Nano Banana provider result has no model identifier")
        if result.runtime_ms < 0 or result.retry_count < 0:
            raise BenchmarkExecutionError("Nano Banana provider runtime/retry evidence is malformed")
        if not isinstance(result.seed_supported, bool):
            raise BenchmarkExecutionError("Nano Banana seedSupported evidence is malformed")
        output_sha = _verified_image_bytes_sha(result.image_bytes, "Nano Banana output")
        if output_sha == actual_base_sha:
            raise BenchmarkExecutionError("Nano Banana output is byte-identical to the frozen base frame")

        artifact_dir = self.evidence_root / run_id / attempt_id
        artifact_dir.mkdir(parents=True, exist_ok=False)
        output_path = artifact_dir / "output.png"
        output_path.write_bytes(result.image_bytes)
        evidence = {
            "faceQcBefore": None,
            "faceQcAfter": None,
            "identityScore": None,
            "eyesBrowsScore": None,
            "geometryScore": None,
            "anatomyScore": None,
            "outfitScore": None,
            "environmentScore": None,
            "globalScore": None,
            "pixelPreservationResult": "UNKNOWN",
            "runtimeMs": result.runtime_ms,
            "retryCount": result.retry_count,
            "workflowId": None,
            "workflowSha256": None,
            "gpuName": None,
            "vramPeakMb": None,
            "outputPath": str(output_path),
            "outputSha256": output_sha,
            "executorStatus": "COMPLETED",
            "error": None,
            "provider": result.provider_id,
            "providerRequestId": result.provider_request_id,
            "providerRunId": result.provider_run_id,
            "backend": result.backend,
            "host": dict(result.host) if result.host is not None else None,
            "operation": request.operation,
            "model": result.model_id,
            "seedSupported": result.seed_supported,
            "evidencePath": str(artifact_dir / "evidence.json"),
            "lineage": {
                "baseFramePath": str(base_path),
                "baseFrameSha256": base_sha,
                "a2Path": str(self.canonical_a2_path),
                "a2Sha256": a2_sha,
                "maskPath": str(request.mask_path) if request.mask_path else None,
                "maskVersion": request.mask_version,
                "cropTransform": dict(request.crop_transform) if request.crop_transform else None,
                "operation": request.operation,
                "providerMetadata": dict(result.provider_metadata or {}),
                "requestLineage": dict(request.lineage or {}),
                "mock_used": False,
                "local_fallback": False,
                "silent_fallback": False,
            },
        }
        (artifact_dir / "evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return evidence

    def _reuse_existing_evidence(self, case: Mapping[str, Any]) -> dict[str, Any] | None:
        """Reuse a verified prior provider artifact without recalling Nano."""
        if not self.reusable_evidence:
            return None
        evidence_path = self.reusable_evidence.get(str(case.get("id")))
        if evidence_path is None:
            return None
        payload = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        output_path = Path(str(payload.get("outputPath", "")))
        expected_sha = str(payload.get("outputSha256", ""))
        if payload.get("executorStatus") != "COMPLETED" or not output_path.is_file():
            raise BenchmarkExecutionError("reusable Nano Banana artifact is incomplete")
        actual_sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise BenchmarkExecutionError("reusable Nano Banana artifact SHA-256 mismatch")
        if payload.get("provider") != "nano-banana-2" or payload.get("model") != "gemini-3.1-flash-image":
            raise BenchmarkExecutionError("reusable Nano Banana artifact provider authority mismatch")
        lineage = dict(payload.get("lineage") or {})
        source_path = Path(evidence_path).resolve()
        source_attempt_id = source_path.parent.name
        source_run_id = source_path.parent.parent.name
        lineage["artifactReuse"] = {
            "sourceEvidencePath": str(Path(evidence_path).resolve()),
            "providerCallReused": True,
            "sourceRunId": source_run_id,
            "sourceAttemptId": source_attempt_id,
            "sourceOutputSha256": actual_sha,
            "reuseReason": "verified prior Nano Banana provider artifact; no new paid call",
        }
        return {**payload, "outputPath": str(output_path), "outputSha256": actual_sha, "lineage": lineage}

    @staticmethod
    def _validate_request(
        request: NanoBananaEditRequest, *, base_path: Path, a2_path: Path, seed: int
    ) -> None:
        if not isinstance(request, NanoBananaEditRequest):
            raise BenchmarkExecutionError("Nano Banana request factory returned a malformed request")
        if request.operation != "masked_edit":
            raise BenchmarkExecutionError("Nano Banana benchmark requires the existing masked_edit operation")
        if request.base_path.resolve() != base_path.resolve():
            raise BenchmarkExecutionError("Nano Banana request base is not the frozen benchmark frame")
        if request.a2_path.resolve() != a2_path.resolve():
            raise BenchmarkExecutionError("Nano Banana request A2 is not the canonical A2 authority")
        if request.mask_path is None:
            raise BenchmarkExecutionError("Nano Banana masked_edit request has no frozen full-canvas mask")
        if request.geometry_authority_path is None or not request.geometry_authority_path.is_file():
            raise BenchmarkExecutionError("Nano Banana request has no frozen geometry authority")
        try:
            from .benchmark_geometry import load_b01_geometry_authority, _verify_mask
            authority = load_b01_geometry_authority(request.geometry_authority_path)
            source_sha = authority.get("sourceSha256", authority.get("sourceB01Sha256"))
            if source_sha != hashlib.sha256(base_path.read_bytes()).hexdigest():
                raise ValueError("geometry authority B01 SHA mismatch")
            if authority.get("a2AuthoritySha256") != EXPECTED_A2_SHA256:
                raise ValueError("geometry authority A2 SHA mismatch")
            full = authority.get("fullCanvasMask")
            crop = authority.get("cropLocalMask")
            if not isinstance(full, Mapping) or not isinstance(crop, Mapping):
                raise ValueError("geometry authority lacks required masks")
            if Path(str(full.get("path"))).resolve() != request.mask_path.resolve():
                raise ValueError("request mask is not the frozen full-canvas mask")
            with Image.open(base_path) as base_image:
                _verify_mask(request.mask_path, full, expected_size=base_image.size, coordinate_space="full-canvas")
            transform = request.crop_transform
            if not isinstance(transform, Mapping):
                raise ValueError("geometry authority cropTransform is missing")
            crop_path = Path(str(crop.get("path", "")))
            crop_size = (
                int(transform["right"]) - int(transform["left"]),
                int(transform["bottom"]) - int(transform["top"]),
            )
            _verify_mask(crop_path, crop, expected_size=crop_size, coordinate_space="crop-local")
        except Exception as exc:
            raise BenchmarkExecutionError(f"Nano Banana frozen geometry validation failed: {exc}") from exc
        if not isinstance(request.seed_supported, bool):
            raise BenchmarkExecutionError("Nano Banana request seedSupported is malformed")
        if seed != 42:
            raise BenchmarkExecutionError("Nano Banana request seed does not match 42")

    def _write_failure(self, run_id: str, attempt_id: str, payload: Mapping[str, Any]) -> None:
        if self.evidence_root is None:
            return
        artifact_dir = self.evidence_root / run_id / attempt_id
        artifact_dir.mkdir(parents=True, exist_ok=False)
        (artifact_dir / "failure.json").write_text(
            json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


@dataclass(frozen=True)
class ControlBenchmarkExecutor:
    """The no-restoration control branch.

    It verifies and references the frozen source bytes in place; it never
    copies or mutates the benchmark artifact and performs no provider call.
    Other branches are intentionally rejected because this executor is not a
    substitute for their physical adapters.
    """

    repo_root: Path

    def capabilities(self) -> Mapping[str, Mapping[str, Any]]:
        return {
            "control": {
                "executorPath": f"{__name__}.ControlBenchmarkExecutor",
                "physicalCallable": True,
                "evidenceWriter": True,
                "evidenceFields": list(REQUIRED_EVIDENCE_KEYS),
                "ready": True,
                "blockers": [],
            }
        }

    def execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        if branch != "control":
            raise BenchmarkExecutionError(
                f"control executor cannot execute branch {branch!r}; no branch substitution is allowed"
            )
        frame = case.get("baseFrame")
        if not isinstance(frame, Mapping) or not isinstance(frame.get("path"), str):
            raise BenchmarkExecutionError("control source baseFrame.path is missing")
        path = Path(frame["path"])
        if not path.is_absolute():
            path = self.repo_root / path
        if not path.is_file():
            raise BenchmarkExecutionError(f"control source is missing: {path}")
        output_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if output_sha != frame.get("sha256"):
            raise BenchmarkExecutionError(
                f"control source SHA-256 mismatch: expected {frame.get('sha256')}, got {output_sha}"
            )
        return {
            "faceQcBefore": None,
            "faceQcAfter": None,
            "identityScore": None,
            "eyesBrowsScore": None,
            "geometryScore": None,
            "anatomyScore": None,
            "outfitScore": None,
            "environmentScore": None,
            "globalScore": None,
            "pixelPreservationResult": "PASS",
            "runtimeMs": 0,
            "retryCount": 0,
            "workflowId": None,
            "workflowSha256": None,
            "gpuName": None,
            "vramPeakMb": None,
            "outputPath": str(path),
            "outputSha256": output_sha,
            "executorStatus": "COMPLETED",
            "error": None,
            "provider": None,
            "providerRequestId": None,
            "providerRunId": None,
            "backend": "control",
            "host": {"attemptId": attempt_id, "seed": seed},
        }


@dataclass
class ComfyUILocalBenchmarkExecutor:
    """Benchmark boundary around the existing local restoration use case.

    The executor owns only benchmark request/evidence adaptation. Restoration,
    A2 loading, compositing, pixel preservation, ledger writes, and the
    IdentityRestorerPort call remain in ``RestoreFaceCropUseCase``.
    ``request_factory`` is injected by the existing composition path so this
    class never re-crops images or rebuilds masks.
    """

    use_case: RestoreFaceCropUseCase
    request_factory: Callable[[Mapping[str, Any], str, str, int], RestoreCommand]
    repo_root: Path | None = None
    restorer_id: str = "comfyui-local"

    def capabilities(self) -> Mapping[str, Mapping[str, Any]]:
        return {
            "comfyui-local": {
                "executorPath": f"{__name__}.ComfyUILocalBenchmarkExecutor",
                "adapterPath": "identity_restoration.infrastructure.restorers.comfyui_local_restorer.ComfyUILocalRestorer",
                "physicalCallable": True,
                "evidenceWriter": True,
                "evidenceFields": list(LOCAL_EVIDENCE_KEYS),
                "ready": True,
                "blockers": [],
            }
        }

    def execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        if branch != self.restorer_id:
            raise BenchmarkExecutionError(
                f"local executor cannot execute branch {branch!r}; no branch substitution is allowed"
            )
        base_path, base_sha = _base_frame(case, self.repo_root)
        actual_base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
        if actual_base_sha != base_sha:
            raise BenchmarkExecutionError(
                f"base frame SHA-256 mismatch: expected {base_sha}, got {actual_base_sha}"
            )

        try:
            command = self.request_factory(case, run_id, attempt_id, seed)
        except Exception as exc:
            raise BenchmarkExecutionError(f"local benchmark request construction failed: {exc}") from exc
        _validate_port_request(
            command,
            seed=seed,
            restorer_id="comfyui-local",
            workflow_id=None,
            workflow_sha256=None,
            params=None,
        )

        try:
            result = self.use_case.execute(command)
        except Exception as exc:
            raise BenchmarkExecutionError(f"local restoration execution raised: {exc}") from exc
        if not isinstance(result, RestorationResult):
            raise BenchmarkExecutionError("local restoration returned a malformed result object")
        if result.status in {"FAILED", "REJECTED", "CANCELLED"} or result.error is not None:
            detail = result.error.message if result.error is not None else result.status
            raise BenchmarkExecutionError(f"local restoration failed: {detail}")
        if result.composite_path is None:
            raise BenchmarkExecutionError("local restoration result has no composite output path")
        output_path = Path(result.composite_path)
        output_sha = _verified_image_sha(output_path, "composite output")
        restored_path = Path(result.restored_crop_path) if result.restored_crop_path else None
        restored_sha = _verified_image_sha(restored_path, "restored crop") if restored_path else None
        if result.pixel_lock is None:
            raise BenchmarkExecutionError("local restoration result has no pixel-preservation evidence")
        if not result.pixel_lock.passed:
            raise BenchmarkExecutionError("local restoration pixel-preservation evidence failed")

        lineage = dict(result.lineage)
        workflow_id = lineage.get("workflowId")
        workflow_sha = lineage.get("workflowSha256")
        if not isinstance(workflow_id, str) or not isinstance(workflow_sha, str):
            raise BenchmarkExecutionError("local restoration lineage lacks workflow identity/hash")
        crop = command.crop_transform
        return {
            "faceQcBefore": None,
            "faceQcAfter": None,
            "identityScore": None,
            "eyesBrowsScore": None,
            "geometryScore": None,
            "anatomyScore": None,
            "outfitScore": None,
            "environmentScore": None,
            "globalScore": None,
            "pixelPreservationResult": "PASS",
            "runtimeMs": int(lineage.get("runtimeMs", 0)),
            "retryCount": 0,
            "workflowId": workflow_id,
            "workflowSha256": workflow_sha,
            "gpuName": None,
            "vramPeakMb": None,
            "outputPath": str(output_path),
            "outputSha256": output_sha,
            "executorStatus": "COMPLETED",
            "error": None,
            "provider": "comfyui-local",
            "providerRequestId": None,
            "providerRunId": run_id,
            "backend": "comfyui-local",
            "host": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "attemptId": attempt_id,
                "restorationStatus": result.status,
            },
            "a2Path": command.a2_path,
            "cropTransform": {
                "box": list(crop.to_box()),
                "targetSize": crop.target_size,
            },
            "maskVersion": command.mask.version,
            "maskSha256": hashlib.sha256(command.mask.editable).hexdigest(),
            "restoredCropPath": str(restored_path) if restored_path else None,
            "restoredCropSha256": restored_sha,
            "lineage": {
                "baseFramePath": str(base_path),
                "baseFrameSha256": base_sha,
                "a2Sha256": command.a2_sha256,
                "geometryBackend": command.geometry_backend,
                "geometryModel": command.geometry_model,
                "geometryModelSha256": command.geometry_model_sha256,
                "fullCanvasMaskVersion": command.full_canvas_mask.version,
                "fullCanvasMaskSha256": hashlib.sha256(command.full_canvas_mask.editable).hexdigest(),
                "restoration": lineage,
            },
        }



@dataclass
class ComfyUIRemoteBenchmarkExecutor:
    """Benchmark boundary around the existing remote IdentityRestorerPort.

    This class deliberately contains no ComfyUI client, upload, polling, or
    download code. Those operations remain in ``ComfyUIRemoteRestorer``;
    ``RestoreFaceCropUseCase`` remains the only application execution path.
    ``physical_smoke_evidence`` is mandatory before the capability reports
    READY, so offline structural tests cannot accidentally authorize a run.
    """

    use_case: RestoreFaceCropUseCase
    request_factory: Callable[[Mapping[str, Any], str, str, int], RestoreCommand]
    repo_root: Path | None = None
    physical_smoke_evidence: Path | None = None
    health: WorkerHealthPort | None = None
    restorer_id: str = "comfyui-remote"
    evidence_root: Path | None = None
    memory_release: Callable[[], Mapping[str, Any]] | None = None
    reusable_evidence: Mapping[str, Mapping[str, Any]] | None = None

    def capabilities(self) -> Mapping[str, Mapping[str, Any]]:
        verified, reason = _physical_smoke_status(self.physical_smoke_evidence)
        blockers = [] if verified else [reason]
        if self.health is None:
            blockers.append("remote WorkerHealthPort is not configured")
        return {
            "comfyui-remote": {
                "executorPath": f"{__name__}.ComfyUIRemoteBenchmarkExecutor",
                "adapterPath": (
                    "identity_restoration.infrastructure.restorers."
                    "comfyui_remote_restorer.ComfyUIRemoteRestorer"
                ),
                "registered": True,
                "physicalCallable": True,
                "evidenceWriter": True,
                "evidenceFields": list(REMOTE_EVIDENCE_KEYS),
                "ready": verified and self.health is not None,
                "bootstrapSmokeAllowed": self.physical_smoke_evidence is None and self.health is not None,
                "blockers": blockers,
                "physicalSmokeEvidence": str(self.physical_smoke_evidence)
                if self.physical_smoke_evidence else None,
            }
        }

    def execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        """Execute an official benchmark attempt only after smoke evidence."""
        return self._execute(
            case=case, branch=branch, run_id=run_id, attempt_id=attempt_id,
            seed=seed, bootstrap=False,
        )

    def execute_bootstrap_smoke(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
    ) -> Mapping[str, Any]:
        """Run exactly one non-benchmark bootstrap smoke.

        This is the only path allowed to execute without an existing smoke
        evidence file. It still validates the live health port and every
        frozen request authority, and writes a dedicated evidence manifest.
        """
        if self.physical_smoke_evidence is not None:
            raise BenchmarkExecutionError(
                "bootstrap smoke cannot run with an existing smoke evidence file"
            )
        if branch != "comfyui-remote" or case.get("id") != "B01":
            raise BenchmarkExecutionError("bootstrap smoke is restricted to comfyui-remote case B01")
        if self.evidence_root is None:
            raise BenchmarkExecutionError("bootstrap smoke evidence_root is not configured")
        evidence = self._execute(
            case=case, branch=branch, run_id=run_id, attempt_id=attempt_id,
            seed=seed, bootstrap=True,
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        smoke_dir = self.evidence_root / f"gw-p4-t0-5-2d-{timestamp}-{uuid4().hex[:8]}"
        smoke_dir.mkdir(parents=True, exist_ok=False)
        lineage = evidence.get("lineage") if isinstance(evidence.get("lineage"), Mapping) else {}
        restoration = lineage.get("restoration") if isinstance(lineage.get("restoration"), Mapping) else {}
        smoke_manifest = {
            "evidenceType": "NON_BENCHMARK",
            "phase": "PREFLIGHT",
            "bootstrapSmokeAllowed": True,
            "branch": branch,
            "caseId": case.get("id"),
            "runId": run_id,
            "attemptId": attempt_id,
            "status": "PASS",
            "mock_used": False,
            "local_fallback": False,
            "silent_fallback": False,
            "pixelPreservationResult": evidence.get("pixelPreservationResult"),
            "sourceSha256": lineage.get("baseFrameSha256"),
            "a2Sha256": lineage.get("a2Sha256"),
            "workflowSha256": evidence.get("workflowSha256"),
            "outputSha256": evidence.get("outputSha256"),
            "promptId": evidence.get("providerRequestId"),
            "restorationLineage": restoration,
            "evidence": dict(evidence),
        }
        manifest_path = smoke_dir / "smoke_manifest.json"
        manifest_path.write_text(
            json.dumps(smoke_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {**evidence, "smokeEvidencePath": str(manifest_path)}

    def _execute(
        self,
        *,
        case: Mapping[str, Any],
        branch: str,
        run_id: str,
        attempt_id: str,
        seed: int,
        bootstrap: bool,
    ) -> Mapping[str, Any]:
        if branch != self.restorer_id:
            raise BenchmarkExecutionError(
                f"remote executor cannot execute branch {branch!r}; no branch substitution is allowed"
            )
        reused = self._reuse_existing_evidence(case)
        if reused is not None:
            return reused
        if not bootstrap:
            verified, reason = _physical_smoke_status(self.physical_smoke_evidence)
            if not verified:
                raise BenchmarkExecutionError(reason)
        if self.health is None:
            raise BenchmarkExecutionError("remote WorkerHealthPort is not configured")
        recovery_events: list[dict[str, Any]] = []
        try:
            health = self.health.probe()
        except Exception as exc:
            raise BenchmarkExecutionError(f"remote worker health probe failed: {exc}") from exc
        if (
            health.status is WorkerStatus.DEGRADED
            and health.vram_free_mb is not None
            and health.vram_free_mb < 4200
        ):
            if self.memory_release is None:
                raise BenchmarkExecutionError(
                    "remote worker health is DEGRADED; memory release is not configured"
                )
            try:
                release_response = self.memory_release()
                invalidate = getattr(self.health, "invalidate", None)
                if callable(invalidate):
                    invalidate()
                recovery_events.append({
                    "action": "/free",
                    "unloadModels": True,
                    "freeMemory": True,
                    "response": dict(release_response),
                    "beforeVramFreeMb": health.vram_free_mb,
                })
                health = self.health.probe()
            except Exception as exc:
                raise BenchmarkExecutionError(f"remote worker VRAM recovery failed: {exc}") from exc
        if health.status is not WorkerStatus.HEALTHY:
            raise BenchmarkExecutionError(
                f"remote worker health is {health.status.value}; physical execution is blocked"
                + (f"; vramRecovery={json.dumps(recovery_events, sort_keys=True)}" if recovery_events else "")
            )
        base_path, base_sha = _base_frame(case, self.repo_root)
        actual_base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
        if actual_base_sha != base_sha:
            raise BenchmarkExecutionError(
                f"base frame SHA-256 mismatch: expected {base_sha}, got {actual_base_sha}"
            )
        try:
            command = self.request_factory(case, run_id, attempt_id, seed)
        except Exception as exc:
            raise BenchmarkExecutionError(f"remote benchmark request construction failed: {exc}") from exc
        _validate_port_request(
            command,
            seed=seed,
            restorer_id="comfyui-remote",
            workflow_id=EXPECTED_WORKFLOW_ID,
            workflow_sha256=EXPECTED_WORKFLOW_SHA256,
            params=EXPECTED_REMOTE_PARAMS,
        )

        try:
            result = self.use_case.execute(command)
        except Exception as exc:
            raise BenchmarkExecutionError(f"remote restoration execution raised: {exc}") from exc
        if not isinstance(result, RestorationResult):
            raise BenchmarkExecutionError("remote restoration returned a malformed result object")
        if result.status in {"FAILED", "REJECTED", "CANCELLED"} or result.error is not None:
            detail = result.error.message if result.error is not None else result.status
            raise BenchmarkExecutionError(f"remote restoration failed: {detail}")
        if result.composite_path is None:
            raise BenchmarkExecutionError("remote restoration result has no composite output path")
        output_path = Path(result.composite_path)
        output_sha = _verified_image_sha(output_path, "remote composite output")
        restored_path = Path(result.restored_crop_path) if result.restored_crop_path else None
        restored_sha = _verified_image_sha(restored_path, "remote restored crop") if restored_path else None
        input_sha = hashlib.sha256(command.crop_png).hexdigest()
        if restored_sha is None or restored_sha == input_sha:
            raise BenchmarkExecutionError(
                "remote restored crop is byte-identical to the input crop or missing"
            )
        if result.pixel_lock is None:
            raise BenchmarkExecutionError("remote restoration result has no pixel-preservation evidence")
        if not result.pixel_lock.passed:
            raise BenchmarkExecutionError("remote restoration pixel-preservation evidence failed")
        lineage = dict(result.lineage)
        if recovery_events:
            recovery_events[-1]["afterVramFreeMb"] = health.vram_free_mb
            lineage["vramRecovery"] = recovery_events
        workflow_id = lineage.get("workflowId")
        workflow_sha = lineage.get("workflowSha256")
        if workflow_id != EXPECTED_WORKFLOW_ID or workflow_sha != EXPECTED_WORKFLOW_SHA256:
            raise BenchmarkExecutionError("remote restoration lineage does not match the frozen workflow authority")
        crop = command.crop_transform
        worker_health = lineage.get("workerHealth")
        if not isinstance(worker_health, Mapping):
            worker_health = {}
        host = {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "attemptId": attempt_id,
            "restorationStatus": result.status,
            "remoteHost": lineage.get("remoteHost"),
            "remoteHealth": worker_health,
        }
        return {
            "faceQcBefore": None,
            "faceQcAfter": None,
            "identityScore": None,
            "eyesBrowsScore": None,
            "geometryScore": None,
            "anatomyScore": None,
            "outfitScore": None,
            "environmentScore": None,
            "globalScore": None,
            "pixelPreservationResult": "PASS",
            "runtimeMs": int(lineage.get("runtimeMs", 0)),
            "retryCount": 0,
            "workflowId": workflow_id,
            "workflowSha256": workflow_sha,
            "gpuName": lineage.get("gpuName") or worker_health.get("gpuName"),
            "vramPeakMb": lineage.get("vramPeakMb"),
            "outputPath": str(output_path),
            "outputSha256": output_sha,
            "executorStatus": "COMPLETED",
            "error": None,
            "provider": "comfyui-remote",
            "providerRequestId": lineage.get("promptId"),
            "providerRunId": run_id,
            "backend": "comfyui-remote",
            "host": host,
            "a2Path": command.a2_path,
            "cropTransform": {"box": list(crop.to_box()), "targetSize": crop.target_size},
            "maskVersion": command.mask.version,
            "maskSha256": hashlib.sha256(command.mask.editable).hexdigest(),
            "restoredCropPath": str(restored_path),
            "restoredCropSha256": restored_sha,
            "lineage": {
                "baseFramePath": str(base_path),
                "baseFrameSha256": base_sha,
                "a2Sha256": command.a2_sha256,
                "geometryBackend": command.geometry_backend,
                "geometryModel": command.geometry_model,
                "geometryModelSha256": command.geometry_model_sha256,
                "fullCanvasMaskVersion": command.full_canvas_mask.version,
                "fullCanvasMaskSha256": hashlib.sha256(command.full_canvas_mask.editable).hexdigest(),
                "restoration": lineage,
            },
        }

    def _reuse_existing_evidence(self, case: Mapping[str, Any]) -> dict[str, Any] | None:
        """Reuse explicitly indexed remote evidence without submitting a prompt."""
        if not self.reusable_evidence:
            return None
        payload = self.reusable_evidence.get(str(case.get("id")))
        if payload is None:
            return None
        output_path = Path(str(payload.get("outputPath", "")))
        expected_sha = str(payload.get("outputSha256", ""))
        if payload.get("executorStatus") != "COMPLETED" or not output_path.is_file():
            raise BenchmarkExecutionError("reusable remote artifact is incomplete")
        if hashlib.sha256(output_path.read_bytes()).hexdigest() != expected_sha:
            raise BenchmarkExecutionError("reusable remote artifact SHA-256 mismatch")
        if payload.get("workflowId") != EXPECTED_WORKFLOW_ID or payload.get("workflowSha256") != EXPECTED_WORKFLOW_SHA256:
            raise BenchmarkExecutionError("reusable remote artifact workflow authority mismatch")
        lineage = dict(payload.get("lineage") or {})
        source_run_id = str(payload.get("runId") or "")
        source_attempt_id = str(payload.get("attemptId") or "")
        if not source_run_id or not source_attempt_id:
            # Prior row evidence does not always persist these fields.  The
            # explicit index supplied by benchmark_module is still rooted in
            # the source run directory, so retain that provenance if present.
            artifact_reuse = dict(lineage.get("artifactReuse") or {})
            source_run_id = str(artifact_reuse.get("sourceRunId") or "")
            source_attempt_id = str(artifact_reuse.get("sourceAttemptId") or "")
        lineage["artifactReuse"] = {
            "providerCallReused": True,
            "sourceRunId": source_run_id or None,
            "sourceAttemptId": source_attempt_id or None,
            "sourceOutputSha256": expected_sha,
            "reuseReason": "verified prior Remote composite artifact; no new GPU job",
        }
        return {**payload, "outputPath": str(output_path), "outputSha256": expected_sha, "lineage": lineage}


def _validate_port_request(
    command: RestoreCommand,
    *,
    seed: int,
    restorer_id: str,
    workflow_id: str | None,
    workflow_sha256: str | None,
    params: Mapping[str, Any] | None,
) -> None:
    if command.restorer_id != restorer_id:
        raise BenchmarkExecutionError(
            f"{restorer_id} request selected unexpected restorerId {command.restorer_id!r}"
        )
    if command.seed != seed or command.seed != 42:
        raise BenchmarkExecutionError(
            f"{restorer_id} request seed {command.seed} does not match frozen benchmark seed 42"
        )
    if command.a2_sha256 != EXPECTED_A2_SHA256:
        raise BenchmarkExecutionError(
            f"{restorer_id} request A2 SHA-256 does not match frozen authority: {command.a2_sha256}"
        )
    if workflow_id is not None and command.workflow_id != workflow_id:
        raise BenchmarkExecutionError("remote request workflow ID does not match frozen authority")
    if params is not None:
        actual = {
            "denoise": command.params.denoise,
            "steps": command.params.steps,
            "cfg": int(command.params.cfg) if command.params.cfg.is_integer() else command.params.cfg,
            "sampler": command.params.sampler,
            "scheduler": command.params.scheduler,
        }
        if actual != dict(params):
            raise BenchmarkExecutionError(
                f"remote request params do not match frozen authority: {actual}"
            )
    try:
        crop = Image.open(BytesIO(command.crop_png))
        mask = Image.open(BytesIO(command.mask.editable))
        full_mask = Image.open(BytesIO(command.full_canvas_mask.editable))
        base = Image.open(BytesIO(command.base_canvas_png))
        if crop.size != mask.size:
            raise BenchmarkExecutionError(f"{restorer_id} crop and crop-local mask dimensions differ")
        if full_mask.size != base.size:
            raise BenchmarkExecutionError(f"{restorer_id} full-canvas mask and base dimensions differ")
    except BenchmarkExecutionError:
        raise
    except Exception as exc:
        raise BenchmarkExecutionError(f"{restorer_id} request image/mask evidence is malformed: {exc}") from exc


def _physical_smoke_status(path: Path | None) -> tuple[bool, str]:
    if path is None:
        return False, "remote physical smoke evidence is required before remote benchmark execution"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"remote physical smoke evidence cannot be read: {exc}"
    if not isinstance(payload, Mapping):
        return False, "remote physical smoke evidence must be a JSON object"
    required = {
        "branch": "comfyui-remote",
        "status": "PASS",
        "mock_used": False,
        "local_fallback": False,
        "silent_fallback": False,
        "pixelPreservationResult": "PASS",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            return False, f"remote physical smoke evidence is not authoritative: {key}={payload.get(key)!r}"
    for key in ("sourceSha256", "a2Sha256", "workflowSha256", "outputSha256", "promptId"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            return False, f"remote physical smoke evidence is missing {key}"
    return True, ""


def _base_frame(case: Mapping[str, Any], repo_root: Path | None = None) -> tuple[Path, str]:
    frame = case.get("baseFrame")
    if not isinstance(frame, Mapping) or not isinstance(frame.get("path"), str):
        raise BenchmarkExecutionError("benchmark case baseFrame.path is missing")
    if not isinstance(frame.get("sha256"), str):
        raise BenchmarkExecutionError("benchmark case baseFrame.sha256 is missing")
    path = Path(frame["path"])
    if not path.is_absolute() and repo_root is not None:
        path = repo_root / path
    if not path.is_file():
        raise BenchmarkExecutionError(f"benchmark base frame is missing: {path}")
    return path, frame["sha256"]


def _verified_image_sha(path: Path | None, label: str) -> str:
    if path is None or not path.is_file():
        raise BenchmarkExecutionError(f"{label} is missing: {path}")
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise BenchmarkExecutionError(f"{label} is undecodable: {path}") from exc
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_image_bytes_sha(data: bytes, label: str) -> str:
    if not isinstance(data, bytes) or not data:
        raise BenchmarkExecutionError(f"{label} is missing")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise BenchmarkExecutionError(f"{label} is undecodable") from exc
    return hashlib.sha256(data).hexdigest()
