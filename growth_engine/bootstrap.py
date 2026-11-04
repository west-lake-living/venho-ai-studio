from __future__ import annotations

import os
import logging
import random
import sqlite3
import sys
import tempfile
import time
from uuid import uuid4
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

class _SystemClock:
    def now_ms(self) -> int:
        return time.time_ns() // 1_000_000


class _UuidIds:
    def new_id(self) -> str:
        return str(uuid4())


class _LazyCapabilityIssuer:
    def __init__(self, key_config: str) -> None:
        self._key_config = key_config
        self._manager: Any | None = None

    @property
    def active_key_id(self) -> str:
        self._load_manager()
        return self._manager.active_key_id

    def issue(self, claims: Any, *, key_id: str | None = None) -> str:
        self._load_manager()
        return self._manager.issue(claims, key_id=key_id)

    def _load_manager(self) -> None:
        if self._manager is None:
            module = import_module("growth_engine.adapters.outbound.security.capability_tokens")
            self._manager = module.CapabilityTokenManager(module.parse_key_ring(self._key_config))


class _LazyMediaUrlIssuer:
    def __init__(self, public_base_url: str, key_config: str) -> None:
        self._public_base_url = public_base_url
        self._key_config = key_config
        self._issuer: Any | None = None

    def media_url(self, sha256: str, command_id: str, expires_at_ms: int) -> str:
        if self._issuer is None:
            module = import_module("growth_engine.adapters.outbound.media.signed_urls")
            self._issuer = module.SignedMediaUrlIssuer(self._public_base_url, self._key_config)
        return self._issuer.media_url(sha256, command_id, expires_at_ms)


MIGRATIONS = Path(__file__).parent / "adapters" / "outbound" / "persistence" / "sqlite" / "migrations"
REQUIRED_CHANNELS = frozenset({"fb_hanoi", "fb_venho", "ig_venho"})
_REQUIRED = "REQUIRED_FROM_P0"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    pre_switch: bool = False

    @property
    def failed(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks)

    def render(self) -> str:
        label = "venho-engine doctor --pre-switch" if self.pre_switch else "venho-engine doctor"
        lines = [label, "", "| Kiểm tra | Trạng thái | Chi tiết |", "|---|---|---|"]
        lines.extend(
            f"| {check.name} | **{check.status}** | {check.detail} |" for check in self.checks
        )
        return "\n".join(lines)


class SqliteMigrationService:
    def __init__(self, connect: Callable[[str | Path], sqlite3.Connection], migration_runner: Any) -> None:
        self._connect = connect
        self._migration_runner = migration_runner

    def run(self, db_path: Path, check: bool) -> str:
        connection = self._connect(db_path)
        try:
            runner = self._migration_runner(MIGRATIONS)
            if check:
                versions = runner.check(connection)
                return f"Schema is current at version {max(versions, default=0)}."
            count = runner.apply(connection, application_version="venho-engine")
            versions = runner.check(connection)
            return f"Applied {count} migration(s); schema version {max(versions, default=0)}."
        finally:
            connection.close()


