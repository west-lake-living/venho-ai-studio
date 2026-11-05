from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Any, Callable, Iterator, Mapping
from uuid import uuid4

from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord
from growth_engine.application.content.generate_package import (
    GenerationClaim,
    PackageFact,
)
from growth_engine.application.scheduling.ensure_slots import ChannelAvailability
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    incident_fingerprint,
)
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


class SqliteGenerationStore:
    """SQLite transaction adapter for slot preparation and package generation."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        ids: Any,
        *,
        reserve_drafts: bool = True,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._reserve_drafts = reserve_drafts

    @contextmanager
    def begin_immediate(self) -> Iterator[_GenerationTransaction]:
        with self._uow_factory().begin_immediate() as tx:
            yield _GenerationTransaction(tx, self._ids)

    def claim_generation(self, business_key: str, **claims: object) -> GenerationClaim:
        with self._uow_factory().begin_immediate() as tx:
            row = tx.connection.execute(
                "SELECT id, state, payload_json, last_error FROM jobs "
                "WHERE kind='generate_package' AND business_key=?",
                (business_key,),
            ).fetchone()
            if row is not None:
                state = str(row["state"])
                if state == "SUCCEEDED":
                    package_id = json.loads(row["payload_json"]).get("package_id")
                    package_id = package_id if isinstance(package_id, str) else None
                    package = None if package_id is None else tx.packages.get(package_id)
                    delivery_ids = () if package_id is None else tuple(
                        str(item[0]) for item in tx.connection.execute(
                            "SELECT d.id FROM deliveries d JOIN channels c ON c.id=d.channel_id "
                            "WHERE d.package_id=? ORDER BY c.channel_key", (package_id,)
                        ).fetchall()
                    )
                    return GenerationClaim("SUCCEEDED", package, delivery_ids)
                if state == "UNKNOWN":
                    return GenerationClaim("UNKNOWN")
                if state == "FAILED" and row["last_error"] == "ERR_GC2_BUDGET_EXCEEDED":
                    return GenerationClaim("BUDGET_EXCEEDED")
                return GenerationClaim("IN_PROGRESS")

            paid_call_id = str(claims["paid_call_id"])
            estimate = int(claims["estimated_cost_minor"])
            accepted = tx.budget.reserve(
                call_id=paid_call_id,
                business_key=business_key,
                period_key=str(claims["period_key"]),
                currency=str(claims["currency"]),
                provider=str(claims["provider"]),
                operation=str(claims["operation"]),
                amount_minor=estimate,
                cap_minor=int(claims["monthly_cap_minor"]),
                created_at_ms=int(claims["now_ms"]),
            )
            if not accepted:
                now_ms = int(claims["now_ms"])
                job_id = str(claims["job_id"])
                tx.jobs.save(JobRecord(
                    id=job_id,
                    kind="generate_package",
                    lane="jobs",
                    business_key=business_key,
                    payload_json=_json({"slot_id": claims["slot_id"], "package_id": None}),
                    state="FAILED",
                    run_at_ms=now_ms,
                    max_attempts=1,
                    last_error="ERR_GC2_BUDGET_EXCEEDED",
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                ))
                incident_type = "GENERATION_BUDGET_EXCEEDED"
                incident = Incident(
                    id=self._ids.new_id(), type=incident_type,
                    fingerprint=incident_fingerprint(incident_type, None, business_key),
                    channel_id=None, ref=business_key, severity=IncidentSeverity.WARNING,
                    state=IncidentState.OPEN, first_seen_at_ms=now_ms, last_seen_at_ms=now_ms,
                )
                tx.incidents.open_or_touch(
                    incident, details_json=_json({"estimated_cost_minor": estimate})
                )
                return GenerationClaim("BUDGET_EXCEEDED")
            now_ms = int(claims["now_ms"])
            payload = {
                "slot_id": claims["slot_id"],
                "lane": claims["lane"],
                "package_spec_hash": claims["package_spec_hash"],
                "generator_version": claims["generator_version"],
                "package_id": None,
            }
            tx.jobs.save(JobRecord(
                id=str(claims["job_id"]),
                kind="generate_package",
                lane="jobs",
                business_key=business_key,
                payload_json=_json(payload),
                state="RUNNING",
                run_at_ms=now_ms,
                max_attempts=1,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            ))
            return GenerationClaim("CLAIMED")

    def mark_generation_unknown(self, business_key: str, **fields: object) -> None:
        now_ms = int(fields["now_ms"])
        with self._uow_factory().begin_immediate() as tx:
            tx.budget.mark_unknown(business_key)
            cursor = tx.connection.execute(
                "UPDATE jobs SET state='UNKNOWN', last_error=?, updated_at=? "
                "WHERE kind='generate_package' AND business_key=? AND state IN ('RUNNING','FAILED')",
                (str(fields["error_class"]), now_ms, business_key),
            )
            if cursor.rowcount != 1:
                row = tx.connection.execute(
                    "SELECT state FROM jobs WHERE kind='generate_package' AND business_key=?",
                    (business_key,),
                ).fetchone()
                if row is None or row["state"] != "UNKNOWN":
                    raise RuntimeError("generation job was not in a claimable state")
            incident_type = "GENERATION_UNKNOWN"
            incident = Incident(
                id=self._ids.new_id(),
                type=incident_type,
                fingerprint=incident_fingerprint(incident_type, None, business_key),
                channel_id=None,
                ref=business_key,
                severity=IncidentSeverity.WARNING,
                state=IncidentState.OPEN,
                first_seen_at_ms=now_ms,
                last_seen_at_ms=now_ms,
            )
            tx.incidents.open_or_touch(incident, details_json=_json({"error_class": fields["error_class"]}))

    def complete_generation(
        self,
        business_key: str,
        package: ContentPackage,
        asset_options: tuple[Mapping[str, object], ...],
        package_facts: tuple[PackageFact, ...],
        captions_by_profile: Mapping[str, str],
        **fields: object,
    ) -> tuple[str, ...]:
        settled_at = int(fields["settled_at_ms"])
        correlation_id = str(fields["correlation_id"])
        with self._uow_factory().begin_immediate() as tx:
            job = tx.connection.execute(
                "SELECT id, state, payload_json FROM jobs WHERE kind='generate_package' AND business_key=?",
                (business_key,),
            ).fetchone()
            if job is None:
                raise RuntimeError("generation completion has no durable claim")
            if job["state"] == "SUCCEEDED":
                payload = json.loads(job["payload_json"])
                package_id = str(payload["package_id"])
                return tuple(str(row[0]) for row in tx.connection.execute(
                    "SELECT d.id FROM deliveries d JOIN channels c ON c.id=d.channel_id "
                    "WHERE d.package_id=? ORDER BY c.channel_key", (package_id,)
                ).fetchall())
            if job["state"] != "RUNNING":
                raise RuntimeError("generation claim is no longer active")

            snapshot = json.loads(package.source_snapshot_json)
            snapshot["captions_by_profile"] = dict(captions_by_profile)
            persisted_package = ContentPackage(
                id=package.id,
                slot_id=package.slot_id,
                topic_key=package.topic_key,
                pillar=package.pillar,
                lane=package.lane,
                source_snapshot_json=_json(snapshot),
                fact_snapshot_json=package.fact_snapshot_json,
                fact_snapshot_hash=package.fact_snapshot_hash,
                generation_version=package.generation_version,
                created_at_ms=package.created_at_ms,
                candidate_id=package.candidate_id,
            )
            tx.packages.save(persisted_package)
            for fact in package_facts:
                tx.connection.execute(
                    """INSERT INTO package_facts
                       (package_id, fact_key, fact_revision, text_hash, valid_until, source_ref)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (package.id, fact.fact_key, fact.fact_revision, fact.text_hash,
                     fact.valid_until_ms, fact.source_ref),
                )
            for option in asset_options:
                asset_id = str(option["asset_id"])
                asset = tx.media.get_asset(asset_id)
                if asset is None:
                    raise RuntimeError("generated asset was not persisted before package completion")
                job_id = self._ids.new_id()
                self._save_job(
                    tx,
                    job_id=job_id,
                    kind="prepare_variant",
                    business_key=f"prepare-variant:{asset_id}",
                    payload={"asset_id": asset_id, "option_id": option["option_id"]},
                    now_ms=settled_at,
                )

            targets = tx.connection.execute(
                """SELECT st.id, st.channel_id, c.channel_key, c.platform, cc.id AS config_id,
                          s.scheduled_at, s.deadline_at
                   FROM slot_targets st
                   JOIN channels c ON c.id=st.channel_id
                   JOIN slots s ON s.id=st.slot_id
                   LEFT JOIN channel_configs cc ON cc.channel_id=c.id
                   WHERE st.slot_id=? AND c.enabled=1
                   ORDER BY c.channel_key""",
                (package.slot_id,),
            ).fetchall()
            if not targets:
                raise RuntimeError("generation package has no enabled slot target")
            delivery_ids: list[str] = []
            for target in (targets if self._reserve_drafts else ()):
                delivery_id = str(uuid4())
                tx.deliveries.save(
                    Delivery(delivery_id, DeliveryState.DRAFT),
                    target_id=str(target["id"]),
                    channel_id=str(target["channel_id"]),
                    package_id=package.id,
                    created_at_ms=settled_at,
                    updated_at_ms=settled_at,
                )
                delivery_ids.append(delivery_id)
                tx.audit.append(
                    event_id=self._ids.new_id(),
                    aggregate_type="delivery",
                    aggregate_id=delivery_id,
                    actor="growth-engine",
                    action="delivery.reserved",
                    before_hash=None,
                    after_hash=sha256_hex(canonical_json_bytes({
                        "delivery_id": delivery_id,
                        "target_id": target["id"],
                        "channel_key": target["channel_key"],
                        "package_id": package.id,
                        "state": "DRAFT",
                    })),
                    details_json=_json({
                        "target_id": target["id"],
                        "package_id": package.id,
                        "channel_key": target["channel_key"],
                    }),
                    correlation_id=correlation_id,
                    created_at_ms=settled_at,
                )
                self._save_job(
                    tx,
                    job_id=self._ids.new_id(),
                    kind="assemble_revision",
                    business_key=f"assemble-revision:{delivery_id}:1",
                    payload={
                        "delivery_id": delivery_id,
                        "channel_config_id": target["config_id"],
                        "channel_key": target["channel_key"],
                        "platform": target["platform"],
                        "media_profile": (
                            "instagram_photo_v1"
                            if target["platform"] == "instagram"
                            else "facebook_photo_v1"
                        ),
                        "captions_by_profile": dict(captions_by_profile),
                        "asset_option_ids": [item["option_id"] for item in asset_options],
                    },
                    now_ms=settled_at,
                )
            settled = tx.budget.settle(
                business_key,
                actual_minor=int(fields["estimated_cost_minor"]),
                settled_at_ms=settled_at,
            )
            if not settled:
                raise RuntimeError("generation budget reservation could not be settled")
            payload = json.loads(job["payload_json"])
            payload["package_id"] = package.id
            tx.connection.execute(
                "UPDATE jobs SET state='SUCCEEDED', payload_json=?, updated_at=? WHERE id=? AND state='RUNNING'",
                (_json(payload), settled_at, job["id"]),
            )
            tx.audit.append(
                event_id=self._ids.new_id(), aggregate_type="content_package", aggregate_id=package.id,
                actor="growth-engine", action="generation.completed", before_hash=None,
                after_hash=sha256_hex(canonical_json_bytes({"package_id": package.id, "delivery_ids": delivery_ids})),
                details_json=_json({"slot_id": package.slot_id, "delivery_ids": delivery_ids}),
                correlation_id=correlation_id, created_at_ms=settled_at,
            )
            return tuple(delivery_ids)

    def _save_job(
        self, tx: Any, *, job_id: str, kind: str, business_key: str,
        payload: Mapping[str, object], now_ms: int,
    ) -> None:
        tx.jobs.save(JobRecord(
            id=job_id, kind=kind, lane="jobs", business_key=business_key,
            payload_json=_json(payload), state="PENDING", run_at_ms=now_ms,
            created_at_ms=now_ms, updated_at_ms=now_ms,
        ))


