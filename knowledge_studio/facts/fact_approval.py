from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from knowledge_studio.facts.fact_store import FactStore


def approve_fact(fact: dict[str, Any], *, approved_by: str, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> Path:
    payload = {
        **fact,
        "status": "approved",
        "approved_by": approved_by,
        "approved_at": datetime.now().isoformat(),
    }
    return FactStore(project=project, data_root=data_root).save(payload)