class DoctorService:
    def __init__(
        self,
        settings: Any,
        *,
        connect: Callable[[str | Path], sqlite3.Connection],
        migration_runner: Any,
        sqlite_version_check: Callable[[tuple[int, ...]], None],
        sqlite_version_error: type[Exception],
    ) -> None:
        self.settings = settings
        self._connect = connect
        self._migration_runner = migration_runner
        self._sqlite_version_check = sqlite_version_check
        self._sqlite_version_error = sqlite_version_error

    def run(self, *, pre_switch: bool = False) -> DoctorReport:
        checks: list[DoctorCheck] = []
        checks.extend(self._runtime_checks())
        connection, connection_error = self._database_connection()
        if connection is None:
            checks.extend(
                (
                    DoctorCheck("SQLite PRAGMA", "FAIL", "Không mở được cơ sở dữ liệu."),
                    DoctorCheck("Schema version", "FAIL", "Không kiểm tra được schema."),
                    DoctorCheck("Channel config", "WARN", "Chưa đọc được cấu hình kênh."),
                )
            )
        else:
            try:
                checks.append(self._pragma_check(connection))
                checks.append(self._schema_check(connection))
                checks.append(self._channel_check(connection))
            finally:
                connection.close()
        checks.extend(
            (
                self._media_root_check(),
                self._settings_check(),
                self._clock_check(),
                self._publish_lock_check(),
                self._heartbeat_check(),
                self._backup_check(),
            )
        )
        if connection_error and not any(check.status == "FAIL" for check in checks):
            checks.append(DoctorCheck("Database", "FAIL", "Không mở được cơ sở dữ liệu."))
        return DoctorReport(tuple(checks), pre_switch=pre_switch)

    def _runtime_checks(self) -> list[DoctorCheck]:
        python_ok = sys.version_info >= (3, 11)
        try:
            self._sqlite_version_check(sqlite3.sqlite_version_info)
            sqlite_ok = True
        except self._sqlite_version_error:
            sqlite_ok = False
        status = "PASS" if python_ok and sqlite_ok else "FAIL"
        detail = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}; SQLite {sqlite3.sqlite_version}."
        return [DoctorCheck("Python & SQLite version", status, detail)]

    def _database_connection(self) -> tuple[sqlite3.Connection | None, bool]:
        if _is_required(self.settings.db_path):
            return None, True
        try:
            return self._connect(self.settings.db_path), False
        except (OSError, sqlite3.Error, self._sqlite_version_error):
            return None, True

    @staticmethod
    def _pragma_check(connection: sqlite3.Connection) -> DoctorCheck:
        values = {
            "foreign_keys": int(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
            "journal_mode": str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
            "busy_timeout": int(connection.execute("PRAGMA busy_timeout").fetchone()[0]),
        }
        expected = {"foreign_keys": 1, "journal_mode": "wal", "synchronous": 2, "busy_timeout": 5000}
        ok = values == expected
        return DoctorCheck("SQLite PRAGMA", "PASS" if ok else "FAIL", str(values))

    def _schema_check(self, connection: sqlite3.Connection) -> DoctorCheck:
        try:
            versions = self._migration_runner(MIGRATIONS).check(connection)
        except Exception:
            return DoctorCheck("Schema version", "FAIL", "Migration chưa đầy đủ hoặc checksum không khớp.")
        return DoctorCheck(
            "Schema version",
            "PASS",
            f"v{max(versions, default=0)} ({len(versions)} migration).",
        )

    @staticmethod
    def _channel_check(connection: sqlite3.Connection) -> DoctorCheck:
        try:
            rows = connection.execute(
                """SELECT c.channel_key, c.remote_account_id, c.enabled,
                          count(cc.id) AS config_count
                   FROM channels c LEFT JOIN channel_configs cc ON cc.channel_id=c.id
                   GROUP BY c.id"""
            ).fetchall()
        except sqlite3.Error:
            return DoctorCheck("Channel config", "WARN", "Schema chưa có cấu hình kênh.")
        by_key = {str(row["channel_key"]): row for row in rows}
        missing = sorted(REQUIRED_CHANNELS - set(by_key))
        placeholders = sorted(
            key
            for key, row in by_key.items()
            if _is_required(str(row["remote_account_id"])) and int(row["enabled"])
        )
        no_config = sorted(key for key, row in by_key.items() if int(row["config_count"]) < 1)
        if placeholders:
            return DoctorCheck("Channel config", "FAIL", f"Kênh bật nhưng thiếu remote ID: {', '.join(placeholders)}.")
        if missing or no_config:
            detail = []
            if missing:
                detail.append(f"thiếu {', '.join(missing)}")
            if no_config:
                detail.append(f"chưa có config {', '.join(no_config)}")
            return DoctorCheck("Channel config", "WARN", "; ".join(detail) + ".")
        return DoctorCheck("Channel config", "PASS", f"{len(by_key)} kênh có channel_config.")

    def _media_root_check(self) -> DoctorCheck:
        if _is_required(self.settings.media_root):
            return DoctorCheck("Media root writable", "FAIL", "GE_MEDIA_ROOT chưa cấu hình.")
        root = Path(self.settings.media_root)
        if not root.is_dir():
            return DoctorCheck("Media root writable", "FAIL", "Thư mục media chưa tồn tại.")
        try:
            with tempfile.NamedTemporaryFile(prefix=".doctor-", dir=root, delete=True):
                pass
        except OSError:
            return DoctorCheck("Media root writable", "FAIL", "Không ghi được vào thư mục media.")
        return DoctorCheck("Media root writable", "PASS", "Thư mục media ghi được.")

    def _settings_check(self) -> DoctorCheck:
        values: dict[str, object] = {
            "GE_DB_PATH": self.settings.db_path,
            "GE_MEDIA_ROOT": self.settings.media_root,
            "GE_PUBLIC_BASE_URL": self.settings.public_base_url,
            "GE_CAPABILITY_KEYS": self.settings.capability_keys,
            "GE_SERVICE_TOKENS": self.settings.service_tokens,
        }
        values.update({f"GE_MAKE_WEBHOOK_URL_{key}": value for key, value in self.settings.make_webhook_urls.items()})
        values.update({f"GE_META_READ_TOKEN_{key}": value for key, value in self.settings.meta_read_tokens.items()})
        values.update({f"GE_TELEGRAM_{key}": value for key, value in self.settings.telegram.items()})
        missing = sorted(name for name, value in values.items() if _is_required(str(value)))
        status = "FAIL" if missing else "PASS"
        detail = "Chưa cấu hình: " + ", ".join(missing) + "." if missing else "Không còn giá trị rỗng/REQUIRED_FROM_P0."
        return DoctorCheck("Settings complete", status, detail)

    @staticmethod
    def _clock_check() -> DoctorCheck:
        return DoctorCheck("Clock skew", "WARN", "Chưa có nguồn thời gian chuẩn để đo độ lệch.")

    def _publish_lock_check(self) -> DoctorCheck:
        if _is_required(self.settings.db_path):
            return DoctorCheck("Publish lane instance", "WARN", "Chưa xác định đường dẫn state.")
        lock_path = Path(self.settings.db_path).parent / "publish.lock"
        if not lock_path.exists():
            return DoctorCheck("Publish lane instance", "WARN", "Chưa có publish worker/lock.")
        try:
            import fcntl

            descriptor = os.open(lock_path, os.O_RDONLY)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        except BlockingIOError:
            return DoctorCheck("Publish lane instance", "FAIL", "Đang có publish worker giữ lock.")
        except OSError:
            return DoctorCheck("Publish lane instance", "WARN", "Không kiểm tra được publish lock.")
        return DoctorCheck("Publish lane instance", "PASS", "Không có instance khác giữ lock.")

    @staticmethod
    def _heartbeat_check() -> DoctorCheck:
        return DoctorCheck("Heartbeat age", "WARN", "Heartbeat worker chưa được triển khai ở pha P2.")

    def _backup_check(self) -> DoctorCheck:
        if _is_required(self.settings.db_path):
            return DoctorCheck("Backup age", "WARN", "Chưa xác định thư mục backup.")
        parent = Path(self.settings.db_path).parent
        backups = [path for path in parent.glob("*.bak*") if path.is_file()]
        if not backups:
            return DoctorCheck("Backup age", "WARN", "Chưa tìm thấy backup cạnh DB.")
        newest = max(backups, key=lambda path: path.stat().st_mtime)
        age_seconds = max(0, int(time.time() - newest.stat().st_mtime))
        status = "PASS" if age_seconds <= 2 * 60 * 60 else "FAIL"
        return DoctorCheck("Backup age", status, f"Backup mới nhất {age_seconds // 60} phút trước.")


@dataclass(frozen=True)
class Container:
    settings: Any
    uow_factory: Callable[[], Any]
    migration_service: SqliteMigrationService
    legacy_import_service: Any
    doctor_service: DoctorService
    readiness_check: Callable[[], tuple[bool, int | None]]
    ingest_candidate: Any
    decide_candidate: Any
    expire_candidates: Any
    enqueue_due: Any
    expire_overdue: Any
    dispatch_store: Any
    dispatch_outbox: Any
    publishing_policy: Any
    publish_lane: Any


def build_container(settings: Any) -> Container:
    connection_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.connection"
    )
    migrator_adapter = import_module("growth_engine.adapters.outbound.persistence.sqlite.migrator")
    uow_adapter = import_module("growth_engine.adapters.outbound.persistence.sqlite.uow")
    candidate_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.candidate_store"
    )
    ingest_adapter = import_module("growth_engine.application.content.ingest_candidate")
    decide_adapter = import_module("growth_engine.application.content.decide_candidate")
    expire_adapter = import_module("growth_engine.application.content.expire_candidates")
    enqueue_adapter = import_module("growth_engine.application.publishing.enqueue_due")
    overdue_adapter = import_module("growth_engine.application.publishing.expire_overdue")
    scheduler_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.repositories.publish_scheduler"
    )
    dispatch_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.repositories.dispatch"
    )
    dispatch_adapter = import_module("growth_engine.application.publishing.dispatch_outbox")
    policy_adapter = import_module("growth_engine.domain.publishing.window")
    transport_adapter = import_module("growth_engine.adapters.outbound.make.http_transport")
    envelope_adapter = import_module("growth_engine.adapters.outbound.make.envelope")
    worker_loop_adapter = import_module("growth_engine.adapters.inbound.workers.loop")
    publish_lane_adapter = import_module("growth_engine.adapters.inbound.workers.publish_lane")
    legacy_adapter = import_module("growth_engine.adapters.outbound.legacy.importer")
    connect = connection_adapter.connect
    migration_runner_type = migrator_adapter.MigrationRunner
    connection_factory = lambda: connect(settings.db_path)
    migration_runner = migration_runner_type(MIGRATIONS)

    def readiness_check() -> tuple[bool, int | None]:
        connection: sqlite3.Connection | None = None
        try:
            connection = connection_factory()
            versions = migration_runner.check(connection)
            return True, max(versions, default=0)
        except Exception:
            return False, None
        finally:
            if connection is not None:
                connection.close()

    uow_factory = lambda: uow_adapter.SqliteUnitOfWork(connection_factory)
    candidate_store = candidate_store_adapter.SqliteCandidateStore(uow_factory)
    clock = _SystemClock()
    ids = _UuidIds()
    channel_environment = "production" if settings.env.lower() == "production" else "test"
    token_issuer = _LazyCapabilityIssuer(settings.capability_keys)
    scheduler_store = scheduler_store_adapter.SqlitePublishSchedulerStore(
        uow_factory, channel_environment, lambda: token_issuer.active_key_id
    )
    enqueue_due = enqueue_adapter.EnqueueDue(scheduler_store, token_issuer, ids)
    expire_overdue = overdue_adapter.ExpireOverdue(scheduler_store, ids)
    publishing_policy = policy_adapter.PublishingPolicy(
        window_minutes=30,
        grant_ttl_seconds=60,
        receipt_grace_minutes=15,
        redeliver_after_ack_minutes=5,
        max_transport_attempts=8,
        verify_delay_minutes=5,
        unknown_escalation_minutes=60,
    )
    dispatch_store = dispatch_store_adapter.SqliteDispatchStore(
        uow_factory,
        channel_environment,
        settings.make_webhook_urls,
        token_issuer,
        redeliver_after_ack_minutes=publishing_policy.redeliver_after_ack_minutes,
    )
    dispatch_outbox = dispatch_adapter.DispatchOutbox(
        dispatch_store,
        transport_adapter.HttpTransport(clock),
        _LazyMediaUrlIssuer(settings.public_base_url, settings.capability_keys),
        envelope_adapter.MakeEnvelopeBuilder(),
        policy=publishing_policy,
        rng=random.uniform,
    )
    worker_tasks = publish_lane_adapter.build_publish_tasks(
        {
            "enqueue_due": lambda: enqueue_due.execute(clock.now_ms()),
            "expire_overdue": lambda: expire_overdue.execute(clock.now_ms()),
            "dispatch_outbox": lambda: dispatch_outbox.execute(clock.now_ms()),
        }
    )
    worker_loop = worker_loop_adapter.WorkerLoop(
        worker_tasks,
        clock,
        on_error=lambda task, error: logging.getLogger("growth_engine.publish").error(
            "publish task failed: task=%s error_type=%s", task.name, type(error).__name__
        ),
    )
    publish_lane = publish_lane_adapter.PublishLane(
        worker_loop,
        Path(settings.db_path).parent / "publish.lock",
    )
    return Container(
        settings=settings,
        uow_factory=uow_factory,
        migration_service=SqliteMigrationService(connect, migration_runner_type),
        legacy_import_service=legacy_adapter.LegacyImportDryRun(),
        doctor_service=DoctorService(
            settings,
            connect=connect,
            migration_runner=migration_runner_type,
            sqlite_version_check=connection_adapter.check_sqlite_version,
            sqlite_version_error=connection_adapter.SQLiteVersionError,
        ),
        readiness_check=readiness_check,
        ingest_candidate=ingest_adapter.IngestCandidate(candidate_store, clock, ids),
        decide_candidate=decide_adapter.DecideCandidate(candidate_store, clock, ids),
        expire_candidates=expire_adapter.ExpireCandidates(candidate_store, clock),
        enqueue_due=enqueue_due,
        expire_overdue=expire_overdue,
        dispatch_store=dispatch_store,
        dispatch_outbox=dispatch_outbox,
        publishing_policy=publishing_policy,
        publish_lane=publish_lane,
    )


def _is_required(value: str) -> bool:
    return not value.strip() or _REQUIRED in value
