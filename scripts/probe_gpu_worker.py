#!/usr/bin/env python3
"""One-shot health CLI for the identity restoration GPU worker (v2.0 PHẦN 10.1).

Usage:
    IDR_COMFYUI_ENABLED=true IDR_COMFYUI_BASE_URL=http://venho-gpu-win:8188 \\
        PYTHONPATH=. /usr/bin/python3 scripts/probe_gpu_worker.py

Prints WorkerHealth as JSON and exits 0 on HEALTHY/DEGRADED, 1 on OFFLINE.
Makes a real network call — never run this from pytest (0-network invariant).

Interpreter note: run with /usr/bin/python3 (system Python 3.9), the same
interpreter the repo's pytest suite uses. A bare `python3` on this machine's
PATH can resolve to Homebrew Python 3.14, which does not have Pillow/PyYAML
installed and will fail with ModuleNotFoundError. This is an environment
resolution issue, not a script bug — see reference-venho-os-build-traps.md
for the same class of trap in a sibling repo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity_restoration.application.use_cases.check_worker_health import CheckWorkerHealthUseCase
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_worker_health,
)


def main() -> int:
    # FACT 2 fix: health must never depend on the inference workflow loading
    # successfully — build_worker_health() reads env only, no workflow I/O.
    worker_health = build_worker_health()
    if worker_health is None:
        print(json.dumps({"status": "NOT_CONFIGURED",
                          "message": "IDR_COMFYUI_ENABLED is false — no worker to probe"}))
        return 1
    health = CheckWorkerHealthUseCase(health=worker_health).execute()
    print(json.dumps({"status": health.status.value, "gpuName": health.gpu_name,
                      "vramTotalMb": health.vram_total_mb, "vramFreeMb": health.vram_free_mb,
                      "torchVramTotalMb": health.torch_vram_total_mb,
                      "torchVramFreeMb": health.torch_vram_free_mb,
                      "latencyMs": health.latency_ms}))
    return 0 if health.status.value in ("HEALTHY", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
