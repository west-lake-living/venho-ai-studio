from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .orchestration import AuditTrail


class AuditStore:
    """Durable JSON audit store for resumable Action Composite jobs."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, trail: AuditTrail) -> Path:
        target = self.root / f"{trail.job_id}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(trail.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        return target

    def load(self, job_id: str) -> AuditTrail:
        target = self.root / f"{job_id}.json"
        if not target.is_file():
            raise FileNotFoundError(f"Audit trail not found: {job_id}")
        payload: Dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
        return AuditTrail.model_validate(payload)
