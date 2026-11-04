from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentPackage:
    id: str
    slot_id: str
    topic_key: str
    pillar: str
    lane: str
    source_snapshot_json: str
    fact_snapshot_json: str
    fact_snapshot_hash: str
    generation_version: str
    created_at_ms: int
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "id",
            "slot_id",
            "topic_key",
            "pillar",
            "lane",
            "source_snapshot_json",
            "fact_snapshot_json",
            "generation_version",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if len(self.fact_snapshot_hash) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.fact_snapshot_hash
        ):
            raise ValueError("fact_snapshot_hash must be a 64-character SHA-256 hex digest")
        if type(self.created_at_ms) is not int:
            raise ValueError("created_at_ms must be integer epoch milliseconds")
