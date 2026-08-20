from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...application.ports.identity_restorer import IdentityRestorerPort
from ...application.ports.worker_health import WorkerHealthPort
from ...application.registry.restorer_registry import RestorerRegistry
from ...application.use_cases.check_worker_health import CheckWorkerHealthUseCase
from ...application.use_cases.restore_face_crop import RestoreFaceCropUseCase
from ...domain.value_objects import RestorerId
from ..comfyui.workflow_repository import FileWorkflowRepository
from ..health.cached_worker_health import CachedWorkerHealth
from ..health.comfyui_health_probe import ComfyUIHealthProbe
from ..persistence.atomic_file_artifact_sink import AtomicFileArtifactSink
from ..persistence.file_a2_authority_repository import FileA2AuthorityRepository
from ..persistence.file_concurrency_lease import FileConcurrencyLease
from ..persistence.jsonl_restoration_ledger import JsonlRestorationLedger
from ..restorers.comfyui_local_restorer import ComfyUILocalRestorer
from ..restorers.mock_restorer import MockIdentityRestorer
from ..system.system_clock import SystemClock
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


@dataclass
class IdentityRestorationModule:
    use_case: RestoreFaceCropUseCase
    health: Optional[WorkerHealthPort]
    registry: RestorerRegistry
    env: RestorationEnv

    def check_health(self) -> CheckWorkerHealthUseCase | None:
        if self.health is None:
            return None
        return CheckWorkerHealthUseCase(health=self.health)


def build_identity_restoration_module(env: Optional[RestorationEnv] = None,
                                      *, repo_root: Path | None = None) -> IdentityRestorationModule:
    env = env or read_restoration_env()
    root = repo_root or Path.cwd()
    clock = SystemClock()

    health: Optional[WorkerHealthPort] = None
    restorers: dict[RestorerId, IdentityRestorerPort] = {
        "mock": MockIdentityRestorer(),
    }

    if env.comfyui_enabled:
        health = CachedWorkerHealth(
            inner=ComfyUIHealthProbe(base_url=env.comfyui_base_url, timeout_s=env.health_timeout_seconds),
            clock=clock,
            ttl_seconds=env.health_ttl_seconds,
        )
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

    registry = RestorerRegistry(restorers=restorers, default_id=env.default_restorer)  # type: ignore[arg-type]

    use_case = RestoreFaceCropUseCase(
        registry=registry,
        a2_authority=FileA2AuthorityRepository(path=str(root / env.a2_path)),
        artifact_sink=AtomicFileArtifactSink(root=root / env.artifact_root),
        ledger=JsonlRestorationLedger(path=root / env.ledger_path),
        lease=FileConcurrencyLease(lock_path=root / env.artifact_root / ".lease"),
        clock=clock,
        qc=None,  # wired explicitly by callers that want live QC — never by default (cost discipline)
        health=health,
        face_qc_min=env.face_qc_min,
    )

    return IdentityRestorationModule(use_case=use_case, health=health, registry=registry, env=env)
