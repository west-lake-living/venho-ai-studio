from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from growth_engine.application.dto import FactSnapshot
from shared.security import ensure_safe_slug


class LegacyFactSource:
    """Read approved, time-valid legacy facts without creating or mutating storage."""

    def __init__(
        self,
        project: str = "venho_hotel",
        data_root: Path = Path("data/projects"),
    ) -> None:
        self.project = ensure_safe_slug(project, field="project")
        self.data_root = Path(data_root)

    def approved_facts(self, keys: list[str], at_ms: int) -> FactSnapshot:
        moment = datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc)
        facts_dir = self.data_root / self.project / "growth" / "facts"
        facts: dict[str, dict[str, Any]] = {}

        for key in sorted(set(keys)):
            safe_key = ensure_safe_slug(key, field="fact_key")
            path = facts_dir / f"{safe_key.replace('.', '__')}.json"
            if path.is_symlink() or not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("fact_key") != key:
                continue
            if payload.get("status") != "approved":
                continue

            valid_from = _parse_fact_time(payload.get("valid_from"))
            valid_to_raw = payload.get("valid_to")
            valid_to = _parse_fact_time(valid_to_raw) if valid_to_raw else None
            if valid_to_raw and valid_to is None:
                continue
            if valid_from is None or moment < valid_from or (valid_to is not None and moment > valid_to):
                continue
            facts[key] = payload

        encoded = json.dumps(
            facts,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return FactSnapshot(facts=facts, snapshot_hash=digest)


def _parse_fact_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
