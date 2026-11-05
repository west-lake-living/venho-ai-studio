from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord
from growth_engine.application.media.upload_asset import AssetUploadResult


class SqliteDashboardAssetUploadStore:
    def __init__(self, uow_factory: Callable[[], Any]) -> None:
        self._uow_factory = uow_factory

    def find_upload(self, business_key: str) -> tuple[str, Mapping[str, object]] | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT id, payload_json FROM jobs WHERE kind='asset_upload' AND business_key=?",
                (business_key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["id"]), json.loads(row["payload_json"])

    def save_upload(
        self,
        job_id: str,
        business_key: str,
        result: AssetUploadResult,
        *,
        created_at_ms: int,
    ) -> None:
        payload = {
            "asset_id": result.asset_id,
            "source_sha256": result.source_sha256,
            "request_fingerprint": result.request_fingerprint,
            "state": result.state,
        }
        with self._uow_factory().begin_immediate() as tx:
            tx.jobs.save(JobRecord(
                id=job_id,
                kind="asset_upload",
                lane="jobs",
                business_key=business_key,
                payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                state="SUCCEEDED",
                run_at_ms=created_at_ms,
                created_at_ms=created_at_ms,
                updated_at_ms=created_at_ms,
            ))
