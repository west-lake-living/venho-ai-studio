from __future__ import annotations

import os
from dataclasses import dataclass

# THE ONLY FILE THAT READS os.environ for this bounded context (v2.0 PHẦN 11).
# Defaults are deliberately the safest possible: mock restorer, ComfyUI
# disabled. Turning on a real backend is a conscious act, never an accident
# of a missing .env.


@dataclass(frozen=True)
class RestorationEnv:
    default_restorer: str = "mock"
    comfyui_enabled: bool = False
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_timeout_seconds: float = 600.0
    # GW-P3: comfyui-remote is a separate opt-in from comfyui-local/health so the
    # composition root can attempt to register it without that attempt ever being
    # able to break health probing (FACT 2) — see build_worker_health() below.
    comfyui_remote_enabled: bool = False
    comfyui_remote_base_url: str = "http://127.0.0.1:8188"
    comfyui_remote_timeout_seconds: float = 600.0
    health_ttl_seconds: float = 30.0
    health_timeout_seconds: float = 5.0
    workflow_root: str = "identity_restoration/workflows"
    artifact_root: str = "data/projects/venho_hotel/identity_restoration"
    ledger_path: str = "data/projects/venho_hotel/identity_restoration/ledger.jsonl"
    a2_path: str = "assets/linh_an/A2_Front.png"
    max_concurrent: int = 1
    nano_banana_enabled: bool = False
    nano_banana_bridge_enabled: bool = False
    nano_banana_bridge_url: str = "http://127.0.0.1:3000/api/v1/identity-restoration/nano-banana-smoke"
    # Candidate v3 is a Phase 0 contract only; execution remains disabled
    # until a later candidate runtime has been implemented and authorized.
    candidate_v3_enabled: bool = False
    production_release_path: str = "config/projects/venho_hotel/identity_restoration/production_release.json"
    face_qc_min: float = 90.0
    # Explicit geometry backend selection.  The default preserves the existing
    # InsightFace production behavior; YuNet is opt-in and never a fallback.
    geometry_backend: str = "insightface"
    # QC is opt-in so existing mock/offline restoration behavior remains
    # backward-compatible. The production validation command enables it
    # explicitly through the same composition root.
    qc_enabled: bool = False
    qc_provider: str = "mock"
    qc_samples: int = 3


def read_restoration_env() -> RestorationEnv:
    return RestorationEnv(
        default_restorer=os.environ.get("IDR_DEFAULT_RESTORER", "mock"),
        comfyui_enabled=_as_bool(os.environ.get("IDR_COMFYUI_ENABLED", "false")),
        comfyui_base_url=os.environ.get("IDR_COMFYUI_BASE_URL", "http://127.0.0.1:8188"),
        comfyui_timeout_seconds=float(os.environ.get("IDR_COMFYUI_TIMEOUT_SECONDS", "600")),
        comfyui_remote_enabled=_as_bool(os.environ.get("IDR_COMFYUI_REMOTE_ENABLED", "false")),
        comfyui_remote_base_url=os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL", "http://127.0.0.1:8188"),
        comfyui_remote_timeout_seconds=float(os.environ.get("IDR_COMFYUI_REMOTE_TIMEOUT_SECONDS", "600")),
        health_ttl_seconds=float(os.environ.get("IDR_HEALTH_TTL_SECONDS", "30")),
        health_timeout_seconds=float(os.environ.get("IDR_HEALTH_TIMEOUT_SECONDS", "5")),
        workflow_root=os.environ.get("IDR_WORKFLOW_ROOT", "identity_restoration/workflows"),
        artifact_root=os.environ.get("IDR_ARTIFACT_ROOT", "data/projects/venho_hotel/identity_restoration"),
        ledger_path=os.environ.get(
            "IDR_LEDGER_PATH", "data/projects/venho_hotel/identity_restoration/ledger.jsonl"),
        a2_path=os.environ.get("IDR_A2_PATH", "assets/linh_an/A2_Front.png"),
        max_concurrent=int(os.environ.get("IDR_MAX_CONCURRENT", "1")),
        nano_banana_enabled=_as_bool(os.environ.get("IDR_NANO_BANANA_ENABLED", "false")),
        nano_banana_bridge_enabled=_as_bool(
            os.environ.get("IDR_NANO_BANANA_BRIDGE_ENABLED", "false")
        ),
        nano_banana_bridge_url=os.environ.get(
            "IDR_NANO_BANANA_BRIDGE_URL",
            "http://127.0.0.1:3000/api/v1/identity-restoration/nano-banana-smoke",
        ),
        candidate_v3_enabled=_as_bool(os.environ.get("IDR_CANDIDATE_V3_ENABLED", "false")),
        production_release_path=os.environ.get("IDR_PRODUCTION_RELEASE_PATH", "config/projects/venho_hotel/identity_restoration/production_release.json"),
        face_qc_min=float(os.environ.get("IDR_FACE_QC_MIN", "90.0")),
        geometry_backend=os.environ.get("IDR_GEOMETRY_BACKEND", "insightface"),
        qc_enabled=_as_bool(os.environ.get("IDR_QC_ENABLED", "false")),
        qc_provider=os.environ.get("IDR_QC_PROVIDER", "mock"),
        qc_samples=int(os.environ.get("IDR_QC_SAMPLES", "3")),
    )


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
