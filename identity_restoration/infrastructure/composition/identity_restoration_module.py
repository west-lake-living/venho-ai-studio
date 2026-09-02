from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ...application.ports.identity_restorer import IdentityRestorerPort
from ...application.ports.worker_health import WorkerHealthPort
from ...application.registry.restorer_registry import RestorerRegistry
from ...application.use_cases.check_worker_health import CheckWorkerHealthUseCase
from ...application.use_cases.restore_face_crop import RestoreFaceCropUseCase
from ...application.benchmark_executor import (
    NanoBananaEditBenchmarkExecutor,
    NanoBananaEditPort,
    NanoBananaEditRequest,
)
from ...domain.value_objects import RestorerId
from ..comfyui.http_client import ComfyUIHttpClient
from ..comfyui.workflow_repository import FileWorkflowRepository
from ..health.cached_worker_health import CachedWorkerHealth
from ..health.comfyui_health_probe import ComfyUIHealthProbe
from ..persistence.atomic_file_artifact_sink import AtomicFileArtifactSink
from ..persistence.file_a2_authority_repository import FileA2AuthorityRepository
from ..persistence.file_concurrency_lease import FileConcurrencyLease
from ..persistence.jsonl_restoration_ledger import JsonlRestorationLedger
from ..persistence.production_release_state import load_production_release_state
from ..qc.validator_studio_qc_gateway import ValidatorStudioQcGateway
from ..restorers.comfyui_local_restorer import ComfyUILocalRestorer
from ..restorers.comfyui_remote_restorer import ComfyUIRemoteRestorer
from ..restorers.comfyui_candidate_v3_adapter import (
    CANDIDATE_V3_WORKFLOW_ID,
    ComfyUiCandidateV3Adapter,
)
from ..restorers.mock_restorer import MockIdentityRestorer
from ..restorers.nano_banana_edit_adapter import NanoBananaEditAdapter
from ..restorers.venho_os_nano_banana_port import VenhoOsNanoBananaPort
from ..system.system_clock import SystemClock
from ...domain.errors import RestorationError
from .env import RestorationEnv, read_restoration_env

# THE ONLY FILE THAT KNOWS EVERY CONCRETE CLASS (v2.0 PHẦN 3.5).
# CLI, integration tests and scripts all call build_identity_restoration_module().
# No other file is allowed to construct an adapter.
#
# READ BEFORE EDITING:
#   If you find yourself importing an adapter outside this file, you are
#   breaking the architecture. Inject through the Port instead.

# Legacy workflow already pinned in workflow_pins.yaml (GW-P0); this is the
# SDXL/PuLID workflow that ComfyUIIdentityRestorer already runs in production
# and that the GW-P0-T2 golden-master was frozen against. comfyui-local wraps
# it unchanged (patch v2.1 §2.3) — it is NOT the new SD1.5 workflow GW-P3
# authors for the remote worker.
_LOCAL_WORKFLOW_ID = "face_restore_v1_api"

# The active SD1.5 + IPAdapter FaceID workflow for the Windows worker.
# Registration remains fail-soft when the opt-in remote authority cannot load.
_REMOTE_WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v2"


@dataclass
class IdentityRestorationModule:
    use_case: RestoreFaceCropUseCase
    health: Optional[WorkerHealthPort]
    registry: RestorerRegistry
    env: RestorationEnv
    nano_banana_executor: Optional[NanoBananaEditBenchmarkExecutor] = None

    def check_health(self) -> CheckWorkerHealthUseCase | None:
        if self.health is None:
            return None
        return CheckWorkerHealthUseCase(health=self.health)


def build_qc_gateway(env: Optional[RestorationEnv] = None, *, required: bool = False):
    """Compose the existing Validator Studio adapter through one root.

    QC remains opt-in for the legacy restoration command. The dedicated
    existing-artifact validation command passes ``required=True`` so its
    explicit operation cannot silently degrade to ``QC_NOT_CONFIGURED``;
    no validator implementation or threshold is duplicated here.
    """
    env = env or read_restoration_env()
    if not env.qc_enabled and not required:
        return None
    if required and (not env.qc_enabled or env.qc_provider != "gemini"):
        return _UnavailableAuthoritativeQcGateway(
            "authoritative QC requires IDR_QC_ENABLED=true and IDR_QC_PROVIDER=gemini"
        )
    return ValidatorStudioQcGateway(provider=env.qc_provider, samples=env.qc_samples)


