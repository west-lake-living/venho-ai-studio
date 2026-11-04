from __future__ import annotations

import json
import math
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from growth_engine.application.dto import CandidateInput
from growth_engine.application.ports.content import CandidateSource
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_DEFAULT_TTL_MS = 30 * 24 * 60 * 60 * 1000
_VOLATILE_FIELDS = frozenset(
    {
        "status",
        "verified_by_human",
        "approved_by",
        "approved_at",
        "rejected_by",
        "rejected_at",
        "used_at",
        "scanned_at",
        "last_seen_at",
        "fast_lane_status",
        "fast_lane_checked_at",
        "fast_lane_publication_ids",
        "fast_lane_slot_id",
    }
)


class LegacyTrendSource(CandidateSource):
    """Read-only bridge from legacy trend JSON to the v2 candidate port."""

    def __init__(
        self,
        data_root: Path = Path("data/projects"),
        *,
        project: str = "venho_hotel",
    ) -> None:
        if not project.strip() or Path(project).name != project or project in {".", ".."}:
            raise ValueError("project must be a single safe path component")
        self._data_root = data_root
        self._project = project

    def scan(self, now_ms: int) -> list[CandidateInput]:
        if type(now_ms) is not int:
            raise ValueError("now_ms must be an integer epoch millisecond")
        path = self._source_path()
        if not path.exists():
            return []
        if path.is_symlink() or not path.is_file():
            raise ValueError("legacy trend source must be a regular file")
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("legacy trend source is unreadable or malformed") from error
        if not isinstance(rows, list):
            raise ValueError("legacy trend source must contain a JSON array")

        candidates = []
        for row in rows:
            if not isinstance(row, dict) or row.get("status") != "needs_human_approval":
                continue
            external_key = row.get("id")
            title = row.get("event_name") or row.get("title")
            if not isinstance(external_key, str) or not external_key.strip():
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            payload = _safe_payload(row)
            payload_hash = sha256_hex(canonical_json_bytes(payload))
            start_at_ms = _event_date_ms(row.get("event_start"), end_of_day=False)
            end_at_ms = _event_date_ms(row.get("event_end") or row.get("event_start"), end_of_day=True)
            explicit_expiry = row.get("expires_at_ms")
            if type(explicit_expiry) is int:
                expires_at_ms = explicit_expiry
            elif end_at_ms is not None:
                expires_at_ms = end_at_ms
            else:
                expires_at_ms = now_ms + _DEFAULT_TTL_MS
            is_event = row.get("is_event") is True
            candidates.append(
                CandidateInput(
                    source="trend_radar",
                    external_key=external_key,
                    source_revision=payload_hash,
                    topic_key=external_key,
                    event_key=external_key if is_event else None,
                    event_start_at_ms=start_at_ms,
                    event_end_at_ms=end_at_ms if is_event else None,
                    expires_at_ms=expires_at_ms,
                    payload=payload,
                    source_hash=payload_hash,
                )
            )
        return candidates

    def _source_path(self) -> Path:
        root = self._data_root.expanduser().resolve()
        candidate = self._data_root / self._project / "research" / "trend_candidates.json"
        if candidate.is_symlink():
            raise ValueError("legacy trend source must not be a symlink")
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError("legacy trend source resolves outside data_root") from error
        return resolved


def _safe_payload(row: dict[str, Any]) -> dict[str, object]:
    content = {key: value for key, value in row.items() if key not in _VOLATILE_FIELDS}
    normalized = _normalize_json(content)
    if not isinstance(normalized, dict):
        raise ValueError("trend candidate payload must be an object")
    return normalized


def _normalize_json(value: object) -> object:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("trend candidate contains a non-finite number")
        return format(value, ".15g")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("trend candidate payload keys must be strings")
        return {key: _normalize_json(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_normalize_json(nested) for nested in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("trend candidate payload contains an unsupported value")


def _event_date_ms(value: object, *, end_of_day: bool) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    wall_time = time.max if end_of_day else time.min
    return int(datetime.combine(parsed, wall_time, _ICT).timestamp() * 1000)
