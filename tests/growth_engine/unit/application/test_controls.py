from __future__ import annotations

import re
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.domain.ops.incident import IncidentSeverity, IncidentState
from growth_engine.domain.publishing.runtime_mode import PublishMode
from tests.growth_engine.support.fakes import FakeClock, SeqIds


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
HASH = "a" * 64


def _dependencies(tmp_path: Path) -> tuple[SqliteUnitOfWork, FakeClock, SeqIds]:
    path = tmp_path / "controls.db"
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
        connection.execute(
            """INSERT INTO runtime_controls
               (environment, publish_mode, dispatch_epoch, global_pause, policy_version, updated_at)
               VALUES ('test', 'LIVE_MANUAL', 'ep-before', 0, 'policy-test', 1)"""
        )
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name, created_at)
               VALUES ('channel-test', 'venho-test', 'test', 'fb_hanoi', 'facebook',
                       'synthetic-page', 'Synthetic Page', 1)"""
        )
        connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, created_at)
               VALUES ('slot-test', 'venho-test', '2026-11-05', '09:00', 'Asia/Ho_Chi_Minh',
                       'weekly', 'v1', 1, 1000, 1)"""
        )
        connection.execute(
            "INSERT INTO slot_targets(id, slot_id, channel_id) VALUES ('target-test', 'slot-test', 'channel-test')"
        )
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
                fact_snapshot_hash, generation_version, created_at)
               VALUES ('package-test', 'slot-test', 'topic', 'local', 'weekly', '{}', '{}', ?, 'v1', 1)""",
            (HASH,),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, created_at, updated_at)
               VALUES ('delivery-test', 'target-test', 'channel-test', 'package-test', 'DRAFT', 1, 1)"""
        )
    finally:
        connection.close()
    uow = SqliteUnitOfWork(lambda: connect(path), sleep=lambda _: None)
    return uow, FakeClock(1_798_790_400_000), SeqIds("synthetic-control")


def _audit_count(uow: SqliteUnitOfWork) -> int:
    with uow.read_only() as tx:
        return int(tx.connection.execute("SELECT count(*) FROM audit_events").fetchone()[0])


def test_pause_resume_and_mode_are_audited_without_changing_delivery_state(tmp_path: Path) -> None:
    uow, clock, ids = _dependencies(tmp_path)
    from growth_engine.application.ops.controls import ControlsUseCase

    controls = ControlsUseCase(lambda: uow, clock, ids, environment="test")
    paused = controls.pause(actor="operator-test", correlation_id="corr-1")
    assert paused.controls is not None and paused.controls.global_pause is True
    channel_paused = controls.pause(
        actor="operator-test", correlation_id="corr-2", channel_id="channel-test"
    )
    assert channel_paused.channel_paused is True
    global_resumed = controls.resume(actor="operator-test", correlation_id="corr-3")
    assert global_resumed.controls is not None and global_resumed.controls.global_pause is False
    channel_resumed = controls.resume(
        actor="operator-test", correlation_id="corr-4", channel_id="channel-test"
    )
    assert channel_resumed.channel_paused is False
    changed_mode = controls.set_mode(
        PublishMode.DRY_RUN, actor="operator-test", correlation_id="corr-5"
    )
    assert changed_mode.controls is not None and changed_mode.controls.mode is PublishMode.DRY_RUN

    with uow.read_only() as tx:
        delivery = tx.deliveries.get("delivery-test")
        channel = tx.channels.get_channel("channel-test")
        assert delivery is not None and delivery.state.value == "DRAFT"
        assert channel is not None and channel.paused is False
        control_row = tx.controls.get("test")
        assert control_row is not None and control_row.mode is PublishMode.DRY_RUN
    assert _audit_count(uow) == 5


def test_bump_epoch_has_utc_minute_and_four_hex_suffix_and_is_audited(tmp_path: Path) -> None:
    uow, clock, ids = _dependencies(tmp_path)
    from growth_engine.application.ops.controls import ControlsUseCase

    controls = ControlsUseCase(lambda: uow, clock, ids, environment="test")
    result = controls.bump_epoch(actor="operator-test", correlation_id="corr-epoch")
    assert result.controls is not None
    assert re.fullmatch(r"ep-\d{12}-[0-9a-f]{4}", result.controls.dispatch_epoch)
    assert result.controls.dispatch_epoch != "ep-before"
    assert _audit_count(uow) == 1


def test_incidents_dedupe_touch_resolve_and_audit(tmp_path: Path) -> None:
    uow, clock, ids = _dependencies(tmp_path)
    from growth_engine.application.ops.incidents import IncidentUseCase

    incidents = IncidentUseCase(lambda: uow, clock, ids)
    first = incidents.open_or_touch_incident(
        incident_type="UNKNOWN",
        channel_id="channel-test",
        ref="delivery-test",
        severity=IncidentSeverity.HIGH,
        details={"synthetic": True},
        actor="operator-test",
        correlation_id="corr-incident-1",
    )
    clock.set(clock.now_ms() + 1)
    touched = incidents.open_or_touch_incident(
        incident_type="UNKNOWN",
        channel_id="channel-test",
        ref="delivery-test",
        severity=IncidentSeverity.WARNING,
        details={"synthetic": True, "attempt": 2},
        actor="operator-test",
        correlation_id="corr-incident-2",
    )
    assert touched.id == first.id
    assert touched.occurrence_count == 2
    assert touched.severity is IncidentSeverity.HIGH
    resolved = incidents.resolve_incident(
        touched.id,
        actor="operator-test",
        reason="synthetic evidence resolved",
        correlation_id="corr-incident-3",
    )
    assert resolved.state is IncidentState.RESOLVED
    with uow.read_only() as tx:
        rows = tx.connection.execute(
            "SELECT state, occurrence_count, resolved_by FROM incidents"
        ).fetchall()
        delivery = tx.deliveries.get("delivery-test")
        assert len(rows) == 1
        assert tuple(rows[0]) == ("RESOLVED", 2, "operator-test")
        assert delivery is not None and delivery.state.value == "DRAFT"
    assert _audit_count(uow) == 3
