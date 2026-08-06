"""DoD #24 -- backup of growth state, including photo artifacts, that is
proven by restoring it rather than by the backup command exiting 0."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from shared.backup.growth_backup import (
    backup_dir_from_env,
    create_backup,
    latest_backup,
    list_backups,
    prune_backups,
    verify_restore,
)


def _seed_project(root: Path) -> Path:
    project_root = root / "venho_hotel"
    (project_root / "growth" / "artifacts" / "daily-monday" / "images").mkdir(parents=True)
    (project_root / "publishing").mkdir(parents=True)
    (project_root / "growth" / "facts").mkdir(parents=True)

    db_path = project_root / "growth" / "growth.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE publishing_slots (slot_id TEXT PRIMARY KEY, slot_date TEXT)")
        db.executemany(
            "INSERT INTO publishing_slots VALUES (?, ?)",
            [("slot-2026-08-10-monday", "2026-08-10"), ("slot-2026-08-12-wednesday", "2026-08-12")],
        )
    (project_root / "publishing" / "publication_registry.json").write_text(
        json.dumps({"publications": [{"publication_id": "pub-1"}]}), encoding="utf-8"
    )
    (project_root / "growth" / "rotation_state.json").write_text("{}", encoding="utf-8")
    (project_root / "growth" / "facts" / "fact-1.json").write_text('{"id": "fact-1"}', encoding="utf-8")
    (project_root / "growth" / "artifacts" / "daily-monday" / "images" / "generated.png").write_bytes(b"\x89PNG fake bytes")
    return project_root


def test_backup_captures_database_state_files_and_photo_artifacts(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _seed_project(data_root)
    manifest = create_backup(data_root=data_root, backup_dir=tmp_path / "backups")

    assert manifest["database"]["row_counts"] == {"publishing_slots": 2}
    assert {entry["path"] for entry in manifest["files"]} == {
        "publishing/publication_registry.json",
        "growth/rotation_state.json",
        "growth/facts/fact-1.json",
    }
    assert manifest["counts"]["artifacts"] == 1


def test_verify_restore_actually_restores_and_checks_row_counts(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _seed_project(data_root)
    manifest = create_backup(data_root=data_root, backup_dir=tmp_path / "backups")

    report = verify_restore(Path(manifest["snapshot_dir"]), backup_dir=tmp_path / "backups")

    assert report["ok"] is True
    assert report["database_ok"] is True
    assert report["files_verified"] == report["files_expected"] == 3
    assert report["artifacts_verified"] == report["artifacts_expected"] == 1
    # The restore is a real one: the database exists on disk outside the backup.
    restored_db = Path(report["restored_to"]) / "growth.db"
    with sqlite3.connect(restored_db) as db:
        assert db.execute("SELECT COUNT(*) FROM publishing_slots").fetchone()[0] == 2


def test_verify_restore_fails_loudly_on_a_corrupted_artifact(tmp_path: Path) -> None:
    """The failure mode this whole DoD exists for: a backup that still looks
    present but no longer restores what it claims."""
    data_root = tmp_path / "data"
    _seed_project(data_root)
    manifest = create_backup(data_root=data_root, backup_dir=tmp_path / "backups")
    blob = next((tmp_path / "backups" / "venho_hotel" / "artifacts-cas").rglob("*"))
    while blob.is_dir():
        blob = next(blob.rglob("*"))
    blob.write_bytes(b"corrupted")

    report = verify_restore(Path(manifest["snapshot_dir"]), backup_dir=tmp_path / "backups")

    assert report["ok"] is False
    assert any("artifact checksum mismatch" in error for error in report["errors"])


def test_verify_restore_fails_on_a_missing_snapshot_database(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _seed_project(data_root)
    manifest = create_backup(data_root=data_root, backup_dir=tmp_path / "backups")
    (Path(manifest["snapshot_dir"]) / "growth.db").unlink()

    report = verify_restore(Path(manifest["snapshot_dir"]), backup_dir=tmp_path / "backups")

    assert report["ok"] is False
    assert any("database file is missing" in error for error in report["errors"])


def test_artifacts_are_deduplicated_across_snapshots(tmp_path: Path) -> None:
    """90 daily snapshots must not cost 90 copies of 98MB of photos."""
    data_root = tmp_path / "data"
    _seed_project(data_root)
    create_backup(data_root=data_root, backup_dir=tmp_path / "backups")
    create_backup(data_root=data_root, backup_dir=tmp_path / "backups")

    cas_blobs = [p for p in (tmp_path / "backups" / "venho_hotel" / "artifacts-cas").rglob("*") if p.is_file()]
    assert len(cas_blobs) == 1
    assert len(list_backups(backup_dir=tmp_path / "backups")) == 2


def test_prune_keeps_the_newest_snapshots_and_collects_orphan_blobs(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    data_root = tmp_path / "data"
    project_root = _seed_project(data_root)
    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    for index in range(3):
        # A different photo per snapshot, so pruning has orphan blobs to collect.
        (project_root / "growth" / "artifacts" / "daily-monday" / "images" / "generated.png").write_bytes(
            f"\x89PNG {index}".encode("utf-8")
        )
        create_backup(data_root=data_root, backup_dir=tmp_path / "backups", now=base + timedelta(days=index))

    result = prune_backups(backup_dir=tmp_path / "backups", keep=1)

    assert result["snapshots_kept"] == 1
    assert result["blobs_removed"] == 2
    assert verify_restore(latest_backup(backup_dir=tmp_path / "backups"), backup_dir=tmp_path / "backups")["ok"]


def test_backup_dir_honours_env_override(tmp_path: Path) -> None:
    assert backup_dir_from_env({"VENHO_BACKUP_DIR": str(tmp_path / "elsewhere")}) == tmp_path / "elsewhere"
    assert backup_dir_from_env({}).name == "venho-ai-studio"
