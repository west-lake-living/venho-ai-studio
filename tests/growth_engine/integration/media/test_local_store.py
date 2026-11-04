from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.media.pillow_processor import PillowImageProcessor, transform_version
from growth_engine.adapters.outbound.media.local_store import LocalMediaStore, MediaStoreError
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.media.ingest_asset import IngestAsset
from growth_engine.application.media.prepare_variant import PrepareVariant
from growth_engine.domain.media.asset import VariantQcStatus
from growth_engine.domain.media.media_policy import FACEBOOK_PHOTO_V1, INSTAGRAM_PHOTO_V1
from tests.growth_engine.support.fakes import FakeClock, SeqIds
from tests.growth_engine.support.image_fixtures import make_orientation_jpeg


def test_local_store_writes_original_and_variant_by_sha(tmp_path: Path) -> None:
    store = LocalMediaStore(tmp_path / "media")
    original_bytes = b"synthetic-original"
    original = store.put_original(BytesIO(original_bytes), max_bytes=100)
    variant_bytes = b"synthetic-variant-jpeg"
    variant_sha = hashlib.sha256(variant_bytes).hexdigest()
    variant_key = store.put_variant(variant_bytes, variant_sha)

    assert original.sha256 == hashlib.sha256(original_bytes).hexdigest()
    assert original.byte_size == len(original_bytes)
    assert variant_key == f"variants/{variant_sha[:2]}/{variant_sha}.jpg"
    assert store.open(original.object_key).read() == original_bytes
    assert store.open(variant_key).read() == variant_bytes
    assert store.verify(variant_key, variant_sha)


def test_failed_atomic_replace_leaves_no_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalMediaStore(tmp_path / "media")
    content = b"synthetic-variant"
    digest = hashlib.sha256(content).hexdigest()

    def fail_replace(source, target) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr("growth_engine.adapters.outbound.media.local_store.os.replace", fail_replace)
    with pytest.raises(OSError, match="synthetic replace failure"):
        store.put_variant(content, digest)

    assert not list((tmp_path / "media").rglob("*.jpg"))
    assert not list((tmp_path / "media").rglob(".tmp-*"))


def test_store_rejects_hash_mismatch_oversize_and_path_traversal(tmp_path: Path) -> None:
    store = LocalMediaStore(tmp_path / "media")
    with pytest.raises(MediaStoreError, match="max_bytes"):
        store.put_original(BytesIO(b"12345"), max_bytes=4)
    with pytest.raises(MediaStoreError, match="SHA-256"):
        store.put_variant(b"wrong", "a" * 64)
    with pytest.raises(MediaStoreError, match="object key"):
        store.open("../outside.txt")


def test_ingest_and_prepare_variants_persist_metadata_and_pending_qc(tmp_path: Path) -> None:
    database_path = tmp_path / "media.db"
    connection = connect(database_path)
    try:
        migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
        MigrationRunner(migrations).apply(connection, application_version="pytest")
    finally:
        connection.close()
    uow = SqliteUnitOfWork(lambda: connect(database_path), sleep=lambda _: None)
    store = LocalMediaStore(tmp_path / "store")
    clock = FakeClock(1_798_790_400_000)
    ids = SeqIds("media-test")
    ingest = IngestAsset(lambda: uow, store, clock, ids)
    asset = ingest.execute(
        source_type="upload",
        source_ref="synthetic-photo",
        source_revision="r1",
        stream=BytesIO(make_orientation_jpeg(6)),
        metadata={"fixture": "synthetic"},
    )
    assert store.verify(asset.original_key, asset.source_sha256)
    with uow.read_only() as read_tx:
        stored_asset = read_tx.media.get_asset(asset.id)
    assert stored_asset == asset

    prepare = PrepareVariant(lambda: uow, store, PillowImageProcessor(), clock, ids)
    facebook_variant = prepare.execute(asset.id, FACEBOOK_PHOTO_V1, transform_version(FACEBOOK_PHOTO_V1))
    instagram_variant = prepare.execute(asset.id, INSTAGRAM_PHOTO_V1, transform_version(INSTAGRAM_PHOTO_V1))
    assert facebook_variant.qc_status is VariantQcStatus.PENDING
    assert facebook_variant.width == 60 and facebook_variant.height == 80
    assert instagram_variant.qc_status is VariantQcStatus.PENDING
    assert instagram_variant.width * 5 == instagram_variant.height * 4
    assert store.verify(facebook_variant.object_key, facebook_variant.sha256)
    assert store.verify(instagram_variant.object_key, instagram_variant.sha256)
    with uow.read_only() as read_tx:
        assert read_tx.media.get_variant(facebook_variant.id) == facebook_variant
        assert read_tx.media.get_variant(instagram_variant.id) == instagram_variant