class _UnavailableAuthoritativeQcGateway:
    """Fail closed when production validation would otherwise select mock QC."""

    provider = "unavailable"
    samples = 0

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def validate(self, _composite_path: str, _a2_path: str):
        raise RestorationError("QC_AUTHORITY_UNAVAILABLE", self._reason, False)


def build_worker_health(env: Optional[RestorationEnv] = None,
                        *, clock: Optional[SystemClock] = None) -> Optional[WorkerHealthPort]:
    """Build the health probe from env alone — NO workflow JSON is read or
    validated (FACT 2 fix, v2.0 PHẦN 10.1). `venho-restore health` and
    scripts/probe_gpu_worker.py call this directly instead of going through
    build_identity_restoration_module(), so a broken/unpinned workflow (e.g.
    the GW-P3 remote workflow before it is authored) can never prevent a
    health probe from running."""
    env = env or read_restoration_env()
    if not env.comfyui_enabled:
        return None
    return CachedWorkerHealth(
        inner=ComfyUIHealthProbe(base_url=env.comfyui_base_url, timeout_s=env.health_timeout_seconds),
        clock=clock or SystemClock(),
        ttl_seconds=env.health_ttl_seconds,
    )


def _try_load_remote_restorer(env: RestorationEnv, root: Path) -> Optional[ComfyUIRemoteRestorer]:
    """comfyui-remote is opt-in (IDR_COMFYUI_REMOTE_ENABLED) AND requires the
    GW-P3 workflow to actually be authored + pinned in workflow_pins.yaml.
    Neither condition is true in this repo yet (workflow_pins.yaml still has
    a placeholder sha256 for face_restore_win_sd15_ipadapter_v1) — so this is
    deliberately fail-soft: an unready remote workflow must never break
    building the rest of the module (mock, comfyui-local, health). Requesting
    restorerId=comfyui-remote when it did not register still fails loudly at
    RestorerRegistry.resolve() (KeyError with the list of what IS available)."""
    if not env.comfyui_remote_enabled:
        return None
    workflow_repo = FileWorkflowRepository(
        workflow_root=root / env.workflow_root,
        pins_path=root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
    )
    try:
        workflow, descriptor = workflow_repo.load(_REMOTE_WORKFLOW_ID)
    except (RestorationError, OSError):
        # OSError covers FileNotFoundError from workflow_repo — the workflow
        # file itself missing (not authored yet) is the FACT 3 baseline case,
        # not a RestorationError from workflow_repository.py's own checks.
        return None
    return ComfyUIRemoteRestorer(
        client=ComfyUIHttpClient(base_url=env.comfyui_remote_base_url, timeout_s=env.comfyui_remote_timeout_seconds),
        workflow=workflow, workflow_id=descriptor.workflow_id, workflow_sha256=descriptor.sha256,
        model_identifiers=descriptor.models, timeout_seconds=env.comfyui_remote_timeout_seconds,
    )


def _try_load_candidate_v3_restorer(
    env: RestorationEnv, root: Path, *, gpu_execution_authorized: bool
) -> Optional[ComfyUiCandidateV3Adapter]:
    """Register Candidate v3 only behind its explicit feature flag.

    Loading and hash-verifying the pinned graph is local. The adapter's
    separate GPU authorization remains false by default, so enabling the
    feature flag alone cannot submit a job.
    """
    if not gpu_execution_authorized and not env.candidate_v3_enabled:
        return None
    workflow_repo = FileWorkflowRepository(
        workflow_root=root / env.workflow_root,
        pins_path=root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
    )
    workflow, descriptor = workflow_repo.load(CANDIDATE_V3_WORKFLOW_ID)
    return ComfyUiCandidateV3Adapter(
        client=ComfyUIHttpClient(
            base_url=env.comfyui_remote_base_url,
            timeout_s=env.comfyui_remote_timeout_seconds,
        ),
        workflow=workflow,
        workflow_id=descriptor.workflow_id,
        workflow_sha256=descriptor.sha256,
        model_identifiers=descriptor.models,
        timeout_seconds=env.comfyui_remote_timeout_seconds,
        gpu_execution_authorized=gpu_execution_authorized,
    )


