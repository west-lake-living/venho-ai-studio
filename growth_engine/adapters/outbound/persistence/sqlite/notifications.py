from __future__ import annotations

import json
import secrets
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from growth_engine.adapters.outbound.persistence.sqlite.cas import complete_with_lease
from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord
from growth_engine.application.ops.notifications import NotificationJob
from growth_engine.application.ops.reminders import DailyDigest, ReminderCandidate
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import canonical_json_bytes


class SqliteNotificationQueue:
    """Durable, deduplicated notification queue backed by the existing jobs table."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        ids: Any,
        *,
        dashboard_base_url: str = "",
        templates: Mapping[str, str] | None = None,
        timezone_name: str = "Asia/Ho_Chi_Minh",
        lease_ms: int = 30_000,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._dashboard_base_url = dashboard_base_url.rstrip("/")
        self._templates = dict(templates or {})
        self._zone = ZoneInfo(timezone_name)
        self._lease_ms = lease_ms
        self._owner = f"notify-{secrets.token_urlsafe(12)}"
        self._lease_tokens: dict[str, str] = {}

    def enqueue_unique(self, dedupe_key: str, message: str, *, created_at_ms: int) -> str | None:
        if not dedupe_key.strip() or not message.strip() or type(created_at_ms) is not int:
            raise ValueError("notification dedupe key, message and timestamp are required")
        with self._uow_factory().begin_immediate() as tx:
            existing = tx.connection.execute(
                "SELECT id FROM jobs WHERE kind='notify' AND business_key=?", (dedupe_key,)
            ).fetchone()
            if existing is not None:
                return None
            job_id = self._ids.new_id()
            tx.jobs.save(JobRecord(
                id=job_id,
                kind="notify",
                lane="publish",
                business_key=dedupe_key,
                payload_json=canonical_json_bytes({"dedupe_key": dedupe_key, "message": message}).decode("utf-8"),
                state="PENDING",
                run_at_ms=created_at_ms,
                created_at_ms=created_at_ms,
                updated_at_ms=created_at_ms,
            ))
            return job_id

    def claim_pending(self, *, limit: int, now_ms: int) -> Sequence[NotificationJob]:
        if type(limit) is not int or limit < 1 or type(now_ms) is not int:
            raise ValueError("notification claim limit and timestamp are invalid")
        claimed: list[NotificationJob] = []
        with self._uow_factory().begin_immediate() as tx:
            rows = tx.connection.execute(
                """SELECT id, business_key, payload_json, attempts, state, lease_until
                   FROM jobs WHERE kind='notify' AND lane='publish' AND run_at<=?
                     AND (state='PENDING' OR (state='RUNNING' AND lease_until<=?))
                   ORDER BY run_at, created_at, id LIMIT ?""",
                (now_ms, now_ms, limit),
            ).fetchall()
            for row in rows:
                payload = json.loads(row["payload_json"])
                message, stale = self._message_for(tx.connection, payload)
                if stale:
                    tx.connection.execute(
                        "UPDATE jobs SET state='CANCELLED', lease_owner=NULL, lease_token=NULL, lease_until=NULL, updated_at=?, last_error='stale_notification' WHERE id=? AND state IN ('PENDING','RUNNING')",
                        (now_ms, row["id"]),
                    )
                    continue
                if not message:
                    continue
                claim = tx.jobs.claim_with_lease(
                    {"id": row["id"], "state": row["state"], "run_at": ("<=", now_ms),
                     **({"lease_until": ("<=", now_ms)} if row["state"] == "RUNNING" else {})},
                    owner=self._owner,
                    lease_ms=self._lease_ms,
                    now_ms=now_ms,
                )
                if claim is None:
                    continue
                claimed_row, token = claim
                job_id = str(claimed_row["id"])
                self._lease_tokens[job_id] = token
                claimed.append(NotificationJob(
                    id=job_id,
                    dedupe_key=str(claimed_row["business_key"]),
                    message=message,
                    attempts=int(claimed_row["attempts"]),
                ))
        return tuple(claimed)

    def mark_sent(self, job_id: str, *, sent_at_ms: int) -> None:
        token = self._lease_tokens.pop(job_id, None)
        if token is None:
            raise RuntimeError("notification lease is missing or expired")
        with self._uow_factory().begin_immediate() as tx:
            if not tx.jobs.complete(job_id, token, updated_at_ms=sent_at_ms, state="SUCCEEDED"):
                raise RuntimeError("notification lease was lost before completion")

    def schedule_retry(self, job_id: str, *, retry_at_ms: int, error_type: str) -> None:
        token = self._lease_tokens.pop(job_id, None)
        if token is None:
            raise RuntimeError("notification lease is missing or expired")
        with self._uow_factory().begin_immediate() as tx:
            row = tx.jobs.get(job_id)
            if row is None:
                raise RuntimeError("notification job disappeared")
            attempts = row.attempts + 1
            state = "PENDING" if attempts < row.max_attempts else "DEAD"
            completed = complete_with_lease(
                tx.connection,
                "jobs",
                job_id,
                token,
                fields={
                    "state": state,
                    "attempts": attempts,
                    "run_at": retry_at_ms,
                    "last_error": f"notify:{error_type[:64]}",
                    "updated_at": retry_at_ms,
                },
            )
            if not completed:
                raise RuntimeError("notification lease was lost before retry scheduling")

    def _message_for(self, connection: Any, payload: Mapping[str, object]) -> tuple[str | None, bool]:
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message, False
        if payload.get("type") != "REVIEW_NEEDED":
            return None, False
        delivery_id = payload.get("delivery_id")
        revision_id = payload.get("revision_id")
        if not isinstance(delivery_id, str) or not isinstance(revision_id, str):
            return None, False
        row = connection.execute(
            """SELECT d.state, d.current_revision_id, c.name AS page_name,
                      s.local_date, s.local_time, p.topic_key
               FROM deliveries d JOIN channels c ON c.id=d.channel_id
               JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
               JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
               WHERE d.id=?""",
            (delivery_id,),
        ).fetchone()
        if row is None or row["state"] != DeliveryState.IN_REVIEW.value or row["current_revision_id"] != revision_id:
            return None, True
        if not self._dashboard_base_url.startswith("https://"):
            return None, False
        local_date = datetime.fromisoformat(row["local_date"]).date()
        weekday = _weekday_vi(local_date.weekday())
        deadline = f"{weekday} {local_date:%d/%m} {row['local_time']}"
        template = self._templates.get(
            "review_needed",
            "🟡 Bài chờ duyệt — {weekday} {date} {time}\nChủ đề: {topic}\nPage: {pages}\nHạn duyệt: {deadline}\n👉 Duyệt: {review_link}",
        )
        review_link = f"{self._dashboard_base_url}/growth/deliveries/{delivery_id}"
        return template.format(
            weekday=weekday,
            date=f"{local_date:%d/%m}",
            time=row["local_time"],
            topic=row["topic_key"],
            pages=row["page_name"],
            deadline=deadline,
            review_link=review_link,
        ), False


class SqliteReminderRepository:
    """Slot-aware reminder and digest readers with dedupe writes in the jobs table."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        ids: Any,
        *,
        environment: str,
        timezone_name: str = "Asia/Ho_Chi_Minh",
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._environment = environment
        self._zone = ZoneInfo(timezone_name)

    def due_reminders(
        self,
        *,
        now_ms: int,
        reminder_offsets_minutes: Sequence[int],
        window_minutes: int,
    ) -> Sequence[ReminderCandidate]:
        if type(now_ms) is not int or type(window_minutes) is not int or window_minutes < 1:
            raise ValueError("reminder times are invalid")
        offsets = tuple(reminder_offsets_minutes)
        if not offsets or any(type(item) is not int or item <= 0 for item in offsets):
            raise ValueError("reminder offsets must be positive minute values")
        minimum = now_ms + (min(offsets) - window_minutes) * 60_000
        maximum = now_ms + (max(offsets) + window_minutes) * 60_000
        with self._uow_factory().read_only() as tx:
            rows = tx.connection.execute(
                """SELECT d.id AS delivery_id, d.current_revision_id AS revision_id,
                          d.state, s.scheduled_at, s.local_date, s.local_time,
                          p.topic_key, c.name AS page_name
                   FROM deliveries d JOIN channels c ON c.id=d.channel_id
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
                   WHERE d.active=1 AND d.state='IN_REVIEW' AND d.current_revision_id IS NOT NULL
                     AND c.enabled=1 AND c.environment=? AND s.scheduled_at BETWEEN ? AND ?
                   ORDER BY s.scheduled_at, d.id""",
                (self._environment, minimum, maximum),
            ).fetchall()
        candidates: list[ReminderCandidate] = []
        for row in rows:
            delta = int(row["scheduled_at"]) - now_ms
            if not any(abs(delta - offset * 60_000) <= window_minutes * 60_000 for offset in offsets):
                continue
            local_date = datetime.fromisoformat(row["local_date"]).date()
            scheduled_label = f"{_weekday_vi(local_date.weekday())} {local_date:%d/%m} {row['local_time']}"
            candidates.append(ReminderCandidate(
                delivery_id=row["delivery_id"],
                revision_id=row["revision_id"],
                state=DeliveryState(row["state"]),
                scheduled_at_ms=int(row["scheduled_at"]),
                topic=row["topic_key"],
                page_names=(row["page_name"],),
                deadline_label=scheduled_label,
            ))
        return tuple(candidates)

    def reserve_if_current(
        self,
        candidate: ReminderCandidate,
        *,
        reminder_kind: str,
        message: str,
        now_ms: int,
    ) -> bool:
        dedupe_key = f"reminder:{candidate.delivery_id}:{candidate.revision_id}:{reminder_kind}"
        with self._uow_factory().begin_immediate() as tx:
            current = tx.connection.execute(
                """SELECT d.state, d.current_revision_id, s.scheduled_at
                   FROM deliveries d JOIN slot_targets st ON st.id=d.target_id
                   JOIN slots s ON s.id=st.slot_id WHERE d.id=?""",
                (candidate.delivery_id,),
            ).fetchone()
            if (
                current is None
                or current["state"] != DeliveryState.IN_REVIEW.value
                or current["current_revision_id"] != candidate.revision_id
                or int(current["scheduled_at"]) != candidate.scheduled_at_ms
            ):
                return False
            existing = tx.connection.execute(
                "SELECT 1 FROM jobs WHERE kind='notify' AND business_key=?", (dedupe_key,)
            ).fetchone()
            if existing is not None:
                return False
            tx.jobs.save(JobRecord(
                id=self._ids.new_id(), kind="notify", lane="publish", business_key=dedupe_key,
                payload_json=canonical_json_bytes({"dedupe_key": dedupe_key, "message": message}).decode("utf-8"),
                state="PENDING", run_at_ms=now_ms, created_at_ms=now_ms, updated_at_ms=now_ms,
            ))
            return True

    def daily_digest(self, now_ms: int) -> DailyDigest:
        local_today = datetime.fromtimestamp(now_ms / 1000, timezone.utc).astimezone(self._zone).date()
        tomorrow = local_today + timedelta(days=1)
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT COUNT(st.id) AS total,
                          SUM(CASE WHEN d.state IN ('APPROVED','QUEUED') THEN 1 ELSE 0 END) AS ready,
                          SUM(CASE WHEN d.state='IN_REVIEW' THEN 1 ELSE 0 END) AS awaiting
                   FROM slot_targets st JOIN slots s ON s.id=st.slot_id
                   JOIN channels c ON c.id=st.channel_id
                   LEFT JOIN deliveries d ON d.target_id=st.id AND d.active=1
                   WHERE s.local_date=? AND c.environment=? AND c.enabled=1""",
                (tomorrow.isoformat(), self._environment),
            ).fetchone()
        total = int(row["total"] or 0)
        ready = int(row["ready"] or 0)
        awaiting = int(row["awaiting"] or 0)
        return DailyDigest(
            ready=ready,
            total=total,
            awaiting=awaiting,
            attention=max(0, total - ready - awaiting),
            tomorrow_label=f"{_weekday_vi(tomorrow.weekday())} {tomorrow:%d/%m}",
        )


def _weekday_vi(index: int) -> str:
    return ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật")[index]
