from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Callable

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.media import ImageProcessor, MediaStore
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.media_policy import MediaProfile


class AssetNotFoundError(LookupError):
    pass


class MediaIntegrityError(RuntimeError):
    pass


class PrepareVariant:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        media_store: MediaStore,
        image_processor: ImageProcessor,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._media_store = media_store
        self._image_processor = image_processor
        self._clock = clock
        self._ids = ids

    def execute(self, asset_id: str, profile: MediaProfile, transform_version: str) -> MediaVariant:
        if not transform_version.strip():
            raise ValueError("transform_version is required")
        with self._uow_factory().read_only() as tx:
            asset = tx.media.get_asset(asset_id)
        if asset is None:
            raise AssetNotFoundError(f"media asset not found: {asset_id}")

        # Filesystem I/O and image decoding stay outside database transactions.
        source_digest = hashlib.sha256()
        source_size = 0
        with self._media_store.open(asset.original_key) as original_stream:
            with tempfile.TemporaryDirectory(prefix="growth-media-") as temp_dir:
                original_path = Path(temp_dir) / "source.bin"
                with original_path.open("wb") as output:
                    while True:
                        chunk = original_stream.read(64 * 1024)
                        if not chunk:
                            break
                        source_size += len(chunk)
                        if source_size > 25 * 1024 * 1024:
                            raise MediaIntegrityError("original asset exceeds 25 MiB")
                        source_digest.update(chunk)
                        output.write(chunk)
                if source_digest.hexdigest() != asset.source_sha256:
                    raise MediaIntegrityError("original asset SHA-256 does not match metadata")
                normalized = self._image_processor.normalize(original_path, profile.spec)

        object_key = self._media_store.put_variant(normalized.data, normalized.sha256)
        variant = MediaVariant(
            id=self._ids.new_id(),
            asset_id=asset.id,
            transform_version=transform_version,
            sha256=normalized.sha256,
            object_key=object_key,
            width=normalized.width,
            height=normalized.height,
            mime=normalized.mime,
            byte_size=len(normalized.data),
            qc_status=VariantQcStatus.PENDING,
            created_at_ms=self._clock.now_ms(),
        )
        with self._uow_factory().begin_immediate() as tx:
            tx.media.save_variant(variant)
        return variant


def prepare_variant(
    use_case: PrepareVariant,
    asset_id: str,
    profile: MediaProfile,
    transform_version: str,
) -> MediaVariant:
    return use_case.execute(asset_id, profile, transform_version)