def build_nano_banana_benchmark_executor(
    *,
    env: RestorationEnv,
    repo_root: Path,
    production_path: NanoBananaEditPort | None,
    request_factory: Callable[[dict, str, str, int], NanoBananaEditRequest] | None,
    evidence_root: Path | None,
    canonical_a2_path: Path | None = None,
) -> NanoBananaEditBenchmarkExecutor | None:
    """Register the existing Nano Banana path only when explicitly supplied.

    The Python composition root cannot construct Venho OS's TypeScript
    provider. The caller must inject the already-composed production path;
    absent that path/configuration this returns ``None`` rather than creating a
    second provider or silently substituting another backend.
    """
    if not env.nano_banana_enabled:
        return None
    if production_path is None and env.nano_banana_bridge_enabled:
        production_path = VenhoOsNanoBananaPort(endpoint=env.nano_banana_bridge_url)
    if production_path is None or request_factory is None or evidence_root is None:
        return None
    a2_path = canonical_a2_path or (repo_root / env.a2_path)
    if not a2_path.is_file():
        return None
    return NanoBananaEditBenchmarkExecutor(
        edit_path=NanoBananaEditAdapter(production_path),
        request_factory=request_factory,
        repo_root=repo_root,
        canonical_a2_path=a2_path,
        evidence_root=evidence_root,
    )


def build_identity_restoration_module(
    env: Optional[RestorationEnv] = None,
    *,
    repo_root: Path | None = None,
    nano_banana_path: NanoBananaEditPort | None = None,
    nano_banana_request_factory: Callable[[dict, str, str, int], NanoBananaEditRequest] | None = None,
    benchmark_evidence_root: Path | None = None,
    canonical_a2_path: Path | None = None,
) -> IdentityRestorationModule:
    env = env or read_restoration_env()
    root = repo_root or Path.cwd()
    release = load_production_release_state(root / env.production_release_path)
    clock = SystemClock()

    health = build_worker_health(env, clock=clock)

    restorers: dict[RestorerId, IdentityRestorerPort] = {
        "mock": MockIdentityRestorer(),
    }

    if env.comfyui_enabled:
        workflow_repo = FileWorkflowRepository(
            workflow_root=root / env.workflow_root,
            pins_path=root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml",
        )
        workflow, descriptor = workflow_repo.load(_LOCAL_WORKFLOW_ID)
        restorers["comfyui-local"] = ComfyUILocalRestorer(
            workflow=workflow, workflow_id=descriptor.workflow_id, workflow_sha256=descriptor.sha256,
            endpoint=env.comfyui_base_url, timeout_seconds=env.comfyui_timeout_seconds,
            model_identifiers=descriptor.models,
        )

    remote_restorer = _try_load_remote_restorer(env, root)
    if remote_restorer is not None:
        restorers["comfyui-remote"] = remote_restorer

    candidate_v3_restorer = _try_load_candidate_v3_restorer(
        env, root, gpu_execution_authorized=release.candidate_v3_active
    )
    if candidate_v3_restorer is not None:
        restorers["comfyui-candidate-v3"] = candidate_v3_restorer

    default_restorer = "comfyui-candidate-v3" if release.candidate_v3_active else env.default_restorer
    registry = RestorerRegistry(restorers=restorers, default_id=default_restorer)  # type: ignore[arg-type]

    use_case = RestoreFaceCropUseCase(
        registry=registry,
        a2_authority=FileA2AuthorityRepository(path=str(root / env.a2_path)),
        artifact_sink=AtomicFileArtifactSink(root=root / env.artifact_root),
        ledger=JsonlRestorationLedger(path=root / env.ledger_path),
        lease=FileConcurrencyLease(lock_path=root / env.artifact_root / ".lease"),
        clock=clock,
        qc=build_qc_gateway(env),
        health=health,
        face_qc_min=env.face_qc_min,
    )

    nano_banana_executor = build_nano_banana_benchmark_executor(
        env=env,
        repo_root=root,
        production_path=nano_banana_path,
        request_factory=nano_banana_request_factory,
        evidence_root=benchmark_evidence_root,
        canonical_a2_path=canonical_a2_path,
    )
    return IdentityRestorationModule(
        use_case=use_case,
        health=health,
        registry=registry,
        env=env,
        nano_banana_executor=nano_banana_executor,
    )
