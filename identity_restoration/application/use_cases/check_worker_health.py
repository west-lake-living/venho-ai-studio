from __future__ import annotations

from dataclasses import dataclass

from ..ports.worker_health import WorkerHealth, WorkerHealthPort


@dataclass
class CheckWorkerHealthUseCase:
    health: WorkerHealthPort

    def execute(self) -> WorkerHealth:
        return self.health.probe()
