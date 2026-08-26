from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from identity_restoration.application.ports.worker_health import WorkerStatus
from identity_restoration.infrastructure.health.comfyui_health_probe import ComfyUIHealthProbe


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "contracts/identity_restoration/fixtures/comfyui"


class _Response:
    status = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _probe_fixture(name: str):
    payload = json.loads((FIXTURES / name).read_text())
    with patch("identity_restoration.infrastructure.health.comfyui_health_probe.urlopen",
               return_value=_Response(payload)):
        return ComfyUIHealthProbe("https://fixture.invalid").probe()


def test_health_gate_uses_physical_vram_not_torch_allocator() -> None:
    health = _probe_fixture("system_stats_healthy.json")

    assert health.status is WorkerStatus.HEALTHY
    assert health.vram_total_mb == 6144
    assert health.vram_free_mb == 5066
    assert health.torch_vram_total_mb == 32
    assert health.torch_vram_free_mb == 24


def test_low_physical_vram_is_degraded_even_if_torch_free_is_high() -> None:
    payload = json.loads((FIXTURES / "system_stats_low_vram.json").read_text())
    payload["devices"][0]["torch_vram_free"] = 6 * 1024 * 1024 * 1024
    with patch("identity_restoration.infrastructure.health.comfyui_health_probe.urlopen",
               return_value=_Response(payload)):
        health = ComfyUIHealthProbe("https://fixture.invalid").probe()

    assert health.status is WorkerStatus.DEGRADED
    assert health.vram_free_mb == 400
    assert health.torch_vram_free_mb == 6144
