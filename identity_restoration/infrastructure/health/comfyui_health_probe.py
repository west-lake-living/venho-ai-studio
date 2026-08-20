from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from ...application.ports.worker_health import WorkerHealth, WorkerStatus

# GW-P3 §8.3: /system_stats is the foundation of WorkerHealthPort. Real
# network call — never invoked directly in pytest; only via a fake/mock probe
# or recorded fixture (contracts/fixtures/identity_restoration/comfyui/).


@dataclass
class ComfyUIHealthProbe:
    base_url: str
    timeout_s: float = 5.0
    min_vram_mb_for_healthy: int = 4200

    def probe(self) -> WorkerHealth:
        started = time.monotonic()
        try:
            with urlopen(Request(self.base_url.rstrip("/") + "/system_stats"), timeout=self.timeout_s) as response:
                if response.status != 200:
                    return WorkerHealth(status=WorkerStatus.OFFLINE)
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError):
            return WorkerHealth(status=WorkerStatus.OFFLINE)

        latency_ms = (time.monotonic() - started) * 1000
        devices = body.get("devices") or []
        device = devices[0] if devices else {}
        gpu_name = device.get("name")
        vram_free_mb = int(device.get("vram_free", 0)) // (1024 * 1024) if device.get("vram_free") else None
        # DEGRADED, not a hard block: low VRAM jobs sometimes still succeed;
        # blocking them outright would reject work that would have finished,
        # while silently allowing them would let a real OOM get blamed on the
        # model (v2.0 PHẦN 8.4).
        status = WorkerStatus.HEALTHY
        if vram_free_mb is not None and vram_free_mb < self.min_vram_mb_for_healthy:
            status = WorkerStatus.DEGRADED
        return WorkerHealth(status=status, gpu_name=gpu_name, vram_free_mb=vram_free_mb, latency_ms=latency_ms)
