from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable

from growth_engine.application.errors import Conflict
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.kernel.time import BusinessCalendar
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls


@dataclass(frozen=True)
class ControlsResult:
    controls: RuntimeControls
    channel_id: str | None = None
    channel_paused: bool | None = None


class ControlsUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        clock: Clock,
        ids: IdGenerator,
        *,
        environment: str,
    ) -> None:
        if not environment.strip():
            raise ValueError("environment is required")
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._environment = environment

    def set_mode(
        self,
        mode: PublishMode,
        *,
        actor: str,
        correlation_id: str,
    ) -> ControlsResult:
        self._validate_audit(actor, correlation_id)
        if not isinstance(mode, PublishMode):
            raise ValueError("mode must be a PublishMode")
        with self._uow_factory().begin_immediate() as tx:
            before, row_version = self._read_controls(tx)
            after = RuntimeControls(mode, before.dispatch_epoch, before.global_pause)
            if after == before:
                return ControlsResult(before)
            self._compare_and_set(
                tx,
                row_version,
                {"publish_mode": mode},
            )
            append_audit(
                tx,
                ids=self._ids,
                clock=self._clock,
                aggregate_type="runtime_controls",
                aggregate_id=self._environment,
                actor=actor,
                action="set_mode",
                before=_controls_snapshot(before),
                after=_controls_snapshot(after),
                details={"environment": self._environment},
                correlation_id=correlation_id,
            )
            return ControlsResult(after)

    def pause(
        self,
        *,
        actor: str,
        correlation_id: str,
        channel_id: str | None = None,
    ) -> ControlsResult:
        return self._set_paused(
            True,
            actor=actor,
            correlation_id=correlation_id,
            channel_id=channel_id,
        )

    def resume(
        self,
        *,
        actor: str,
        correlation_id: str,
        channel_id: str | None = None,
    ) -> ControlsResult:
        return self._set_paused(
            False,
            actor=actor,
            correlation_id=correlation_id,
            channel_id=channel_id,
        )

    def bump_epoch(self, *, actor: str, correlation_id: str) -> ControlsResult:
        self._validate_audit(actor, correlation_id)
        with self._uow_factory().begin_immediate() as tx:
            before, row_version = self._read_controls(tx)
            now_ms = self._clock.now_ms()
            utc_minute = BusinessCalendar("UTC").epoch_ms_to_local(now_ms).strftime("%Y%m%d%H%M")
            suffix = sha256_hex(self._ids.new_id().encode("utf-8"))[:4]
            after = RuntimeControls(
                before.mode,
                f"ep-{utc_minute}-{suffix}",
                before.global_pause,
            )
            self._compare_and_set(tx, row_version, {"dispatch_epoch": after.dispatch_epoch})
            append_audit(
                tx,
                ids=self._ids,
                clock=self._clock,
                aggregate_type="runtime_controls",
                aggregate_id=self._environment,
                actor=actor,
                action="bump_epoch",
                before=_controls_snapshot(before),
                after=_controls_snapshot(after),
                details={"environment": self._environment},
                correlation_id=correlation_id,
            )
            return ControlsResult(after)

    def _set_paused(
        self,
        paused: bool,
        *,
        actor: str,
        correlation_id: str,
        channel_id: str | None,
    ) -> ControlsResult:
        self._validate_audit(actor, correlation_id)
        with self._uow_factory().begin_immediate() as tx:
            before, row_version = self._read_controls(tx)
            if channel_id is None:
                after = RuntimeControls(before.mode, before.dispatch_epoch, paused)
                if after == before:
                    return ControlsResult(before)
                self._compare_and_set(tx, row_version, {"global_pause": paused})
                aggregate_type = "runtime_controls"
                aggregate_id = self._environment
                before_snapshot = _controls_snapshot(before)
                after_snapshot = _controls_snapshot(after)
                result = ControlsResult(after)
            else:
                channel = tx.channels.get_channel(channel_id)
                if channel is None:
                    raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy kênh đăng.")
                if channel.paused == paused:
                    return ControlsResult(before, channel_id, paused)
                if not tx.controls.set_channel_paused(channel_id, paused):
                    raise Conflict("Trạng thái kênh đã thay đổi; hãy tải lại.")
                aggregate_type = "channel"
                aggregate_id = channel_id
                before_snapshot = {"channel_id": channel_id, "paused": channel.paused}
                after_snapshot = {"channel_id": channel_id, "paused": paused}
                result = ControlsResult(before, channel_id, paused)
            append_audit(
                tx,
                ids=self._ids,
                clock=self._clock,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                actor=actor,
                action="pause" if paused else "resume",
                before=before_snapshot,
                after=after_snapshot,
                details={"environment": self._environment, "channel_id": channel_id},
                correlation_id=correlation_id,
            )
            return result

    def _read_controls(self, tx: UnitOfWork) -> tuple[RuntimeControls, int]:
        snapshot = tx.controls.get_with_version(self._environment)
        if snapshot is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy cấu hình điều khiển.")
        return snapshot

    def _compare_and_set(
        self,
        tx: UnitOfWork,
        row_version: int,
        fields: Mapping[str, object],
    ) -> None:
        if not tx.controls.compare_and_set(
            self._environment,
            row_version,
            fields=fields,
            updated_at_ms=self._clock.now_ms(),
        ):
            raise Conflict("Cấu hình đã thay đổi; hãy tải lại.")

    @staticmethod
    def _validate_audit(actor: str, correlation_id: str) -> None:
        if not actor.strip() or not correlation_id.strip():
            raise ValueError("actor and correlation_id are required")


def append_audit(
    tx: UnitOfWork,
    *,
    ids: IdGenerator,
    clock: Clock,
    aggregate_type: str,
    aggregate_id: str,
    actor: str,
    action: str,
    before: Mapping[str, object] | None,
    after: Mapping[str, object],
    details: Mapping[str, object],
    correlation_id: str,
) -> None:
    before_hash = None if before is None else sha256_hex(canonical_json_bytes(before))
    after_hash = sha256_hex(canonical_json_bytes(after))
    tx.audit.append(
        event_id=ids.new_id(),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor=actor,
        action=action,
        before_hash=before_hash,
        after_hash=after_hash,
        details_json=canonical_json_bytes(details).decode("utf-8"),
        correlation_id=correlation_id,
        created_at_ms=clock.now_ms(),
    )


def _controls_snapshot(controls: RuntimeControls) -> dict[str, object]:
    return {
        "mode": controls.mode.value,
        "dispatch_epoch": controls.dispatch_epoch,
        "global_pause": controls.global_pause,
    }
