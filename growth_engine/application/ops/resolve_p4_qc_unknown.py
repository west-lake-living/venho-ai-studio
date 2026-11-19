from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


QC_UNKNOWN_ERROR = "ERR_GC2_JOB_QC_PAID_CALL_UNKNOWN"
P4_SLOT_DATE = "2026-11-21"
P4_SLOT_TIME = "09:00"
P4_PAGE_ID = "1124616474074140"
MAX_P4_QC_MINOR = 400
_RESOLUTION_ACTION = "p4.qc_unknown_resolved_and_requeued"


class P4QcResolutionError(ValueError):
    pass


@dataclass(frozen=True)
class P4QcResolutionPreview:
    job_id: str
    delivery_id: str
    slot_date: str
    slot_time: str
    paid_call_id: str
    paid_call_state: str
    reserved_minor: int
    actual_minor: int
    already_resolved: bool = False


@dataclass(frozen=True)
class P4QcResolutionResult:
    job_id: str
    delivery_id: str
    paid_call_id: str
    actual_minor: int
    qc_retry_key: str
    already_resolved: bool


class ResolveP4QcUnknown:
    """Audited, idempotent settlement and one controlled QC retry for the P4 job."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        *,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def preview(self, job_id: str, *, actual_minor: int | None = None) -> P4QcResolutionPreview:
        with self._uow_factory().read_only() as tx:
            audit = tx.connection.execute(
                "SELECT details_json FROM audit_events WHERE aggregate_type='job' AND aggregate_id=? AND action=?",
                (job_id, _RESOLUTION_ACTION),
            ).fetchone()
            if audit is not None:
                details = json.loads(str(audit["details_json"]))
                return P4QcResolutionPreview(
                    job_id=job_id,
                    delivery_id=str(details["delivery_id"]),
                    slot_date=P4_SLOT_DATE,
                    slot_time=P4_SLOT_TIME,
                    paid_call_id=str(details["paid_call_id"]),
                    paid_call_state="SETTLED",
                    reserved_minor=int(details["reserved_minor"]),
                    actual_minor=int(details["actual_minor"]),
                    already_resolved=True,
                )
            candidate = self._find_candidate(tx.connection, job_id)
        planned = candidate["reserved_minor"] if actual_minor is None else actual_minor
        self._validate_amount(planned, candidate["reserved_minor"])
        return P4QcResolutionPreview(
            job_id=job_id,
            delivery_id=candidate["delivery_id"],
            slot_date=candidate["slot_date"],
            slot_time=candidate["slot_time"],
            paid_call_id=candidate["paid_call_id"],
            paid_call_state=candidate["paid_call_state"],
            reserved_minor=candidate["reserved_minor"],
            actual_minor=planned,
        )

    def execute(
        self,
        job_id: str,
        *,
        actual_minor: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        actor: str = "growth-engine-operator",
    ) -> P4QcResolutionResult:
        if (input_tokens is None) != (output_tokens is None):
            raise P4QcResolutionError("input and output token evidence must be supplied together")
        if input_tokens is not None and (
            type(input_tokens) is not int or input_tokens < 0 or type(output_tokens) is not int or output_tokens < 0
        ):
            raise P4QcResolutionError("token evidence must be non-negative integers")
        now_ms = self._now_ms()
        with self._uow_factory().begin_immediate() as tx:
            audit = tx.connection.execute(
                "SELECT details_json FROM audit_events WHERE aggregate_type='job' AND aggregate_id=? AND action=?",
                (job_id, _RESOLUTION_ACTION),
            ).fetchone()
            if audit is not None:
                details = json.loads(str(audit["details_json"]))
                return P4QcResolutionResult(
                    job_id=job_id,
                    delivery_id=str(details["delivery_id"]),
                    paid_call_id=str(details["paid_call_id"]),
                    actual_minor=int(details["actual_minor"]),
                    qc_retry_key=str(details["qc_retry_key"]),
                    already_resolved=True,
                )

            candidate = self._find_candidate(tx.connection, job_id)
            amount = candidate["reserved_minor"] if actual_minor is None else actual_minor
            self._validate_amount(amount, candidate["reserved_minor"])
            evidence = {
                "kind": "operator_confirmed_provider_usage",
                "http_status": 200,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "accounting_basis": "legacy fixed per-image-QC cost table",
                "raw_response_available": False,
            }
            evidence_json = json.dumps({"operator_recovery": evidence}, sort_keys=True, separators=(",", ":"))
            if not tx.budget.record_provider_response(candidate["business_key"], response_json=evidence_json):
                raise P4QcResolutionError("paid-call recovery evidence could not be recorded")
            if not tx.budget.resolve_unknown(
                candidate["business_key"], actual_minor=amount, settled_at_ms=now_ms
            ):
                raise P4QcResolutionError("paid call is no longer UNKNOWN")

            job = tx.connection.execute("SELECT payload_json FROM jobs WHERE id=?", (job_id,)).fetchone()
            payload = json.loads(str(job["payload_json"]))
            retry_key = self._id_factory()
            payload["qc_retry_key"] = retry_key
            before_hash = _sha256_json({"job_state": "UNKNOWN", "paid_call_state": "UNKNOWN"})
            after_hash = _sha256_json({
                "job_state": "PENDING",
                "paid_call_state": "SETTLED",
                "qc_retry_key": retry_key,
            })
            cursor = tx.connection.execute(
                """UPDATE jobs SET payload_json=?,state='PENDING',run_at=?,last_error=NULL,
                          lease_owner=NULL,lease_token=NULL,lease_until=NULL,updated_at=?
                   WHERE id=? AND state='UNKNOWN'""",
                (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), now_ms, now_ms, job_id),
            )
            if cursor.rowcount != 1:
                raise P4QcResolutionError("assemble job changed before it could be requeued")
            details = {
                "delivery_id": candidate["delivery_id"],
                "paid_call_id": candidate["paid_call_id"],
                "business_key_sha256": hashlib.sha256(candidate["business_key"].encode()).hexdigest(),
                "reserved_minor": candidate["reserved_minor"],
                "actual_minor": amount,
                "slot_date": candidate["slot_date"],
                "slot_time": candidate["slot_time"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "qc_retry_key": retry_key,
                "raw_response_available": False,
            }
            tx.audit.append(
                event_id=self._id_factory(),
                aggregate_type="job",
                aggregate_id=job_id,
                actor=actor,
                action=_RESOLUTION_ACTION,
                before_hash=before_hash,
                after_hash=after_hash,
                details_json=json.dumps(details, sort_keys=True, separators=(",", ":")),
                correlation_id=f"resolve-p4-qc-unknown:{job_id}",
                created_at_ms=now_ms,
            )
        return P4QcResolutionResult(
            job_id=job_id,
            delivery_id=candidate["delivery_id"],
            paid_call_id=candidate["paid_call_id"],
            actual_minor=amount,
            qc_retry_key=retry_key,
            already_resolved=False,
        )

    @staticmethod
    def _find_candidate(connection: Any, job_id: str) -> dict[str, Any]:
        job = connection.execute(
            "SELECT id,kind,state,last_error,payload_json,updated_at FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if job is None or job["kind"] != "assemble_revision" or job["state"] != "UNKNOWN":
            raise P4QcResolutionError("target must be an UNKNOWN assemble_revision job")
        if not str(job["last_error"] or "").startswith(QC_UNKNOWN_ERROR + ":"):
            raise P4QcResolutionError("job is not the expected paid QC UNKNOWN")
        payload = json.loads(str(job["payload_json"]))
        delivery_id = payload.get("delivery_id")
        if not isinstance(delivery_id, str) or not delivery_id:
            raise P4QcResolutionError("assemble job has no delivery identity")
        target = connection.execute(
            """SELECT d.state AS delivery_state,c.environment,c.channel_key,c.remote_account_id,
                      s.local_date,s.local_time
               FROM deliveries d JOIN channels c ON c.id=d.channel_id
               JOIN slot_targets st ON st.id=d.target_id JOIN slots s ON s.id=st.slot_id
               WHERE d.id=? AND d.active=1""",
            (delivery_id,),
        ).fetchone()
        if (
            target is None
            or target["environment"] != "production"
            or target["channel_key"] != "fb_hanoi"
            or str(target["remote_account_id"]) != P4_PAGE_ID
            or target["local_date"] != P4_SLOT_DATE
            or target["local_time"] != P4_SLOT_TIME
            or target["delivery_state"] != "DRAFT"
        ):
            raise P4QcResolutionError("job is not the expected 2026-11-21 fb_hanoi P4 DRAFT")
        dispatch_artifacts = connection.execute(
            """SELECT
                 (SELECT count(*) FROM outbox_commands WHERE delivery_id=?) AS outbox_count,
                 (SELECT count(*) FROM executions WHERE delivery_id=?) AS execution_count""",
            (delivery_id, delivery_id),
        ).fetchone()
        if dispatch_artifacts is None or int(dispatch_artifacts["outbox_count"]) or int(dispatch_artifacts["execution_count"]):
            raise P4QcResolutionError("P4 DRAFT already has an outbox command or execution")
        controls = connection.execute(
            "SELECT publish_mode,global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        if controls is None or controls["publish_mode"] != "DISABLED" or not bool(controls["global_pause"]):
            raise P4QcResolutionError("production must remain DISABLED with global_pause=1")

        asset_ids = sorted({
            str(option["asset_id"])
            for option in payload.get("asset_options", [])
            if isinstance(option, dict) and isinstance(option.get("asset_id"), str)
        })
        if len(asset_ids) != 1:
            raise P4QcResolutionError("one controlled QC retry requires exactly one image asset on the assemble job")
        placeholders = ",".join("?" for _ in asset_ids)
        variants = connection.execute(
            f"SELECT DISTINCT sha256 FROM media_variants WHERE asset_id IN ({placeholders}) AND mime='image/jpeg'",
            tuple(asset_ids),
        ).fetchall()
        prefixes = tuple(f"qc:{row['sha256']}:" for row in variants)
        if not prefixes:
            raise P4QcResolutionError("no prepared JPEG variant matches the P4 media asset")
        calls = connection.execute(
            """SELECT id,business_key,state,reserved_minor,created_at FROM paid_calls
               WHERE provider='legacy_openai_vision' AND operation='image_qc' AND state='UNKNOWN'"""
        ).fetchall()
        matches = [
            row for row in calls
            if str(row["business_key"]).startswith(prefixes)
            and abs(int(row["created_at"]) - int(job["updated_at"])) <= 15 * 60_000
        ]
        if len(matches) != 1:
            raise P4QcResolutionError("could not identify exactly one UNKNOWN QC paid call for this P4 job")
        paid_call = matches[0]
        return {
            "job_id": job_id,
            "delivery_id": delivery_id,
            "slot_date": str(target["local_date"]),
            "slot_time": str(target["local_time"]),
            "paid_call_id": str(paid_call["id"]),
            "paid_call_state": str(paid_call["state"]),
            "business_key": str(paid_call["business_key"]),
            "reserved_minor": int(paid_call["reserved_minor"]),
        }

    @staticmethod
    def _validate_amount(actual_minor: int, reserved_minor: int) -> None:
        if type(actual_minor) is not int or not 0 <= actual_minor <= min(reserved_minor, MAX_P4_QC_MINOR):
            raise P4QcResolutionError("actual QC cost must be within the reserved legacy per-call amount")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
