from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from growth_engine.application.dto import EffectiveQcPolicy, FactSnapshot, QcResult, VariantView
from growth_engine.application.ports.content import QcEvaluator
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.application.review.create_revision import CreateRevision, RevisionDraft
from growth_engine.domain.media.asset import VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.delivery.revision import normalize_caption


P4_JOB_ID = "e0d00517-3661-4390-a532-6f516e0ef176"
P4_DELIVERY_ID = "2509f430-4a4a-47dd-97a9-4b99e8d4ba88"
P4_RETRY_KEY = "ea0bb3d3-1a5c-49ef-b60f-840cfca4e319"
P4_SLOT_DATE = "2026-11-21"
P4_PAGE_ID = "1124616474074140"
_REPROCESS_ACTION = "p4.qc_evidence_reprocessed"


class P4QcEvidenceError(ValueError):
    code = "ERR_GC2_P4_QC_REPROCESS_FAILED"

    def __init__(self, message: str) -> None:
        self.public_message = message
        super().__init__(message)


class P4QcEvidenceInsufficient(P4QcEvidenceError):
    code = "ERR_GC2_P4_QC_EVIDENCE_INSUFFICIENT"

    def __init__(self, missing: str) -> None:
        self.missing = missing
        self.public_message = (
            f"Stored QC evidence is insufficient: {missing}. Option B would require one new QC call "
            "(maximum 400 VND) and separate operator approval; it was not started."
        )
        ValueError.__init__(self, self.public_message)


class P4QcEvidenceNonFiniteNumber(P4QcEvidenceError):
    code = "ERR_GC2_QC_NONFINITE_NUMBER"


@dataclass(frozen=True)
class P4QcEvidencePreview:
    job_id: str
    delivery_id: str
    evidence_length: int
    readable_keys: tuple[str, ...]
    already_processed: bool = False


@dataclass(frozen=True)
class P4QcEvidenceResult:
    job_id: str
    delivery_id: str
    qc_report_id: str | None
    revision_id: str | None
    already_processed: bool


@dataclass(frozen=True)
class _Plan:
    job_id: str
    delivery_id: str
    row_version: int
    caption: str
    variant: VariantView
    fact_snapshot: FactSnapshot
    policy: EffectiveQcPolicy
    result: QcResult
    decision: QcDecision
    evidence_length: int
    readable_keys: tuple[str, ...]