class _GenerationTransaction:
    def __init__(self, tx: Any, ids: Any) -> None:
        self._tx = tx
        self._ids = ids
        self.connection = tx.connection

    def list_channels(self, project_id: str, environment: str):
        rows = self.connection.execute(
            """SELECT c.id, c.project_id, c.environment, c.enabled,
                      EXISTS(SELECT 1 FROM channel_configs cc WHERE cc.channel_id=c.id) AS configured
               FROM channels c WHERE c.project_id=? AND c.environment=? ORDER BY c.channel_key""",
            (project_id, environment),
        ).fetchall()
        return tuple(ChannelAvailability(
            channel_id=str(row["id"]), project_id=str(row["project_id"]),
            environment=str(row["environment"]), enabled=bool(row["enabled"]),
            configured=bool(row["configured"]),
        ) for row in rows)

    def find_slot(self, project_id: str, local_date: date, local_time: str, lane: str):
        row = self.connection.execute(
            """SELECT id, project_id, local_date, local_time, timezone, lane,
                      cadence_version, scheduled_at, deadline_at, cancelled_at
               FROM slots WHERE project_id=? AND local_date=? AND local_time=? AND lane=?""",
            (project_id, local_date.isoformat(), local_time, lane),
        ).fetchone()
        return None if row is None else _slot(row)

    def insert_slot_if_absent(self, slot: Slot, *, created_at_ms: int) -> bool:
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, cancelled_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (slot.id, slot.project_id, slot.local_date.isoformat(), slot.local_time, slot.timezone,
             slot.lane, slot.cadence_version, slot.scheduled_at_ms, slot.deadline_at_ms,
             slot.cancelled_at_ms, created_at_ms),
        )
        return cursor.rowcount == 1

    def find_target(self, slot_id: str, channel_id: str):
        row = self.connection.execute(
            "SELECT id, slot_id, channel_id, required FROM slot_targets WHERE slot_id=? AND channel_id=?",
            (slot_id, channel_id),
        ).fetchone()
        return None if row is None else SlotTarget(
            str(row["id"]), str(row["slot_id"]), str(row["channel_id"]), bool(row["required"])
        )

    def insert_target_if_absent(self, target: SlotTarget) -> bool:
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO slot_targets(id, slot_id, channel_id, required) VALUES (?, ?, ?, ?)",
            (target.id, target.slot_id, target.channel_id, int(target.required)),
        )
        return cursor.rowcount == 1

    def open_channel_config_incident(self, channel_id: str, *, now_ms: int, correlation_id: str) -> None:
        incident_type = "CHANNEL_CONFIG_MISSING"
        incident = Incident(
            id=self._ids.new_id(), type=incident_type,
            fingerprint=incident_fingerprint(incident_type, channel_id, "channel-config"),
            channel_id=channel_id, ref="channel-config", severity=IncidentSeverity.HIGH,
            state=IncidentState.OPEN, first_seen_at_ms=now_ms, last_seen_at_ms=now_ms,
        )
        self._tx.incidents.open_or_touch(incident, details_json=_json({"correlation_id": correlation_id}))

    def append_audit(self, **entry: object) -> None:
        details = entry.get("details", {})
        self._tx.audit.append(
            event_id=self._ids.new_id(),
            aggregate_type=str(entry["aggregate_type"]), aggregate_id=str(entry["aggregate_id"]),
            actor=str(entry["actor"]), action=str(entry["action"]),
            before_hash=entry.get("before_hash") if isinstance(entry.get("before_hash"), str) else None,
            after_hash=entry.get("after_hash") if isinstance(entry.get("after_hash"), str) else None,
            details_json=_json(details if isinstance(details, Mapping) else {}),
            correlation_id=str(entry["correlation_id"]), created_at_ms=int(entry["created_at_ms"]),
        )

    def load_target_context(self, target_id: str) -> dict[str, object] | None:
        row = self.connection.execute(
            """SELECT st.id AS target_id, st.slot_id, st.channel_id, st.required,
                      s.project_id, s.local_date, s.local_time, s.timezone, s.lane,
                      s.cadence_version, s.scheduled_at, s.deadline_at, s.cancelled_at,
                      d.id AS delivery_id, d.state AS delivery_state,
                      d.row_version AS delivery_row_version, d.permalink
               FROM slot_targets st JOIN slots s ON s.id=st.slot_id
               LEFT JOIN deliveries d ON d.target_id=st.id AND d.active=1
               WHERE st.id=? ORDER BY d.created_at DESC LIMIT 1""",
            (target_id,),
        ).fetchone()
        if row is None:
            return None
        delivery = None if row["delivery_id"] is None else Delivery(
            str(row["delivery_id"]), DeliveryState(row["delivery_state"]),
            int(row["delivery_row_version"]), row["permalink"],
        )
        return {
            "target": SlotTarget(str(row["target_id"]), str(row["slot_id"]), str(row["channel_id"]), bool(row["required"])),
            "slot": Slot(str(row["slot_id"]), str(row["project_id"]), date.fromisoformat(row["local_date"]),
                         str(row["local_time"]), str(row["timezone"]), str(row["lane"]),
                         str(row["cadence_version"]), int(row["scheduled_at"]), int(row["deadline_at"]),
                         row["cancelled_at"]),
            "active_delivery": delivery,
        }

    def insert_draft_delivery(self, delivery: Delivery, *, target: SlotTarget, package_id: str, created_at_ms: int) -> bool:
        try:
            self._tx.deliveries.save(
                delivery, target_id=target.id, channel_id=target.channel_id,
                package_id=package_id, created_at_ms=created_at_ms, updated_at_ms=created_at_ms,
            )
        except sqlite3.IntegrityError as error:
            existing = self.connection.execute(
                "SELECT id FROM deliveries WHERE target_id=? AND active=1", (target.id,)
            ).fetchone()
            if existing is not None:
                return False
            raise error
        package = self.connection.execute(
            "SELECT source_snapshot_json FROM content_packages WHERE id=?", (package_id,)
        ).fetchone()
        route = self.connection.execute(
            """SELECT c.channel_key, c.platform, cc.id AS channel_config_id
               FROM channels c LEFT JOIN channel_configs cc ON cc.channel_id=c.id
               WHERE c.id=? ORDER BY cc.version DESC LIMIT 1""",
            (target.channel_id,),
        ).fetchone()
        if package is None or route is None:
            raise RuntimeError("package or channel route is missing for delivery assembly")
        snapshot = json.loads(package["source_snapshot_json"])
        image_options = snapshot.get("images", [])
        self._tx.jobs.save(JobRecord(
            id=self._ids.new_id(),
            kind="assemble_revision",
            lane="jobs",
            business_key=f"assemble-revision:{delivery.id}:1",
            payload_json=_json({
                "delivery_id": delivery.id,
                "channel_config_id": route["channel_config_id"],
                "channel_key": route["channel_key"],
                "platform": route["platform"],
                "media_profile": (
                    "instagram_photo_v1"
                    if route["platform"] == "instagram"
                    else "facebook_photo_v1"
                ),
                "captions_by_profile": snapshot.get("captions_by_profile", {}),
                "asset_options": image_options,
            }),
            state="PENDING",
            run_at_ms=created_at_ms,
            created_at_ms=created_at_ms,
            updated_at_ms=created_at_ms,
        ))
        return True


def _slot(row: Any) -> Slot:
    return Slot(
        id=str(row["id"]), project_id=str(row["project_id"]),
        local_date=date.fromisoformat(row["local_date"]), local_time=str(row["local_time"]),
        timezone=str(row["timezone"]), lane=str(row["lane"]),
        cadence_version=str(row["cadence_version"]), scheduled_at_ms=int(row["scheduled_at"]),
        deadline_at_ms=int(row["deadline_at"]), cancelled_at_ms=row["cancelled_at"],
    )


def _json(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8")
