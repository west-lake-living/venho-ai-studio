from __future__ import annotations

import hashlib
import json
from typing import Callable, Optional

from ...domain.compositing import composite_crop_into_canvas
from ...domain.entities import RestorationRequest, RestoredCrop
from ...domain.errors import RestorationError
from ...domain.policies.geometry import assert_crop_transform_round_trips
from ...domain.policies.pixel_preservation import assert_pixels_preserved
from ...domain.policies.promotion import QcResult, is_full_gate_pass
from ..dto.restoration_result import RestorationErrorDetail, RestorationResult
from ..dto.restore_command import RestoreCommand
from ..ports.a2_authority_repository import A2AuthorityRepositoryPort
from ..ports.artifact_sink import ArtifactSinkPort
from ..ports.clock import ClockPort
from ..ports.concurrency import ConcurrencyLeasePort
from ..ports.ledger import LedgerEntry, RestorationLedgerPort
from ..ports.qc_gateway import QcGatewayPort
from ..ports.worker_health import WorkerHealthPort, WorkerStatus
from ..registry.restorer_registry import RestorerRegistry

# READ BEFORE EDITING (v2.0 PHẦN 7.3):
#   * Exactly ONE call to restorer.restore() in this function. A second call
#     site is hidden cost and a wrong ledger.
#   * Everything before "RANH GIỚI TỐN KÉM" below is free. Everything after
#     has already spent real GPU-time — that ordering is deliberate.
#   * Never swallow an exception. A fake completion is the worst failure mode
#     this system has.


