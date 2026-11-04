from __future__ import annotations

import json
from collections.abc import Mapping
from typing import BinaryIO, Callable

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.media import MediaStore
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.media.asset import MediaAsset

MAX_ORIGINAL_BYTES = 25 * 1024 * 1024


class IngestAsset:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        media_store: MediaStore,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._media_store = media_store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        *,
        source_type: str,
        source_ref: str,
        source_revision: str,
        stream: BinaryIO,
        metadata: Mapping[str, object] | None = None,
    ) -> MediaAsset:
        if source_type not in {"ai_generated", "library", "upload", "fallback", "legacy"}:
            raise ValueError("source_type is invalid")
        if not source_ref.strip() or not source_revision.strip():
            raise ValueError("source_ref and source_revision are required")
        metadata_json = json.dumps(
            dict(metadata or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        stored = self._media_store.put_original(stream, max_bytes=MAX_ORIGINAL_BYTES)
        asset = MediaAsset(
            id=self._ids.new_id(),
            source_type=source_type,
            source_ref=source_ref,
            source_revision=source_revision,
            source_sha256=stored.sha256,
            original_key=stored.object_key,
            metadata_json=metadata_json,
            created_at_ms=self._clock.now_ms(),
        )
        with self._uow_factory().begin_immediate() as tx:
            tx.media.save_asset(asset)
        return asset


def ingest_asset(
    use_case: IngestAsset,
    *,
    source_type: str,
    source_ref: str,
    source_revision: str,
    stream: BinaryIO,
    metadata: Mapping[str, object] | None = None,
) -> MediaAsset:
    return use_case.execute(
        source_type=source_type,
        source_ref=source_ref,
        source_revision=source_revision,
        stream=stream,
        metadata=metadata,
    )
