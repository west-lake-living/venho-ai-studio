from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ...application.ports.ledger import LedgerEntry


@dataclass
class JsonlRestorationLedger:
    path: Path

    def append(self, entry: LedgerEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"runId": entry.run_id, "attemptId": entry.attempt_id, "status": entry.status, **entry.payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
