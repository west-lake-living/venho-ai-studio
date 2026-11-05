from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from growth_engine.adapters.inbound.cli.main import app
from growth_engine.adapters.outbound.legacy.importer import LegacyImportDryRun, dry_run_import
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
FIXTURE_NOTE = "cần thay bằng fixture thật từ P0-T03/P0-T04"
CLI_RUNNER = CliRunner()


def _source_directory(path: Path) -> tuple[Path, int]:
    source = path / "legacy-source"
    source.mkdir()
    publications = [
        {
            "publication_id": "old-facebook",
            "platform": "facebook",
            "status": "PUBLISHED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "platform_post_id": "1124616474074140_101",
            "slot_id": "slot-old-facebook",
        },
        {
            "publication_id": "untracked-facebook",
            "platform": "facebook",
            "status": "PUBLISHED",
            "created_at": "2026-11-04T09:00:00+07:00",
            "platform_post_id": "synthetic-page-post",
            "slot_id": "slot-untracked-facebook",
        },
        {
            "publication_id": "published-after-cutover-facebook",
            "platform": "facebook",
            "status": "PUBLISHED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "published_at": "2026-11-04T09:00:00+07:00",
            "platform_post_id": "synthetic-late-page-post",
            "slot_id": "slot-published-after-cutover",
        },
        {
            "publication_id": "instagram-post",
            "platform": "instagram",
            "status": "PUBLISHED",
            "created_at": "2026-11-04T10:00:00+07:00",
            "platform_post_id": "synthetic-instagram-post",
            "slot_id": "slot-instagram",
        },
        {
            "publication_id": "gateway-facebook",
            "platform": "facebook",
            "status": "GATEWAY_ACCEPTED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "platform_post_id": None,
            "slot_id": "slot-gateway",
        },
        {
            "publication_id": "placeholder-facebook",
            "platform": "facebook",
            "status": "PUBLISHED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "platform_post_id": "3. Post ID",
            "slot_id": "slot-placeholder",
        },
        {
            "publication_id": "old-approved-facebook",
            "platform": "facebook",
            "status": "APPROVED_SCHEDULED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "platform_post_id": None,
            "slot_id": "slot-approved",
        },
        {
            "publication_id": "threads-history",
            "platform": "threads",
            "status": "GATEWAY_ACCEPTED",
            "created_at": "2026-11-02T09:00:00+07:00",
            "platform_post_id": None,
            "slot_id": "slot-threads",
        },
        {
            "publication_id": "manual-facebook",
            "source_name": "manual_post",
            "platform": "facebook",
            "status": "PUBLISHED",
            "created_at": "2026-11-04T09:00:00+07:00",
            "platform_post_id": "synthetic-manual-post",
            "slot_id": "slot-manual",
        },
    ]
    slots = [
        {
            "slot_id": publication["slot_id"],
            "slot_date": (publication.get("published_at") or publication["created_at"])[:10],
            "slot_time": f"09:{index:02d}",
            "lane": "weekly",
            "status": "COMPLETED",
        }
        for index, publication in enumerate(publications)
    ]
    (source / "publication_registry.json").write_text(
        json.dumps(
            {"_synthetic": True, "_note": FIXTURE_NOTE, "publications": publications},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (source / "slots_snapshot.json").write_text(
        json.dumps({"_synthetic": True, "_note": FIXTURE_NOTE, "records": slots}),
        encoding="utf-8",
    )
    return source, len(publications) + len(slots)


def _import(source: Path, database: Path, report: Path) -> None:
    connection = connect(database)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
    finally:
        connection.close()
    dry_run_import(source, database, report)


def test_legacy_import_is_idempotent_and_keeps_every_raw_row(tmp_path: Path) -> None:
    source, expected_records = _source_directory(tmp_path)
    database = tmp_path / "dry-run.db"
    report = tmp_path / "report.md"

    _import(source, database, report)
    first_count = _count(database, "legacy_imports")
    _import(source, database, report)

    assert first_count == expected_records
    assert _count(database, "legacy_imports") == expected_records
    assert _count(database, "deliveries") == 7
    assert _count(database, "approval_decisions") == 0
    assert _count(database, "outbox_commands") == 0
    assert _count(database, "channels_enabled") == 0
    report_text = report.read_text(encoding="utf-8")
    assert "GATEWAY_ACCEPTED" in report_text
    assert "CLOSED_UNRESOLVED" in report_text


def test_legacy_import_maps_channels_and_keeps_uncertain_posts_unverified(
    tmp_path: Path,
) -> None:
    source, _ = _source_directory(tmp_path)
    database = tmp_path / "dry-run.db"
    report = tmp_path / "report.md"
    _import(source, database, report)

    connection = connect(database)
    try:
        channels = {
            row["id"]: row["channel_key"]
            for row in connection.execute("SELECT id, channel_key FROM channels")
        }
        deliveries = {
            row["id"]: row
            for row in connection.execute(
                """SELECT d.id, d.state, d.platform_post_id, d.channel_id, c.channel_key,
                          l.source_key, l.issue_code
                   FROM legacy_imports l
                   JOIN deliveries d ON d.id=l.mapped_delivery_id
                   JOIN channels c ON c.id=d.channel_id"""
            )
        }
        by_source_key = {row["source_key"]: row for row in deliveries.values()}

        assert channels[by_source_key["old-facebook"]["channel_id"]] == "fb_hanoi"
        assert by_source_key["untracked-facebook"]["channel_key"] == "fb_venho"
        assert by_source_key["published-after-cutover-facebook"]["channel_key"] == "fb_venho"
        assert by_source_key["instagram-post"]["channel_key"] == "ig_venho"
        assert by_source_key["gateway-facebook"]["state"] == "LEGACY_UNVERIFIED"
        assert by_source_key["gateway-facebook"]["issue_code"] == "CLOSED_UNRESOLVED"
        assert by_source_key["placeholder-facebook"]["state"] == "LEGACY_UNVERIFIED"
        assert by_source_key["placeholder-facebook"]["issue_code"] == "PLACEHOLDER_POST_ID"
        assert by_source_key["untracked-facebook"]["state"] == "LEGACY_UNVERIFIED"
        assert by_source_key["untracked-facebook"]["issue_code"] == "UNTRACKED_PAGE"
        assert by_source_key["old-approved-facebook"]["state"] == "IN_REVIEW"
        assert by_source_key["old-approved-facebook"]["issue_code"] == "APPROVAL_NOT_RESTORED"

        history_only = {
            row["source_key"]: row["mapped_delivery_id"]
            for row in connection.execute(
                "SELECT source_key, mapped_delivery_id FROM legacy_imports "
                "WHERE source_name='publication_registry.json'"
            )
        }
        assert history_only["threads-history"] is None
        manual = connection.execute(
            "SELECT mapped_delivery_id FROM legacy_imports WHERE source_name='manual_post' "
            "AND source_key='manual-facebook'"
        ).fetchone()
        assert manual["mapped_delivery_id"] is None
    finally:
        connection.close()


def test_legacy_import_cli_routes_dry_run_and_apply_to_injected_service(tmp_path: Path) -> None:
    source, _ = _source_directory(tmp_path)
    report = tmp_path / "report.md"

    class Service:
        def __init__(self) -> None:
            self.call: tuple[Path, Path] | None = None

        def run(self, source_dir: Path, report_path: Path) -> str:
            self.call = (source_dir, report_path)
            return "dry-run complete"

        def apply(self, source_dir: Path, database_path: Path, report_path: Path) -> str:
            self.call = (source_dir, database_path, report_path)
            return "apply complete"

    service = Service()
    result = CLI_RUNNER.invoke(
        app,
        ["legacy-import", "--dry-run", "--source", str(source), "--report", str(report)],
        obj={"legacy_import_service": service},
    )
    assert result.exit_code == 0
    assert "dry-run complete" in result.output
    assert service.call == (source, report)

    applied = CLI_RUNNER.invoke(
        app,
        [
            "legacy-import", "--apply", "--source", str(source), "--target-db",
            str(tmp_path / "target.sqlite"), "--report", str(report),
        ],
        obj={"legacy_import_service": service},
    )
    assert applied.exit_code == 0
    assert "apply complete" in applied.output
    assert service.call == (source, tmp_path / "target.sqlite", report)

    missing_target = CLI_RUNNER.invoke(
        app,
        ["legacy-import", "--apply", "--source", str(source), "--report", str(report)],
        obj={"legacy_import_service": service},
    )
    assert missing_target.exit_code != 0
    assert "--apply requires --target-db" in missing_target.output


def test_legacy_import_apply_is_idempotent_on_synthetic_sqlite_fixture(tmp_path: Path) -> None:
    source, expected_records = _source_directory(tmp_path)
    database = tmp_path / "existing-v2.sqlite"
    report = tmp_path / "apply-report.md"
    connection = connect(database)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="legacy-apply-integration")
    finally:
        connection.close()

    service = LegacyImportDryRun()
    first = service.apply(source, database, report)
    first_raw_count = _count(database, "legacy_imports")
    second = service.apply(source, database, report)

    assert first_raw_count == expected_records
    assert _count(database, "legacy_imports") == expected_records
    assert _count(database, "deliveries") == 7
    assert _count(database, "approval_decisions") == 0
    assert _count(database, "outbox_commands") == 0
    assert _count(database, "channels_enabled") == 0
    assert "# GC2 legacy import apply" in first
    assert "The target v2 database was updated." in first
    assert "# GC2 legacy import apply" in second
    assert report.read_text(encoding="utf-8") == second


def test_legacy_import_apply_requires_existing_database(tmp_path: Path) -> None:
    source, _ = _source_directory(tmp_path)
    report = tmp_path / "apply-report.md"

    result = CLI_RUNNER.invoke(
        app,
        [
            "legacy-import", "--apply", "--source", str(source), "--target-db",
            str(tmp_path / "missing.sqlite"), "--report", str(report),
        ],
        obj={"legacy_import_service": LegacyImportDryRun()},
    )

    assert result.exit_code != 0
    assert "existing database file" in result.output
    assert not (tmp_path / "missing.sqlite").exists()


def _count(database: Path, table: str) -> int:
    connection = connect(database)
    try:
        if table == "channels_enabled":
            return int(connection.execute("SELECT count(*) FROM channels WHERE enabled=1").fetchone()[0])
        return int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        connection.close()
