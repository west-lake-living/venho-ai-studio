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


class _NoVerifiedMakeErrorClasses:
    def retryable_for(self, error_class: str) -> bool | None:
        return None


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

    def verify(self, token: str, audience: str, now_ms: int) -> Any:
        self._load_manager()
        return self._manager.verify(token, audience, now_ms)

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


class _LazyLocalMediaVerifier:
    def __init__(self, media_root: str) -> None:
        self._media_root = media_root
        self._store: Any | None = None

    def verify(self, object_key: str, sha256: str) -> bool:
        if _is_required(self._media_root):
            return False
        if self._store is None:
            module = import_module("growth_engine.adapters.outbound.media.local_store")
            self._store = module.LocalMediaStore(Path(self._media_root))
        return self._store.verify(object_key, sha256)


class _LazyLocalMediaWriter:
    def __init__(self, media_root: str) -> None:
        self._media_root = media_root
        self._store: Any | None = None

    def put_original(self, stream: Any, *, max_bytes: int) -> Any:
        if _is_required(self._media_root):
            raise ValueError("configure GE_MEDIA_ROOT before ingesting generated images")
        if self._store is None:
            module = import_module("growth_engine.adapters.outbound.media.local_store")
            self._store = module.LocalMediaStore(Path(self._media_root))
        return self._store.put_original(stream, max_bytes=max_bytes)


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
    analytics_views: Any
    generation_store: Any
    review_store: Any
    review_data_reader: Any
    ensure_slots: Any
    generate_package: Any
    run_lanes: Any
    readiness_check: Callable[[], tuple[bool, int | None]]
    ingest_candidate: Any
    decide_candidate: Any
    expire_candidates: Any
    enqueue_due: Any
    expire_overdue: Any
    authorize_publish: Any
    receive_receipt: Any
    apply_receipt: Any
    watch_receipt_timeouts: Any
    receipt_store: Any
    dispatch_store: Any
    dispatch_outbox: Any
    publishing_policy: Any
    publish_lane: Any
    jobs_lane: Any
    collect_metrics: Any | None
    backup_service: Any
    restore_service: Any


