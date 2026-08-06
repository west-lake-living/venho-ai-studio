"""Backup + verify-restore for growth state (plan v3.1 DoD #24).

Why (2026-08-06): the plan recorded this as the one infrastructure DoD
honestly marked "chưa đạt". `data/` is gitignored in full, so the pieces git
was assumed to be covering -- `publication_registry.json`, `growth.db`, the
generated photos -- have in fact never been backed up anywhere. 98MB of
artifacts and the entire publication history live on exactly one disk.

Design constraints that shaped this:

- **Stdlib only.** The plan's sketch was `backup.sh` with rclone; rclone is
  not installed and adding a cloud dependency to a one-person hotel's backup
  is how backups stop running. This writes to a local directory (override
  with `VENHO_BACKUP_DIR`); putting that directory on iCloud/an external disk
  is a filesystem decision, not a code one.
- **Content-addressed artifacts.** Photos never change once generated, so
  every backup would otherwise re-copy the same 98MB. Artifacts go into a
  shared `artifacts-cas/` keyed by sha256 and each snapshot's manifest just
  references the hashes: 90 daily snapshots cost roughly one copy of the
  images plus 90 small manifests.
- **Verify actually restores.** `verify_restore` is not a "file exists"
  check: it copies the snapshot's database into a scratch directory, opens
  it, runs `PRAGMA integrity_check`, compares every table's row count against
  the counts recorded when the snapshot was taken, and re-hashes every file
  and artifact it references. A backup nobody has restored is a hypothesis.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_BACKUP_DIR = Path.home() / "VenHo-Backups" / "venho-ai-studio"
CAS_DIRNAME = "artifacts-cas"
MANIFEST_NAME = "manifest.json"
SNAPSHOT_DB_NAME = "growth.db"

# Everything under data/projects/{project} that is not an artifact photo:
# small, changes constantly, and is what actually cannot be regenerated.
_STATE_FILES = [
    Path("publishing/publication_registry.json"),
    Path("growth/rotation_state.json"),
    Path("growth/evergreen_pool.json"),
]
_STATE_DIRS = [
    Path("growth/facts"),
    Path("research"),
    Path("knowledge"),
]
_ARTIFACTS_DIR = Path("growth/artifacts")
_DB_PATH = Path("growth/growth.db")


def backup_dir_from_env(env: Optional[dict[str, str]] = None) -> Path:
    env = env if env is not None else dict(os.environ)
    configured = env.get("VENHO_BACKUP_DIR")
    return Path(configured).expanduser() if configured else DEFAULT_BACKUP_DIR


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_row_counts(db_path: Path) -> dict[str, int]:
    """Row count per user table -- the cheapest evidence that a restored
    database holds the same content, not just a structurally valid file."""
    if not db_path.exists():
        return {}
    with sqlite3.connect(db_path) as db:
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def _snapshot_database(source: Path, destination: Path) -> None:
    """sqlite3's online backup API, not a file copy.

    growth.db is written by CLI runs that may overlap with a backup (the
    dashboard dispatching while a cron generates); copying the file mid-write
    yields a torn database, while `Connection.backup` takes a consistent
    snapshot under the same locking the writers use.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def create_backup(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    backup_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Take one snapshot; returns its manifest."""
    root = data_root / project
    destination_root = backup_dir or backup_dir_from_env()
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = destination_root / project / f"snapshot-{timestamp}"
    # Second-resolution names collide when two backups run in the same second
    # (a manual run right after the scheduled one), and the later would
    # silently overwrite the earlier -- losing a snapshot at exactly the
    # moment someone was being careful.
    suffix = 1
    while snapshot_dir.exists():
        snapshot_dir = destination_root / project / f"snapshot-{timestamp}-{suffix}"
        suffix += 1
    cas_dir = destination_root / project / CAS_DIRNAME
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    cas_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "version": 1,
        "project": project,
        "created_at": (now or datetime.now(timezone.utc)).isoformat(),
        "source_root": str(root.resolve()) if root.exists() else str(root),
        "database": None,
        "files": [],
        "artifacts": [],
    }

    db_source = root / _DB_PATH
    if db_source.exists():
        snapshot_db = snapshot_dir / SNAPSHOT_DB_NAME
        _snapshot_database(db_source, snapshot_db)
        manifest["database"] = {
            "path": str(_DB_PATH),
            "sha256": _sha256(snapshot_db),
            "row_counts": _table_row_counts(snapshot_db),
        }

    files_dir = snapshot_dir / "files"
    for relative in _STATE_FILES:
        source = root / relative
        if not source.exists():
            continue
        target = files_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest["files"].append({"path": str(relative), "sha256": _sha256(target)})
    for relative_dir in _STATE_DIRS:
        source_dir = root / relative_dir
        if not source_dir.exists():
            continue
        for source in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            relative = source.relative_to(root)
            target = files_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest["files"].append({"path": str(relative), "sha256": _sha256(target)})

    artifacts_root = root / _ARTIFACTS_DIR
    if artifacts_root.exists():
        for source in sorted(p for p in artifacts_root.rglob("*") if p.is_file()):
            digest = _sha256(source)
            blob = cas_dir / digest[:2] / digest
            if not blob.exists():
                blob.parent.mkdir(parents=True, exist_ok=True)
                # Copy to a temp name first so an interrupted backup can never
                # leave a truncated blob that later verifies as the real thing.
                with tempfile.NamedTemporaryFile(dir=blob.parent, delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                shutil.copy2(source, tmp_path)
                tmp_path.replace(blob)
            manifest["artifacts"].append(
                {"path": str(source.relative_to(root)), "sha256": digest, "size": source.stat().st_size}
            )

    manifest["counts"] = {
        "files": len(manifest["files"]),
        "artifacts": len(manifest["artifacts"]),
        "artifact_bytes": sum(item["size"] for item in manifest["artifacts"]),
    }
    (snapshot_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["snapshot_dir"] = str(snapshot_dir)
    return manifest


def list_backups(*, project: str = "venho_hotel", backup_dir: Optional[Path] = None) -> list[Path]:
    root = (backup_dir or backup_dir_from_env()) / project
    if not root.exists():
        return []
    return sorted(p for p in root.glob("snapshot-*") if (p / MANIFEST_NAME).exists())


def latest_backup(*, project: str = "venho_hotel", backup_dir: Optional[Path] = None) -> Optional[Path]:
    backups = list_backups(project=project, backup_dir=backup_dir)
    return backups[-1] if backups else None


def verify_restore(
    snapshot_dir: Path,
    *,
    backup_dir: Optional[Path] = None,
    restore_to: Optional[Path] = None,
) -> dict[str, Any]:
    """Restore the snapshot into a scratch tree and prove it came back whole.

    Returns `{"ok": bool, "errors": [...], ...}` rather than raising, so a
    scheduled verify can alert on the report instead of a traceback.
    """
    snapshot_dir = Path(snapshot_dir)
    errors: list[str] = []
    manifest_path = snapshot_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return {"ok": False, "errors": [f"no manifest at {manifest_path}"], "snapshot_dir": str(snapshot_dir)}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cas_dir = (backup_dir or snapshot_dir.parent.parent) / manifest["project"] / CAS_DIRNAME
    if not cas_dir.exists():
        cas_dir = snapshot_dir.parent / CAS_DIRNAME

    scratch = Path(restore_to) if restore_to else Path(tempfile.mkdtemp(prefix="venho-restore-"))
    scratch.mkdir(parents=True, exist_ok=True)

    database_ok = None
    if manifest.get("database"):
        snapshot_db = snapshot_dir / SNAPSHOT_DB_NAME
        restored_db = scratch / SNAPSHOT_DB_NAME
        if not snapshot_db.exists():
            errors.append("snapshot database file is missing")
        else:
            shutil.copy2(snapshot_db, restored_db)
            with sqlite3.connect(restored_db) as db:
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                errors.append(f"restored database failed integrity_check: {integrity}")
            restored_counts = _table_row_counts(restored_db)
            expected_counts = manifest["database"].get("row_counts") or {}
            if restored_counts != expected_counts:
                errors.append(f"row counts differ after restore: {expected_counts} != {restored_counts}")
            database_ok = not errors

    files_verified = 0
    for entry in manifest.get("files", []):
        source = snapshot_dir / "files" / entry["path"]
        if not source.exists():
            errors.append(f"missing backed-up file: {entry['path']}")
            continue
        if _sha256(source) != entry["sha256"]:
            errors.append(f"checksum mismatch: {entry['path']}")
            continue
        target = scratch / "files" / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        files_verified += 1

    artifacts_verified = 0
    for entry in manifest.get("artifacts", []):
        blob = cas_dir / entry["sha256"][:2] / entry["sha256"]
        if not blob.exists():
            errors.append(f"missing artifact blob for {entry['path']}")
            continue
        if _sha256(blob) != entry["sha256"]:
            errors.append(f"artifact checksum mismatch: {entry['path']}")
            continue
        artifacts_verified += 1

    return {
        "ok": not errors,
        "errors": errors,
        "snapshot_dir": str(snapshot_dir),
        "restored_to": str(scratch),
        "database_ok": database_ok,
        "files_verified": files_verified,
        "files_expected": len(manifest.get("files", [])),
        "artifacts_verified": artifacts_verified,
        "artifacts_expected": len(manifest.get("artifacts", [])),
    }


def prune_backups(
    *, project: str = "venho_hotel", backup_dir: Optional[Path] = None, keep: int = 30
) -> dict[str, Any]:
    """Drop the oldest snapshots beyond `keep`, then garbage-collect CAS blobs
    no surviving manifest references. Snapshots are cheap; the blobs are not.
    """
    root = (backup_dir or backup_dir_from_env()) / project
    snapshots = list_backups(project=project, backup_dir=backup_dir)
    removed = []
    for snapshot in snapshots[: max(0, len(snapshots) - keep)]:
        shutil.rmtree(snapshot, ignore_errors=True)
        removed.append(snapshot.name)

    referenced: set[str] = set()
    for snapshot in list_backups(project=project, backup_dir=backup_dir):
        manifest = json.loads((snapshot / MANIFEST_NAME).read_text(encoding="utf-8"))
        referenced.update(entry["sha256"] for entry in manifest.get("artifacts", []))
    cas_dir = root / CAS_DIRNAME
    blobs_removed = 0
    if cas_dir.exists():
        for blob in cas_dir.rglob("*"):
            if blob.is_file() and blob.name not in referenced:
                blob.unlink()
                blobs_removed += 1
    return {"snapshots_removed": removed, "blobs_removed": blobs_removed, "snapshots_kept": len(list_backups(project=project, backup_dir=backup_dir))}
