from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from growth_engine.application.dto import JobDraft
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.scheduling.ensure_slots import EnsureSlots
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.publishing.runtime_mode import PublishMode


PRODUCTION_TARGETS = {
    "fb_hanoi": ("facebook", "1124616474074140"),
    "fb_venho": ("facebook", "803531149684177"),
    "ig_venho": ("instagram", "17841457936965829"),
}


@dataclass(frozen=True)
class QueueSlotGenerationResult:
    slot_id: str
    job_id: str
    state: str
    replayed: bool


class QueueSlotGeneration:
    """Create one supported production content target and queue its generation job."""

    def __init__(
        self,
        uow_factory: Callable[[], object],
        ensure_slots: EnsureSlots,
        cadence_policy: object,
        clock: Clock,
        ids: IdGenerator,
        *,
        environment: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._ensure_slots = ensure_slots
        self._cadence_policy = cadence_policy
        self._clock = clock
        self._ids = ids
        self._environment = environment

    def execute(self, local_date: date, *, channel_key: str = "fb_hanoi") -> QueueSlotGenerationResult:
        if self._environment != "production":
            raise ValueError("queue-slot is only available in production")
        if channel_key not in {"fb_hanoi", "group"}:
            raise ValueError("preparation currently allows fb_hanoi or the production group")
        expected = PRODUCTION_TARGETS if channel_key == "group" else {"fb_hanoi": PRODUCTION_TARGETS["fb_hanoi"]}
        required_mode = PublishMode.LIVE_MANUAL if channel_key == "group" else PublishMode.DISABLED

        with self._uow_factory().read_only() as tx:
            controls = tx.controls.get("production")
            if controls is None or controls.mode is not required_mode or not controls.global_pause:
                raise ValueError("production preparation requires the expected mode with global_pause=1")
            rows = tx.connection.execute(
                """SELECT channel_key, platform, remote_account_id, paused,
                          EXISTS(SELECT 1 FROM channel_configs cc WHERE cc.channel_id=c.id) AS configured
                   FROM channels c WHERE environment='production' AND enabled=1"""
            ).fetchall()
            mapped = {row["channel_key"]: (row["platform"], row["remote_account_id"]) for row in rows}
            if mapped != expected or any(row["paused"] or not row["configured"] for row in rows):
                raise ValueError("production content targets do not match the verified preparation mapping")

        now_ms = self._clock.now_ms()
        self._ensure_slots.execute(
            self._cadence_policy,
            start_date=local_date,
            horizon_days=1,
            environment="production",
            correlation_id=f"p4-prepare-slot:{channel_key}:{local_date.isoformat()}",
        )

        with self._uow_factory().begin_immediate() as tx:
            slot = tx.connection.execute(
                """SELECT s.id, s.lane, s.scheduled_at FROM slots s
                   JOIN slot_targets st ON st.slot_id=s.id
                   JOIN channels c ON c.id=st.channel_id
                   WHERE s.project_id='venho_hotel' AND s.local_date=? AND s.local_time=?
                     AND c.environment='production' AND c.channel_key=?
                   ORDER BY s.id LIMIT 1""",
                (local_date.isoformat(), str(getattr(self._cadence_policy, "publish_time")), "fb_hanoi"),
            ).fetchone()
            if slot is None:
                raise ValueError("requested date is not a configured production cadence slot")
            if channel_key == "group" and slot["scheduled_at"] <= now_ms:
                raise ValueError("group preparation requires a future slot")
            slot_id = str(slot["id"])
            business_key = f"prepare-slot:{slot_id}:{channel_key}"
            existing = tx.connection.execute(
                "SELECT id, state FROM jobs WHERE kind='generate_slot' AND business_key=?",
                (business_key,),
            ).fetchone()
            if existing is not None:
                return QueueSlotGenerationResult(slot_id, str(existing["id"]), str(existing["state"]), True)

            job_id = self._ids.new_id()
            tx.jobs.save(JobDraft(
                id=job_id,
                kind="generate_slot",
                lane="jobs",
                business_key=business_key,
                payload_json=canonical_json_bytes({
                    "slot_id": slot_id,
                    "lane": str(slot["lane"]),
                    "channel_key": channel_key,
                }).decode("utf-8"),
                state="PENDING",
                run_at_ms=now_ms,
                max_attempts=1,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            ))
            return QueueSlotGenerationResult(slot_id, job_id, "PENDING", False)
