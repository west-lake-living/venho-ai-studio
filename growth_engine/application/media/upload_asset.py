from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import BinaryIO, Protocol

from growth_engine.application.media.ingest_asset import IngestAsset, MAX_ORIGINAL_BYTES
from growth_engine.application.ports.clock import IdGenerator
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


@dataclass(frozen=True)
class AssetUploadResult:
    job_id: str
    asset_id: str
    source_sha256: str
    request_fingerprint: str
    state: str = "UPLOADED"


class AssetUploadStore(Protocol):
    def find_upload(self, business_key: str) -> tuple[str, Mapping[str, object]] | None: ...
    def save_upload(
        self,
        job_id: str,
        business_key: str,
        result: AssetUploadResult,
        *,
        created_at_ms: int,
    ) -> None: ...


class UploadAsset:
    """Persist the uploaded original, then expose its durable Dashboard job receipt."""

    def __init__(
        self,
        ingest_asset: IngestAsset,
        store: AssetUploadStore,
        *,
        ids: IdGenerator,
        now_ms: Callable[[], int],
    ) -> None:
        self._ingest_asset = ingest_asset
        self._store = store
        self._ids = ids
        self._now_ms = now_ms

    def execute(
        self,
        *,
        idempotency_key: str,
        actor: str,
        stream: BinaryIO,
        filename: str,
        content_type: str,
    ) -> AssetUploadResult:
        if not idempotency_key.strip() or not actor.strip():
            raise ValueError("idempotency_key and actor are required")
        if not callable(getattr(stream, "read", None)):
            raise ValueError("asset upload stream is required")
        request_fingerprint = _fingerprint(stream, filename, content_type)
        business_key = f"dashboard-upload:{idempotency_key}"
        existing = self._store.find_upload(business_key)
        if existing is not None:
            job_id, value = existing
            if value.get("request_fingerprint") != request_fingerprint:
                raise DomainError(
                    ErrorCode.IDEMPOTENCY_MISMATCH,
                    "Idempotency-Key đã dùng với một nội dung upload khác.",
                )
            return AssetUploadResult(
                job_id=job_id,
                asset_id=str(value["asset_id"]),
                source_sha256=str(value["source_sha256"]),
                request_fingerprint=request_fingerprint,
                state=str(value.get("state", "UPLOADED")),
            )

        asset = self._ingest_asset.execute(
            source_type="upload",
            source_ref=business_key,
            source_revision="1",
            stream=stream,
            metadata={"filename": filename, "content_type": content_type, "actor": actor},
        )
        job_id = self._ids.new_id()
        created_at_ms = self._now_ms()
        result = AssetUploadResult(job_id, asset.id, asset.source_sha256, request_fingerprint)
        self._store.save_upload(job_id, business_key, result, created_at_ms=created_at_ms)
        return result


def _fingerprint(stream: BinaryIO, filename: str, content_type: str) -> str:
    if not callable(getattr(stream, "tell", None)) or not callable(getattr(stream, "seek", None)):
        raise ValueError("asset upload stream must support rewind")
    position = stream.tell()
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            if not isinstance(chunk, bytes):
                raise ValueError("asset upload stream must return bytes")
            size += len(chunk)
            if size > MAX_ORIGINAL_BYTES:
                raise ValueError("asset upload exceeds 25 MiB")
            digest.update(chunk)
    finally:
        stream.seek(position)
    fingerprint = hashlib.sha256()
    fingerprint.update(digest.digest())
    fingerprint.update(b"\0")
    fingerprint.update(filename.encode("utf-8"))
    fingerprint.update(b"\0")
    fingerprint.update(content_type.encode("utf-8"))
    return fingerprint.hexdigest()