class RestoreFaceCropUseCase:
    def __init__(
        self,
        *,
        registry: RestorerRegistry,
        a2_authority: A2AuthorityRepositoryPort,
        artifact_sink: ArtifactSinkPort,
        ledger: RestorationLedgerPort,
        lease: ConcurrencyLeasePort,
        clock: ClockPort,
        qc: Optional[QcGatewayPort] = None,
        health: Optional[WorkerHealthPort] = None,
        face_qc_min: float = 90.0,
        cancel_check: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self._registry = registry
        self._a2_repo = a2_authority
        self._sink = artifact_sink
        self._ledger = ledger
        self._lease = lease
        self._clock = clock
        self._qc = qc
        self._health = health
        self._face_qc_min = face_qc_min
        self._cancel_check = cancel_check

    def execute(self, cmd: RestoreCommand) -> RestorationResult:
        restorer = self._registry.resolve(cmd.restorer_id)
        health_evidence = None

        # ---- free, fail fast -------------------------------------------------
        try:
            a2 = self._a2_repo.load()
            a2.verify(cmd.a2_sha256)
            assert_crop_transform_round_trips(cmd.crop_transform)
        except RestorationError as err:
            return self._fail(cmd, err)

        if self._health is not None:
            health = self._health.probe()
            health_evidence = {
                "status": health.status.value,
                "gpuName": health.gpu_name,
                "vramFreeMb": health.vram_free_mb,
                "latencyMs": health.latency_ms,
            }
            if health.status is WorkerStatus.OFFLINE:
                return self._fail(cmd, RestorationError("ERR_GW_WORKER_OFFLINE", "worker health probe reported OFFLINE", retryable=True))

        started = self._clock.monotonic()
        with self._lease.acquire(key="gpu_worker", ttl_seconds=cmd.timeout_seconds + 60):
            if self._cancel_check is not None and self._cancel_check(cmd.run_id):
                return RestorationResult(run_id=cmd.run_id, attempt_id=cmd.attempt_id, status="CANCELLED")

            # ══════════ COSTLY BOUNDARY — everything below is real GPU-time ══════════
            try:
                restored = restorer.restore(
                    RestorationRequest(
                        run_id=cmd.run_id,
                        attempt_id=cmd.attempt_id,
                        crop_png=cmd.crop_png,
                        mask=cmd.mask,
                        a2=a2,
                        workflow_id=cmd.workflow_id,
                        seed=cmd.seed,
                        params=cmd.params,
                    )
                )
            except RestorationError as err:
                self._ledger.append(LedgerEntry(cmd.run_id, cmd.attempt_id, "FAILED", {"code": err.code}))
                return self._fail(cmd, err)

            provider_evidence = {}
            evidence_reader = getattr(restorer, "execution_evidence", None)
            if callable(evidence_reader):
                evidence = evidence_reader()
                if isinstance(evidence, dict):
                    provider_evidence = dict(evidence)

            try:
                restored.assert_geometry_matches(
                    RestorationRequest(cmd.run_id, cmd.attempt_id, cmd.crop_png, cmd.mask, a2,
                                       cmd.workflow_id, cmd.seed, cmd.params)
                )
            except RestorationError as err:
                return self._fail(cmd, err)

            # §3.2 anti-fake-success: identical restored/input bytes means the
            # workflow never ran or we read the wrong file — FAIL, not PASS.
            if restored.png_bytes == cmd.crop_png:
                err = RestorationError("ERR_GW_EMPTY_OUTPUT", "restored crop is byte-identical to input crop",
                                       retryable=False)
                self._ledger.append(LedgerEntry(cmd.run_id, cmd.attempt_id, "FAILED", {"code": err.code}))
                return self._fail(cmd, err)

            composite_bytes = composite_crop_into_canvas(
                base_canvas_png=cmd.base_canvas_png, restored=restored,
                transform=cmd.crop_transform, editable_mask_png=cmd.full_canvas_mask.editable,
            )
            pixel = assert_pixels_preserved(
                before_canvas=cmd.base_canvas_png, after_canvas=composite_bytes,
                editable_mask=cmd.full_canvas_mask.editable,
            )
            if not pixel.passed:
                err = RestorationError("ERR_GW_PIXEL_LOCK_VIOLATED",
                                       f"{pixel.mutated_pixel_count} locked pixels changed", retryable=False)
                self._ledger.append(LedgerEntry(cmd.run_id, cmd.attempt_id, "FAILED",
                                                {"code": err.code, "mutatedPixelCount": pixel.mutated_pixel_count}))
                return self._fail(cmd, err, pixel_lock=pixel)

            composite_artifact = self._sink.write_atomic(
                key=f"{cmd.run_id}/{cmd.attempt_id}/composite.png", data=composite_bytes)
            restored_artifact = self._sink.write_atomic(
                key=f"{cmd.run_id}/{cmd.attempt_id}/restored_crop.png", data=restored.png_bytes)

            qc_result: Optional[QcResult] = None
            qc_payload = None
            if self._qc is not None:
                qc_result = self._qc.validate(composite_artifact.path, a2_path=self._a2_repo.path)
                qc_payload = {"faceScore": qc_result.face_score,
                              "allValidatorsApproved": qc_result.all_validators_approved,
                              "killSwitchTriggered": qc_result.kill_switch_triggered}
                if qc_result.source_authority is not None:
                    qc_payload["sourceAuthority"] = qc_result.source_authority

        runtime_ms = int((self._clock.monotonic() - started) * 1000)
        status = self._decide_status(qc_result, pixel)
        descriptor = restorer.describe()
        restoration_params = {
            "denoise": cmd.params.denoise,
            "steps": cmd.params.steps,
            "cfg": cmd.params.cfg,
            "sampler": cmd.params.sampler,
            "scheduler": cmd.params.scheduler,
        }
        lineage = {
            "restorerId": descriptor.restorer_id,
            "workflowId": descriptor.workflow_id,
            "workflowSha256": descriptor.workflow_sha256,
            "modelIdentifiers": list(descriptor.model_identifiers),
            "seed": cmd.seed,
            "restorationParams": restoration_params,
            "effectiveConfigSha256": _effective_config_sha256(
                workflow_id=descriptor.workflow_id,
                workflow_sha256=descriptor.workflow_sha256,
                seed=cmd.seed,
                params=restoration_params,
            ),
            "a2AuthoritySha256": a2.sha256,
            "cropTransform": {"box": list(cmd.crop_transform.to_box()), "targetSize": cmd.crop_transform.target_size},
            "maskVersion": cmd.mask.version,
            "maskSpaces": {
                "restoration": {
                    "coordinateSpace": "crop-local",
                    "version": cmd.mask.version,
                    "sha256": hashlib.sha256(cmd.mask.editable).hexdigest(),
                },
                "preservation": {
                    "coordinateSpace": "full-canvas",
                    "version": cmd.full_canvas_mask.version,
                    "sha256": hashlib.sha256(cmd.full_canvas_mask.editable).hexdigest(),
                },
            },
            "runtimeMs": runtime_ms,
            "pixelLock": {"passed": pixel.passed, "mutatedPixelCount": pixel.mutated_pixel_count,
                          "editableRegionHash": pixel.editable_region_hash},
        }
        if health_evidence is not None:
            lineage["workerHealth"] = health_evidence
        if provider_evidence:
            lineage.update(provider_evidence)
        self._ledger.append(LedgerEntry(cmd.run_id, cmd.attempt_id, status, lineage))
        return RestorationResult(
            run_id=cmd.run_id, attempt_id=cmd.attempt_id, status=status,
            restored_crop_path=restored_artifact.path, composite_path=composite_artifact.path,
            pixel_lock=pixel, qc=qc_payload, lineage=lineage,
        )

    def _decide_status(self, qc: Optional[QcResult], pixel) -> str:
        if not pixel.passed:
            return "REJECTED"
        if qc is None:
            return "NEEDS_REVIEW"
        if is_full_gate_pass(qc, pixel, face_qc_min=self._face_qc_min):
            return "FULL_GATE_PASS"
        if qc.kill_switch_triggered:
            return "REJECTED"
        return "NEEDS_REVIEW"

    @staticmethod
    def _fail(cmd: RestoreCommand, err: RestorationError, *, pixel_lock=None) -> RestorationResult:
        return RestorationResult(
            run_id=cmd.run_id, attempt_id=cmd.attempt_id, status="FAILED", pixel_lock=pixel_lock,
            error=RestorationErrorDetail(code=err.code, message=err.message, retryable=err.retryable),
        )


def _effective_config_sha256(*, workflow_id: str | None, workflow_sha256: str | None,
                             seed: int, params: dict[str, object]) -> str:
    payload = {
        "workflowId": workflow_id,
        "workflowSha256": workflow_sha256,
        "seed": seed,
        "params": params,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