def build_container(settings: Any, *, metrics_source: Any | None = None) -> Container:
    if (
        settings.env.lower() == "production"
        and metrics_source is not None
        and getattr(metrics_source, "source_kind", None) != "meta_graph"
    ):
        raise ValueError("production composition requires a meta_graph metrics source")
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
    authorize_adapter = import_module("growth_engine.application.publishing.authorize_publish")
    authorize_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.authorize_store"
    )
    receipt_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.receipt_store"
    )
    receive_receipt_adapter = import_module("growth_engine.application.publishing.receive_receipt")
    apply_receipt_adapter = import_module("growth_engine.application.publishing.apply_receipt")
    receipt_timeout_adapter = import_module("growth_engine.application.publishing.watch_receipt_timeouts")
    policy_adapter = import_module("growth_engine.domain.publishing.window")
    transport_adapter = import_module("growth_engine.adapters.outbound.make.http_transport")
    envelope_adapter = import_module("growth_engine.adapters.outbound.make.envelope")
    worker_loop_adapter = import_module("growth_engine.adapters.inbound.workers.loop")
    publish_lane_adapter = import_module("growth_engine.adapters.inbound.workers.publish_lane")
    heartbeat_adapter = import_module("growth_engine.application.ops.heartbeat")
    jobs_lane_adapter = import_module("growth_engine.adapters.inbound.workers.jobs_lane")
    lanes_adapter = import_module("growth_engine.application.content.run_lanes")
    ensure_slots_adapter = import_module("growth_engine.application.scheduling.ensure_slots")
    reserve_target_adapter = import_module("growth_engine.application.scheduling.reserve_target")
    generate_package_adapter = import_module("growth_engine.application.content.generate_package")
    lane_store_adapter = import_module("growth_engine.adapters.outbound.persistence.sqlite.lane_store")
    legacy_generator_adapter = import_module("growth_engine.adapters.outbound.legacy.generator_adapter")
    legacy_fact_adapter = import_module("growth_engine.adapters.outbound.legacy.fact_source")
    ingest_asset_adapter = import_module("growth_engine.application.media.ingest_asset")
    legacy_adapter = import_module("growth_engine.adapters.outbound.legacy.importer")
    backup_adapter = import_module("growth_engine.adapters.outbound.backup.sqlite_backup")
    restore_adapter = import_module("growth_engine.adapters.outbound.backup.restore")
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
    analytics_adapter = import_module("growth_engine.application.queries.analytics_views")
    generation_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.generation_store"
    )
    review_store_adapter = import_module(
        "growth_engine.adapters.outbound.persistence.sqlite.review_store"
    )
    analytics_views = analytics_adapter.AnalyticsViews(uow_factory)
    clock = _SystemClock()
    ids = _UuidIds()
    generation_store = generation_store_adapter.SqliteGenerationStore(uow_factory, ids)
    review_store = review_store_adapter.SqliteReviewStore(uow_factory, ids, clock)
    candidate_store = candidate_store_adapter.SqliteCandidateStore(uow_factory)
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
    authorize_store = authorize_store_adapter.SqliteAuthorizePublishStore(
        uow_factory, channel_environment, clock
    )
    authorize_publish = authorize_adapter.AuthorizePublish(
        authorize_store,
        token_issuer,
        _LazyLocalMediaVerifier(settings.media_root),
        clock,
        ids,
        publishing_policy,
    )
    receipt_store = receipt_store_adapter.SqliteReceiptStore(uow_factory)
    receive_receipt = receive_receipt_adapter.ReceiveReceipt(receipt_store, clock, ids)
    apply_receipt = apply_receipt_adapter.ApplyReceipt(
        receipt_store, clock, ids, _NoVerifiedMakeErrorClasses()
    )
    watch_receipt_timeouts = receipt_timeout_adapter.WatchReceiptTimeouts(
        receipt_store, clock, ids
    )

    def process_apply_receipts() -> None:
        for job_id, lease_token, receipt_id, correlation_id in receipt_store.claim_apply_jobs(
            clock.now_ms()
        ):
            try:
                apply_receipt.execute(receipt_id, correlation_id=correlation_id)
            except Exception as error:
                receipt_store.complete_apply_job(
                    job_id, lease_token, at_ms=clock.now_ms(), error_type=type(error).__name__
                )
                logging.getLogger("growth_engine.publish").error(
                    "receipt apply failed: error_type=%s", type(error).__name__
                )
            else:
                receipt_store.complete_apply_job(job_id, lease_token, at_ms=clock.now_ms())
    heartbeat = heartbeat_adapter.Heartbeat(
        settings.heartbeat_url,
        publish_lane_adapter.UrllibHeartbeatSender(),
    )
    worker_tasks = publish_lane_adapter.build_publish_tasks(
        {
            "enqueue_due": lambda: enqueue_due.execute(clock.now_ms()),
            "expire_overdue": lambda: expire_overdue.execute(clock.now_ms()),
            "dispatch_outbox": lambda: dispatch_outbox.execute(clock.now_ms()),
            "apply_receipts": process_apply_receipts,
            "receipt_timeouts": watch_receipt_timeouts.execute,
            "database_health": readiness_check,
            "heartbeat": heartbeat.execute,
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
    collect_metrics = None
    if metrics_source is not None:
        collector_adapter = import_module("growth_engine.application.analytics.collect_metrics")
        collect_metrics = collector_adapter.CollectMetrics(uow_factory, metrics_source, ids, clock)

    repo_root = Path(__file__).resolve().parents[1]
    cadence_policy, budget_policy, cost_estimates = _load_generation_policies(repo_root)
    ensure_slots = ensure_slots_adapter.EnsureSlots(generation_store, clock, ids)
    lane_store = lane_store_adapter.SqliteRunLanesStore(
        uow_factory,
        ensure_slots,
        cadence_policy,
        environment=channel_environment,
        timezone_name=cadence_policy.timezone,
    )
    lane_generation_store = generation_store_adapter.SqliteGenerationStore(
        uow_factory,
        ids,
        reserve_drafts=False,
    )
    generator = legacy_generator_adapter.LegacyGeneratorAdapter(repo_root=repo_root)
    fact_source = legacy_fact_adapter.LegacyFactSource(
        project="venho_hotel", data_root=repo_root / "data" / "projects"
    )
    asset_ingestor = ingest_asset_adapter.IngestAsset(
        uow_factory,
        _LazyLocalMediaWriter(settings.media_root),
        clock,
        ids,
    )
    generate_package = generate_package_adapter.GeneratePackage(
        lane_generation_store,
        generator,
        fact_source,
        asset_ingestor,
        clock,
        ids,
        budget_policy=budget_policy,
        cost_estimates=cost_estimates,
    )
    package_factory = jobs_lane_adapter.GeneratePackageLaneFactory(
        generate_package,
        lane_store,
        package_spec_hash=_generation_spec_hash(repo_root),
    )
    reserve_target = reserve_target_adapter.ReserveTarget(generation_store, clock, ids)
    run_lanes = lanes_adapter.RunLanes(lane_store, package_factory, reserve_target, clock)

    def report_jobs_error(task: Any, error: Exception) -> None:
        now_ms = clock.now_ms()
        incident_type = "JOBS_LANE_TASK_FAILED"
        incident = import_module("growth_engine.domain.ops.incident").Incident(
            id=ids.new_id(),
            type=incident_type,
            fingerprint=import_module("growth_engine.domain.ops.incident").incident_fingerprint(
                incident_type, None, task.name
            ),
            channel_id=None,
            ref=task.name,
            severity=import_module("growth_engine.domain.ops.incident").IncidentSeverity.HIGH,
            state=import_module("growth_engine.domain.ops.incident").IncidentState.OPEN,
            first_seen_at_ms=now_ms,
            last_seen_at_ms=now_ms,
        )
        with uow_factory().begin_immediate() as tx:
            tx.incidents.open_or_touch(
                incident,
                details_json=json.dumps({"error_class": type(error).__name__}, separators=(",", ":")),
            )
        logging.getLogger("growth_engine.jobs").error(
            "jobs lane task failed: task=%s error_type=%s", task.name, type(error).__name__
        )

    jobs_handlers = {
        "ensure_slots": lambda: lane_store.ensure_slots(clock.now_ms(), horizon_days=14),
        "weekly": lambda: run_lanes.run_weekly(horizon_days=14),
        "fast": lambda: run_lanes.run_fast(horizon_days=14),
        "replacement": lambda: run_lanes.run_replacement(horizon_days=14),
    }
    if collect_metrics is not None:
        jobs_handlers["metrics"] = lambda: collect_metrics.execute(clock.now_ms())
    jobs_tasks = jobs_lane_adapter.build_jobs_tasks(jobs_handlers)
    jobs_loop = worker_loop_adapter.WorkerLoop(
        jobs_tasks,
        clock,
        on_error=report_jobs_error,
    )
    jobs_lane = jobs_lane_adapter.JobsLane(jobs_loop)
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
        analytics_views=analytics_views,
        generation_store=generation_store,
        review_store=review_store,
        review_data_reader=review_store,
        ensure_slots=ensure_slots,
        generate_package=generate_package,
        run_lanes=run_lanes,
        readiness_check=readiness_check,
        ingest_candidate=ingest_adapter.IngestCandidate(candidate_store, clock, ids),
        decide_candidate=decide_adapter.DecideCandidate(candidate_store, clock, ids),
        expire_candidates=expire_adapter.ExpireCandidates(candidate_store, clock),
        enqueue_due=enqueue_due,
        expire_overdue=expire_overdue,
        authorize_publish=authorize_publish,
        receive_receipt=receive_receipt,
        apply_receipt=apply_receipt,
        watch_receipt_timeouts=watch_receipt_timeouts,
        receipt_store=receipt_store,
        dispatch_store=dispatch_store,
        dispatch_outbox=dispatch_outbox,
        publishing_policy=publishing_policy,
        publish_lane=publish_lane,
        jobs_lane=jobs_lane,
        collect_metrics=collect_metrics,
        backup_service=backup_adapter.SqliteBackup(),
        restore_service=restore_adapter.RestoreBackup(),
    )


def _is_required(value: str) -> bool:
    return not value.strip() or _REQUIRED in value


def _load_generation_policies(repo_root: Path) -> tuple[Any, Any, dict[str, int]]:
    yaml = import_module("yaml")

    project = repo_root / "config" / "projects" / "venho_hotel"
    cadence = yaml.safe_load((project / "growth" / "cadence_policy.yaml").read_text(encoding="utf-8"))
    budget = yaml.safe_load((project / "growth" / "budget_policy.yaml").read_text(encoding="utf-8"))
    costs = yaml.safe_load((project / "growth" / "paid_call_costs.yaml").read_text(encoding="utf-8"))
    weekday = {name: index for index, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))}
    cadence_domain = import_module("growth_engine.domain.scheduling.cadence")

    rules = tuple(
        cadence_domain.CadenceRule(
            weekday[str(item["day"]).casefold()], str(item["type"]), str(item["lane"])
        )
        for item in cadence["slots"]
    )
    cadence_policy = cadence_domain.CadencePolicy(
        version=int(cadence["version"]),
        project_id="venho_hotel",
        timezone=str(cadence["timezone"]),
        publish_time=str(cadence["publish_time"]),
        rules=rules,
    )
    budget_policy = type("GrowthBudgetPolicy", (), {
        "monthly_cap_minor": int(budget["monthly_cap_minor"]),
        "currency": str(budget["currency"]),
    })()
    cost_estimates = {
        key: int(costs[key])
        for key in ("text_generation_minor", "image_generation_minor", "vision_qc_minor")
    }
    return cadence_policy, budget_policy, cost_estimates


def _generation_spec_hash(repo_root: Path) -> str:
    import hashlib

    paths = (
        "config/projects/venho_hotel/content/content_pillars.yaml",
        "config/projects/venho_hotel/growth/cadence_policy.yaml",
        "config/projects/venho_hotel/growth/model_policy.yaml",
        "config/projects/venho_hotel/growth/paid_call_costs.yaml",
        "config/projects/venho_hotel/growth_engine/channels.yaml",
    )
    digest = hashlib.sha256()
    for relative in paths:
        path = repo_root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
