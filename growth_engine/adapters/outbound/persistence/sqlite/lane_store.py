from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

from growth_engine.application.content.run_lanes import LaneTarget
from growth_engine.application.scheduling.ensure_slots import EnsureSlots
from growth_engine.application.dto import DraftRequest
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.scheduling.cadence import CadencePolicy


class SqliteRunLanesStore:
    """Read lane-eligible targets from the same migrated SQLite database."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        ensure_slots: EnsureSlots,
        cadence_policy: CadencePolicy,
        *,
        environment: str,
        timezone_name: str = "Asia/Ho_Chi_Minh",
    ) -> None:
        self._uow_factory = uow_factory
        self._ensure_slots = ensure_slots
        self._cadence_policy = cadence_policy
        self._environment = environment
        self._timezone_name = timezone_name

    def ensure_slots(self, now_ms: int, *, horizon_days: int) -> object:
        local_date = datetime.fromtimestamp(now_ms / 1000, timezone.utc).astimezone(
            ZoneInfo(self._timezone_name)
        ).date()
        return self._ensure_slots.execute(
            self._cadence_policy,
            start_date=local_date,
            horizon_days=horizon_days,
            environment=self._environment,
            correlation_id=f"jobs:ensure-slots:{now_ms}",
        )

    def select_targets(self, lane: str, *, now_ms: int, horizon_days: int) -> Sequence[LaneTarget]:
        if lane not in {"weekly", "fast", "replacement"}:
            raise ValueError("jobs lane must be weekly, fast, or replacement")
        until_ms = now_ms + horizon_days * 24 * 60 * 60 * 1000
        delivery_filter = "d.id IS NULL" if lane in {"weekly", "fast"} else "d.state='SUPERSEDED'"
        delivery_state_filter = "d2.active=1" if lane in {"weekly", "fast"} else "d2.state='SUPERSEDED'"
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                f"""SELECT st.id AS target_id, st.slot_id, st.channel_id, s.lane,
                           d.id AS delivery_id, d.state AS delivery_state,
                           d.row_version AS delivery_row_version, d.permalink,
                           EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                             AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution
                    FROM slot_targets st JOIN slots s ON s.id=st.slot_id
                    LEFT JOIN deliveries d ON d.id=(SELECT d2.id FROM deliveries d2
                      WHERE d2.target_id=st.id AND {delivery_state_filter}
                      ORDER BY d2.created_at DESC LIMIT 1)
                    WHERE s.scheduled_at>=? AND s.scheduled_at<=?
                      AND EXISTS(SELECT 1 FROM channels c0 WHERE c0.id=st.channel_id
                        AND c0.enabled=1 AND c0.environment=?)
                      AND ({delivery_filter})
                    ORDER BY s.scheduled_at, st.slot_id, st.channel_id""",
                (now_ms, until_ms, self._environment),
            ).fetchall()
        return tuple(self._lane_target(row) for row in rows)

    def list_recent_topic_keys(self, since_ms: int) -> Sequence[str]:
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                "SELECT DISTINCT topic_key FROM content_packages WHERE created_at>=? ORDER BY topic_key",
                (since_ms,),
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def refresh_target(self, target_id: str) -> LaneTarget | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
            """SELECT st.id AS target_id, st.slot_id, st.channel_id, s.lane,
                           d.id AS delivery_id, d.state AS delivery_state,
                           d.row_version AS delivery_row_version, d.permalink,
                           EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                             AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution
                    FROM slot_targets st JOIN slots s ON s.id=st.slot_id
                    LEFT JOIN deliveries d ON d.target_id=st.id AND d.active=1
                    WHERE st.id=?""",
                (target_id,),
            ).fetchone()
        return None if row is None else self._lane_target(row)

    def draft_request(self, slot_id: str, lane: str, *, now_ms: int, recent_topics: tuple[str, ...]) -> DraftRequest:
        with self._uow_factory().read_only() as tx:
            slot = tx.connection.execute(
                "SELECT scheduled_at FROM slots WHERE id=?", (slot_id,)
            ).fetchone()
            profiles = tx.connection.execute(
                """SELECT DISTINCT cc.caption_profile FROM slot_targets st
                   JOIN channels c ON c.id=st.channel_id
                   JOIN channel_configs cc ON cc.channel_id=c.id
                   WHERE st.slot_id=? AND c.enabled=1 ORDER BY cc.caption_profile""",
                (slot_id,),
            ).fetchall()
        if slot is None:
            raise KeyError(f"slot not found: {slot_id}")
        profile_names = tuple(str(row[0]) for row in profiles) or ("default",)
        return DraftRequest(
            project_id="venho_hotel",
            slot_id=slot_id,
            lane=lane,
            at_ms=int(slot["scheduled_at"]),
            facts={"recent_topics": list(recent_topics), "caption_profiles": list(profile_names)},
        )

    @staticmethod
    def _lane_target(row: Any) -> LaneTarget:
        delivery = None
        if row["delivery_id"] is not None:
            delivery = Delivery(
                str(row["delivery_id"]),
                DeliveryState(row["delivery_state"]),
                int(row["delivery_row_version"]),
                row["permalink"],
            )
        return LaneTarget(
            target_id=str(row["target_id"]),
            slot_id=str(row["slot_id"]),
            channel_id=str(row["channel_id"]),
            lane=str(row["lane"]),
            delivery=delivery,
            live_execution=bool(row["live_execution"]),
        )