class ReprocessP4QcEvidence:
    """Rebuild the one failed P4 QC and review revision from stored response evidence only."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        qc_evaluator: QcEvaluator,
        create_revision: CreateRevision,
        *,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._qc_evaluator = qc_evaluator
        self._create_revision = create_revision
        self._now_ms = now_ms or (lambda: __import__("time").time_ns() // 1_000_000)
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def preview(self, job_id: str) -> P4QcEvidencePreview:
        completed = self._completed_result(job_id)
        if completed is not None:
            return P4QcEvidencePreview(job_id, completed.delivery_id, 0, (), already_processed=True)
        plan = self._prepare(job_id)
        return P4QcEvidencePreview(
            plan.job_id,
            plan.delivery_id,
            plan.evidence_length,
            plan.readable_keys,
        )

    def execute(self, job_id: str, *, actor: str = "growth-engine-operator") -> P4QcEvidenceResult:
        completed = self._completed_result(job_id)
        if completed is not None:
            return completed
        plan = self._prepare(job_id)
        with self._uow_factory().begin_immediate() as tx:
            report = self._persist_qc_report(tx, plan)
            revision = self._create_revision.execute(
                plan.delivery_id,
                expected_row_version=plan.row_version,
                draft=RevisionDraft(caption=plan.caption, variant_id=plan.variant.variant_id),
                actor=actor,
                transaction=tx,
                qc_report_override=report,
            )
            self._record_completion(
                tx, plan, report.id, str(revision.revision.payload["revision_id"]), actor
            )
        return P4QcEvidenceResult(
            plan.job_id,
            plan.delivery_id,
            report.id,
            str(revision.revision.payload["revision_id"]),
            already_processed=False,
        )

    def _prepare(self, job_id: str) -> _Plan:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT j.id AS job_id,j.kind AS job_kind,j.state AS job_state,j.last_error,
                          j.payload_json,d.id AS delivery_id,d.state AS delivery_state,d.row_version,
                          d.current_revision_id,d.package_id,c.environment,c.channel_key,c.platform,
                          c.remote_account_id,c.project_id,cc.id AS channel_config_id,
                          cc.caption_profile,p.source_snapshot_json,p.fact_snapshot_json,p.fact_snapshot_hash,
                          s.local_date,s.local_time
                   FROM jobs j JOIN deliveries d ON d.id=json_extract(j.payload_json,'$.delivery_id')
                   JOIN channels c ON c.id=d.channel_id
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id
                   JOIN content_packages p ON p.id=d.package_id
                   JOIN channel_configs cc ON cc.channel_id=c.id
                   WHERE j.id=? ORDER BY cc.version DESC LIMIT 1""",
                (job_id,),
            ).fetchone()
            if row is None:
                raise P4QcEvidenceError("target job or delivery was not found")
            self._validate_target(tx.connection, row)
            job_payload = _json_object(row["payload_json"], "assemble job payload")
            retry_key = job_payload.get("qc_retry_key")
            if retry_key != P4_RETRY_KEY:
                raise P4QcEvidenceError("job retry key does not match the confirmed production retry")
            options = job_payload.get("asset_options")
            asset_ids = sorted({
                str(item["asset_id"])
                for item in options if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
            }) if isinstance(options, list) else []
            if len(asset_ids) != 1:
                raise P4QcEvidenceInsufficient("exactly one image asset in the assemble job")
            variants = tx.connection.execute(
                """SELECT id,asset_id,sha256,width,height,mime,object_key,qc_status
                   FROM media_variants WHERE asset_id=? AND mime='image/jpeg'""",
                (asset_ids[0],),
            ).fetchall()
            calls = tx.connection.execute(
                """SELECT id,business_key,state,actual_minor,provider_response_json
                   FROM paid_calls WHERE provider='legacy_openai_vision' AND operation='image_qc'
                     AND state='SETTLED'"""
            ).fetchall()
            matching = []
            for variant_row in variants:
                prefix = f"qc:{variant_row['sha256']}:"
                suffix = f":retry:{P4_RETRY_KEY}"
                matching.extend(
                    (variant_row, call)
                    for call in calls
                    if str(call["business_key"]).startswith(prefix)
                    and str(call["business_key"]).endswith(suffix)
                )
            if len(matching) != 1:
                raise P4QcEvidenceInsufficient("exactly one SETTLED image_qc paid call for the retry key")
            variant_row, call = matching[0]
            if type(call["actual_minor"]) is not int or not 0 <= int(call["actual_minor"]) <= 400:
                raise P4QcEvidenceInsufficient("settled QC cost evidence within the 400 VND cap")
            evidence_text = call["provider_response_json"]
            if not isinstance(evidence_text, str) or not evidence_text:
                raise P4QcEvidenceInsufficient("stored filtered provider response")
            evidence = _json_array(evidence_text, "stored provider evidence")
            response = _response_from_evidence(evidence)
            if response is None:
                raise P4QcEvidenceInsufficient("image observation rawResponse or parsedEvidence")
            keys = _readable_keys(response)
            if not _has_http_200(evidence):
                raise P4QcEvidenceInsufficient("provider response_received evidence with HTTP 200")

            source_snapshot = _json_object(row["source_snapshot_json"], "content source snapshot")
            captions = source_snapshot.get("captions_by_profile")
            if not isinstance(captions, dict):
                raise P4QcEvidenceInsufficient("content package caption profile map")
            caption = captions.get(str(row["caption_profile"] or "default")) or captions.get("default")
            if not isinstance(caption, str) or not caption.strip():
                raise P4QcEvidenceInsufficient("caption for the channel profile")
            facts_value = _json_object(row["fact_snapshot_json"], "fact snapshot")
            facts = FactSnapshot(facts_value, str(row["fact_snapshot_hash"]))
            option = next(
                item for item in options
                if isinstance(item, dict) and item.get("asset_id") == asset_ids[0]
            )
            provenance = option.get("provenance") if isinstance(option, dict) else None
            subject = (
                str(provenance.get("dna_subject"))
                if isinstance(provenance, dict) and isinstance(provenance.get("dna_subject"), str)
                else "outside"
            )
            policy = self._qc_evaluator.compile_policy(str(row["project_id"]), subject, None)
            variant = VariantView(
                variant_id=str(variant_row["id"]),
                sha256=str(variant_row["sha256"]),
                width=int(variant_row["width"]),
                height=int(variant_row["height"]),
                mime=str(variant_row["mime"]),
                object_key=str(variant_row["object_key"]),
                qc_status=str(variant_row["qc_status"]),
            )
            try:
                result = self._qc_evaluator.reprocess_response(variant, caption, facts, policy, response)
            except ValueError as error:
                if getattr(error, "code", None) == P4QcEvidenceNonFiniteNumber.code:
                    raise P4QcEvidenceNonFiniteNumber(_safe_error(error)) from None
                raise P4QcEvidenceInsufficient(_safe_error(error)) from None
            if (
                result.ruleset_hash != policy.ruleset_hash
                or result.caption_hash != hashlib.sha256(normalize_caption(caption).encode()).hexdigest()
                or result.fact_snapshot_hash != facts.snapshot_hash
            ):
                raise P4QcEvidenceInsufficient("response does not yield QC for this caption, facts and active ruleset")
            try:
                decision = _effective_decision(result, policy.forbidden)
            except ValueError as error:
                raise P4QcEvidenceInsufficient(_safe_error(error)) from None
            if decision is QcDecision.FAIL:
                raise P4QcEvidenceError(
                    "stored QC evidence evaluates to FAIL; no QC report or revision was written"
                )
            return _Plan(
                job_id=str(row["job_id"]),
                delivery_id=str(row["delivery_id"]),
                row_version=int(row["row_version"]),
                caption=normalize_caption(caption),
                variant=variant,
                fact_snapshot=facts,
                policy=policy,
                result=result,
                decision=decision,
                evidence_length=len(evidence_text),
                readable_keys=tuple(keys),
            )

    def _validate_target(self, connection: Any, row: Any) -> None:
        if (
            row["job_id"] != P4_JOB_ID
            or row["job_kind"] != "assemble_revision"
            or row["job_state"] != "FAILED"
            or not str(row["last_error"] or "").startswith("ERR_GC2_QC_POST_RESPONSE_FAILED:")
            or row["delivery_id"] != P4_DELIVERY_ID
            or row["delivery_state"] != "DRAFT"
            or row["environment"] != "production"
            or row["channel_key"] != "fb_hanoi"
            or row["platform"] != "facebook"
            or str(row["remote_account_id"]) != P4_PAGE_ID
            or row["local_date"] != P4_SLOT_DATE
            or row["current_revision_id"] is not None
        ):
            raise P4QcEvidenceError("target is not the expected failed P4 production draft")
        if row["local_time"] != "09:00":
            raise P4QcEvidenceError("target slot is not 09:00 ICT")
        controls = connection.execute(
            "SELECT publish_mode,global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        if controls is None or controls["publish_mode"] != "DISABLED" or not bool(controls["global_pause"]):
            raise P4QcEvidenceError("production must remain DISABLED with global_pause=1")
        artifacts = connection.execute(
            """SELECT (SELECT count(*) FROM outbox_commands WHERE delivery_id=?) AS outbox_count,
                      (SELECT count(*) FROM executions WHERE delivery_id=?) AS execution_count""",
            (row["delivery_id"], row["delivery_id"]),
        ).fetchone()
        if artifacts is None or int(artifacts["outbox_count"]) or int(artifacts["execution_count"]):
            raise P4QcEvidenceError("delivery already has dispatch artifacts")

    def _persist_qc_report(self, tx: UnitOfWork, plan: _Plan) -> QcReport:
        caption_hash = hashlib.sha256(plan.caption.encode()).hexdigest()
        report = QcReport(
            id=self._id_factory(),
            variant_id=plan.variant.variant_id,
            caption_hash=caption_hash,
            ruleset_hash=plan.policy.ruleset_hash,
            fact_snapshot_hash=plan.fact_snapshot.snapshot_hash,
            decision=plan.decision,
            coverage_gaps=tuple(dict.fromkeys(plan.result.coverage_gaps)),
            result_json=plan.result.result_json,
            created_at_ms=self._now_ms(),
        )
        existing = tx.qc.find_matching(
            report.variant_id, report.caption_hash, report.fact_snapshot_hash, report.ruleset_hash
        )
        if existing is not None:
            report = existing
        current = tx.media.get_variant(report.variant_id)
        if current is None or current.sha256 != plan.variant.sha256:
            raise P4QcEvidenceError("JPEG variant changed during reprocessing")
        tx.media.update_qc_status(report.variant_id, _variant_status(report.decision))
        if existing is None:
            tx.qc.save(report)
        return report

    def _record_completion(
        self,
        tx: UnitOfWork,
        plan: _Plan,
        report_id: str,
        revision_id: str,
        actor: str,
    ) -> None:
        now_ms = self._now_ms()
        if self._has_audit(tx.connection, plan.job_id):
            return
        delivery = tx.connection.execute(
            "SELECT state,current_revision_id,row_version FROM deliveries WHERE id=?",
            (plan.delivery_id,),
        ).fetchone()
        revision = tx.connection.execute(
            "SELECT payload_json FROM delivery_revisions WHERE id=? AND delivery_id=?",
            (revision_id, plan.delivery_id),
        ).fetchone()
        if (
            delivery is None
            or delivery["state"] != "IN_REVIEW"
            or delivery["current_revision_id"] != revision_id
            or revision is None
            or json.loads(str(revision["payload_json"])).get("qc_report_id") != report_id
        ):
            raise P4QcEvidenceError("revision is not linked to the reprocessed QC report")
        tx.audit.append(
            event_id=self._id_factory(),
            aggregate_type="job",
            aggregate_id=plan.job_id,
            actor=actor,
            action=_REPROCESS_ACTION,
            before_hash=_sha256_json({"job": "FAILED", "delivery": "DRAFT"}),
            after_hash=_sha256_json({
                "job": "FAILED",
                "delivery": "IN_REVIEW",
                "qc_report_id": report_id,
                "revision_id": revision_id,
            }),
            details_json=json.dumps({
                "delivery_id": plan.delivery_id,
                "qc_report_id": report_id,
                "revision_id": revision_id,
                "evidence_length": plan.evidence_length,
                "readable_keys": list(plan.readable_keys),
                "provider_called": False,
                "paid_call_created": False,
            }, sort_keys=True, separators=(",", ":")),
            correlation_id=f"reprocess-p4-qc-evidence:{plan.job_id}",
            created_at_ms=now_ms,
        )

    def _completed_result(self, job_id: str) -> P4QcEvidenceResult | None:
        with self._uow_factory().read_only() as tx:
            audit = tx.connection.execute(
                "SELECT details_json FROM audit_events WHERE aggregate_type='job' AND aggregate_id=? AND action=?",
                (job_id, _REPROCESS_ACTION),
            ).fetchone()
            if audit is not None:
                details = json.loads(str(audit["details_json"]))
                return P4QcEvidenceResult(
                    job_id,
                    str(details["delivery_id"]),
                    str(details["qc_report_id"]),
                    str(details["revision_id"]),
                    True,
                )
            row = tx.connection.execute(
                """SELECT d.id,d.state,d.current_revision_id,r.payload_json
                   FROM jobs j JOIN deliveries d ON d.id=json_extract(j.payload_json,'$.delivery_id')
                   JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   WHERE j.id=?""",
                (job_id,),
            ).fetchone()
            if row is None or row["state"] != "IN_REVIEW":
                return None
            payload = _json_object(row["payload_json"], "current revision")
            report_id = payload.get("qc_report_id")
            if not isinstance(report_id, str):
                return None
            report = tx.qc.get(report_id)
            if report is None:
                return None
            return P4QcEvidenceResult(job_id, str(row["id"]), report_id, str(row["current_revision_id"]), True)

    @staticmethod
    def _has_audit(connection: Any, job_id: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM audit_events WHERE aggregate_type='job' AND aggregate_id=? AND action=? LIMIT 1",
            (job_id, _REPROCESS_ACTION),
        ).fetchone() is not None


def _response_from_evidence(events: list[Any]) -> object | None:
    parsed: list[object] = []
    raw: list[object] = []
    for item in events:
        if not isinstance(item, dict) or item.get("source") != "validator":
            continue
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        parsed_evidence = event.get("parsedEvidence")
        if isinstance(parsed_evidence, dict):
            parsed.append(parsed_evidence)
        response = event.get("rawResponse")
        if isinstance(response, (dict, str)):
            raw.append(response)
    return parsed[-1] if parsed else (raw[0] if raw else None)


def _has_http_200(events: list[Any]) -> bool:
    return any(
        isinstance(item, dict)
        and item.get("source") == "provider"
        and isinstance(item.get("event"), dict)
        and item["event"].get("event") == "response_received"
        and item["event"].get("http_status") == 200
        for item in events
    )


def _readable_keys(response: object) -> list[str]:
    value = response
    if isinstance(value, str):
        value = _extract_json_object(value)
    if not isinstance(value, dict):
        raise P4QcEvidenceInsufficient("stored image observation is not a JSON object")
    return sorted(str(key) for key in value)


def _extract_json_object(text: str) -> object | None:
    """Extract one JSON value for the non-sensitive preflight key listing."""
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text, re.IGNORECASE)
    candidate = match.group(1).strip() if match else text.strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(candidate):
        if char not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(candidate[index:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def _json_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise P4QcEvidenceError(f"{label} is missing")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        raise P4QcEvidenceError(f"{label} is invalid JSON") from None
    if not isinstance(parsed, dict):
        raise P4QcEvidenceError(f"{label} must be a JSON object")
    return parsed


def _json_array(value: str, label: str) -> list[Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        raise P4QcEvidenceInsufficient(f"{label} is invalid JSON") from None
    if not isinstance(parsed, list):
        raise P4QcEvidenceInsufficient(f"{label} must be an event array")
    return parsed


def _safe_error(error: Exception) -> str:
    message = str(error) or type(error).__name__
    # These are the parser's field-level diagnostics. Other validator messages
    # are intentionally reduced to their type: evidence may contain provider
    # text and this command must never echo it to the operator log.
    if not message.startswith(("field ", "image observation schema invalid")):
        message = type(error).__name__
    message = re.sub(r"https?://\S+", "[URL REDACTED]", message, flags=re.IGNORECASE)
    message = re.sub(
        r"(?i)(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password|token)"
        r"(\s*[:=]\s*|\s+)[^\s,;]+",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(r"\b[A-Za-z0-9_-]{48,}\b", "[SECRET REDACTED]", message)
    return " ".join(message.split())[:240] or type(error).__name__


def _effective_decision(result: QcResult, forbidden: tuple[str, ...]) -> QcDecision:
    from growth_engine.application.media.evaluate_qc import _effective_decision as resolve_decision

    return resolve_decision(result.decision, result.result_json, forbidden, result.coverage_gaps)


def _variant_status(decision: QcDecision) -> VariantQcStatus:
    return {
        QcDecision.PASS: VariantQcStatus.PASS,
        QcDecision.FAIL: VariantQcStatus.FAIL,
        QcDecision.REVIEW: VariantQcStatus.REVIEW,
    }[decision]


def _sha256_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
