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
    health_ttl_seconds: float = 30.0
    health_timeout_seconds: float = 5.0
    workflow_root: str = "identity_restoration/workflows"
    artifact_root: str = "data/projects/venho_hotel/identity_restoration"
    ledger_path: str = "data/projects/venho_hotel/identity_restoration/ledger.jsonl"
    a2_path: str = "assets/linh_an/A2_Front.png"
    max_concurrent: int = 1
    nano_banana_enabled: bool = False
    face_qc_min: float = 90.0


def read_restoration_env() -> RestorationEnv:
    return RestorationEnv(
        default_restorer=os.environ.get("IDR_DEFAULT_RESTORER", "mock"),
        comfyui_enabled=_as_bool(os.environ.get("IDR_COMFYUI_ENABLED", "false")),
        comfyui_base_url=os.environ.get("IDR_COMFYUI_BASE_URL", "http://127.0.0.1:8188"),
        comfyui_timeout_seconds=float(os.environ.get("IDR_COMFYUI_TIMEOUT_SECONDS", "600")),
        health_ttl_seconds=float(os.environ.get("IDR_HEALTH_TTL_SECONDS", "30")),
        health_timeout_seconds=float(os.environ.get("IDR_HEALTH_TIMEOUT_SECONDS", "5")),
        workflow_root=os.environ.get("IDR_WORKFLOW_ROOT", "identity_restoration/workflows"),
        artifact_root=os.environ.get("IDR_ARTIFACT_ROOT", "data/projects/venho_hotel/identity_restoration"),
        ledger_path=os.environ.get(
            "IDR_LEDGER_PATH", "data/projects/venho_hotel/identity_restoration/ledger.jsonl"),
        a2_path=os.environ.get("IDR_A2_PATH", "assets/linh_an/A2_Front.png"),
        max_concurrent=int(os.environ.get("IDR_MAX_CONCURRENT", "1")),
        nano_banana_enabled=_as_bool(os.environ.get("IDR_NANO_BANANA_ENABLED", "false")),
        face_qc_min=float(os.environ.get("IDR_FACE_QC_MIN", "90.0")),
    )


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
