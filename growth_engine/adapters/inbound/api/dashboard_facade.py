from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from growth_engine.application.content.decide_candidate import (
    CandidateDecisionKind,
    DecideCandidateCommand,
)
from growth_engine.application.errors import NotFound, PreconditionFailed
from growth_engine.application.queries.incident_views import IncidentViewsQuery
from growth_engine.application.queries.slot_views import SlotViewsQuery
from growth_engine.application.review.approve_group import ApprovalItem
from growth_engine.application.review.create_revision import RevisionDraft
from growth_engine.application.review.reject_revision import ReplaceMode
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.publishing.runtime_mode import PublishMode
from growth_engine.domain.kernel.time import BusinessCalendar


_ETAG = re.compile(r'^"?(delivery|slot):([^:\"]+):(\d+)"?$')


class DashboardApi:
    """Application-operation facade consumed by the Dashboard HTTP routers."""

    def __init__(
        self,
        *,
        reads: Any,
        slot_views: Any,
        incident_views: Any,
        review_snapshot: Any,
        create_revision: Any,
        reschedule_slot: Any,
        approve_group: Any,
        reject_revision: Any,
        revoke_approval: Any,
        cancel_delivery: Any,
        decide_candidate: Any,
        controls: Any,
        upload_asset: Any,
        clock: Any,
    ) -> None:
        self._reads = reads
        self._slot_views = slot_views
        self._incident_views = incident_views
        self._review_snapshot = review_snapshot
        self._create_revision_uc = create_revision
        self._reschedule_slot = reschedule_slot
        self._approve_group = approve_group
        self._reject_revision = reject_revision
        self._revoke_approval = revoke_approval
        self._cancel_delivery = cancel_delivery
        self._decide_candidate = decide_candidate
        self._controls = controls
        self._upload_asset_uc = upload_asset
        self._clock = clock

    def execute(
        self,
        operation: str,
        *,
        payload: dict[str, object],
        actor: str,
        correlation_id: str,
        if_match: str | None,
        idempotency_key: str | None,
    ) -> object:
        if operation == "channels.list":
            return self._reads.channels()
        if operation == "slots.list":
            start, end = self._slot_range(payload)
            return self._slot_views.execute(SlotViewsQuery(start, end))
        if operation == "deliveries.list":
            return self._reads.deliveries(
                state=_optional_string(payload.get("state")),
                channel_id=_optional_string(payload.get("channel_id")),
                cursor=_optional_string(payload.get("cursor")),
                limit=int(payload.get("limit", 50)),
            )
        if operation == "delivery.review":
            delivery_id = _required_string(payload, "delivery_id")
            snapshot = self._review_snapshot.execute(delivery_id)
            return {
                "delivery_id": snapshot.delivery_id,
                "state": snapshot.state,
                "row_version": snapshot.row_version,
                "etag": snapshot.etag,
                "channel_key": snapshot.channel_key,
                "channel_name": snapshot.channel_name,
                "remote_account_id": snapshot.remote_account_id,
                "revision_id": snapshot.revision_id,
                "payload_hash": snapshot.payload_hash,
                "caption": snapshot.caption,
                "scheduled_at_ms": snapshot.scheduled_at_ms,
                "deadline_at_ms": snapshot.deadline_at_ms,
                "preview_url": snapshot.preview_url,
                "preview_sha256": snapshot.preview_sha256,
                "image_label": snapshot.image_label,
                "allowed_actions": list(snapshot.allowed_actions),
            }
        if operation == "job.get":
            job = self._reads.job(_required_string(payload, "job_id"))
            if job is None:
                raise NotFound("Không tìm thấy job.")
            return job
        if operation == "candidates.list":
            return self._reads.candidates(
                state=str(payload.get("state", "NEW")),
                cursor=_optional_string(payload.get("cursor")),
                limit=int(payload.get("limit", 50)),
            )
        if operation == "incidents.list":
            return self._incident_views.execute(IncidentViewsQuery(
                state=str(payload.get("state", "OPEN")),
                cursor=_optional_string(payload.get("cursor")),
                limit=int(payload.get("limit", 50)),
            ))
        if operation == "controls.get":
            controls = self._reads.controls()
            if controls is None:
                raise NotFound("Chưa có cấu hình điều khiển cho môi trường này.")
            return controls
        if operation == "asset.upload":
            return self._upload_asset(payload, idempotency_key=idempotency_key, actor=actor)
        if operation == "slot.reschedule":
            return self._reschedule(payload, actor, correlation_id, if_match)
        if operation == "delivery.revision.create":
            return self._handle_create_revision(payload, actor, if_match)
        if operation == "approval.batch":
            return self._approve(payload, actor, idempotency_key)
        if operation == "delivery.reject":
            delivery_id = _required_string(payload, "delivery_id")
            revision_id = _required_string(payload, "revision_id")
            self._check_version("delivery", delivery_id, if_match)
            result = self._reject_revision.execute(
                delivery_id,
                revision_id=revision_id,
                reason=_required_string(payload, "reason"),
                replace_mode=ReplaceMode(str(payload.get("replace_mode", "NONE")).upper()),
                actor=actor,
                correlation_id=correlation_id,
            )
            return {
                "delivery_id": result.delivery_id,
                "revision_id": result.revision_id,
                "state": result.delivery_state.value,
                "row_version": result.row_version,
                "replacement_delivery_id": result.replacement_delivery_id,
            }
        if operation == "delivery.revoke":
            delivery_id = _required_string(payload, "delivery_id")
            self._check_version("delivery", delivery_id, if_match)
            result = self._revoke_approval.execute(
                delivery_id,
                actor=actor,
                reason=_required_string(payload, "reason"),
                correlation_id=correlation_id,
            )
            return {
                "delivery_id": result.delivery_id,
                "state": result.delivery_state.value,
                "row_version": result.row_version,
                "revocation_id": result.revocation_id,
            }
        if operation == "delivery.cancel":
            delivery_id = _required_string(payload, "delivery_id")
            self._check_version("delivery", delivery_id, if_match)
            result = self._cancel_delivery.execute(
                delivery_id,
                actor=actor,
                reason=_required_string(payload, "reason"),
                correlation_id=correlation_id,
            )
            return {
                "delivery_id": result.delivery_id,
                "state": result.delivery_state.value,
                "row_version": result.row_version,
            }
        if operation == "candidate.decide":
            result = self._decide_candidate.execute(DecideCandidateCommand(
                candidate_id=_required_string(payload, "candidate_id"),
                source_hash=_required_string(payload, "source_hash"),
                decision=CandidateDecisionKind(_required_string(payload, "decision").upper()),
                actor=actor,
                reason=str(payload.get("reason") or ""),
                correlation_id=correlation_id,
            ))
            return {
                "candidate_id": result.candidate.id,
                "state": result.candidate.state.value,
                "source_hash": result.candidate.source_hash,
                "decision_id": result.decision_id,
            }
        if operation in {"controls.pause", "controls.resume", "controls.mode"}:
            return self._set_controls(operation, payload, actor, correlation_id)
        if operation in {"delivery.reconcile", "delivery.retry"}:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                "Thao tác đối soát hoặc safe retry chưa có adapter SQLite/Meta khả dụng.",
            )
        raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy thao tác Dashboard.")

    def preview_image(self, sha256: str) -> tuple[bytes, str] | None:
        return self._reads.preview(sha256)

    def _slot_range(self, payload: dict[str, object]) -> tuple[str, str]:
        start = _optional_string(payload.get("from"))
        end = _optional_string(payload.get("to"))
        today = BusinessCalendar("Asia/Ho_Chi_Minh").epoch_ms_to_local(
            self._clock.now_ms()
        ).date()
        start = start or today.isoformat()
        end = end or today.isoformat()
        # Query use case performs ordering validation; date parsing rejects malformed ranges here.
        date.fromisoformat(start)
        date.fromisoformat(end)
        return start, end

    def _check_version(self, resource: str, resource_id: str, if_match: str | None) -> int:
        kind, identifier, expected = _parse_etag(if_match)
        if kind != resource or identifier != resource_id:
            raise PreconditionFailed("If-Match không khớp dữ liệu đang thao tác.")
        current = (
            self._reads.delivery_version(resource_id)
            if resource == "delivery"
            else None
        )
        if current is None or current != expected:
            raise PreconditionFailed("Dữ liệu đã thay đổi; hãy tải lại.")
        return expected

    def _reschedule(
        self,
        payload: dict[str, object],
        actor: str,
        correlation_id: str,
        if_match: str | None,
    ) -> dict[str, object]:
        slot_id = _required_string(payload, "slot_id")
        kind, identifier, expected = _parse_etag(if_match)
        if kind != "slot" or identifier != slot_id:
            raise PreconditionFailed("If-Match không khớp lịch cần đổi.")
        context = self._reads.slot_context(slot_id)
        if context is None:
            raise NotFound("Không tìm thấy lịch cần đổi.")
        if context["row_version"] != expected:
            raise PreconditionFailed("Lịch đã thay đổi; hãy tải lại.")
        scheduled = _required_string(payload, "scheduled_at")
        parsed = datetime.fromisoformat(scheduled)
        if parsed.tzinfo is not None:
            raise ValueError("scheduled_at must be local time without a UTC offset")
        result = self._reschedule_slot.execute(
            slot_id,
            expected_row_version=expected,
            local_date=parsed.date(),
            local_time=parsed.time().replace(tzinfo=None).isoformat(timespec="minutes"),
            actor=actor,
            correlation_id=correlation_id,
        )
        return {
            "slot_id": result.slot_id,
            "scheduled_at_ms": result.scheduled_at_ms,
            "deadline_at_ms": result.deadline_at_ms,
            "revisions_created": list(result.revisions_created),
        }

    def _handle_create_revision(
        self, payload: dict[str, object], actor: str, if_match: str | None
    ) -> dict[str, object]:
        delivery_id = _required_string(payload, "delivery_id")
        expected = self._check_version("delivery", delivery_id, if_match)
        result = self._create_revision_uc.execute(
            delivery_id,
            expected_row_version=expected,
            draft=RevisionDraft(
                caption=_optional_string(payload.get("caption")),
                variant_id=_optional_string(payload.get("variant_id")),
            ),
            actor=actor,
        )
        return {
            "delivery_id": result.delivery_id,
            "revision_id": result.revision.payload["revision_id"],
            "payload_hash": result.revision.payload_hash,
            "state": result.delivery_state.value,
            "row_version": result.row_version,
        }

    def _approve(
        self,
        payload: dict[str, object],
        actor: str,
        idempotency_key: str | None,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ValueError("Idempotency-Key is required")
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("approval items must be a list")
        items = tuple(
            ApprovalItem(
                delivery_id=_required_string(item, "delivery_id"),
                revision_id=_required_string(item, "revision_id"),
                payload_hash=_required_string(item, "payload_hash"),
                expected_row_version=int(item["expected_row_version"]),
            )
            for item in raw_items
            if isinstance(item, Mapping)
        )
        if len(items) != len(raw_items):
            raise ValueError("each approval item must be an object")
        result = self._approve_group.execute(
            items, actor=actor, principal="bff", idempotency_key=idempotency_key
        )
        return {
            "approvals": [
                {
                    "approval_id": approval.id,
                    "revision_id": approval.revision_id,
                    "payload_hash": approval.payload_hash,
                    "actor_id": approval.actor_id,
                    "created_at_ms": approval.created_at_ms,
                }
                for approval in result.approvals
            ],
            "replayed": result.replayed,
        }

    def _set_controls(
        self, operation: str, payload: dict[str, object], actor: str, correlation_id: str
    ) -> dict[str, object]:
        if operation == "controls.mode":
            result = self._controls.set_mode(
                PublishMode(_required_string(payload, "mode").upper()),
                actor=actor,
                correlation_id=correlation_id,
            )
        elif operation == "controls.pause":
            result = self._controls.pause(actor=actor, correlation_id=correlation_id)
        else:
            result = self._controls.resume(actor=actor, correlation_id=correlation_id)
        return {
            "mode": result.controls.mode.value,
            "dispatch_epoch": result.controls.dispatch_epoch,
            "global_pause": result.controls.global_pause,
            "channel_id": result.channel_id,
            "channel_paused": result.channel_paused,
        }

    def _upload_asset(
        self,
        payload: dict[str, object],
        *,
        idempotency_key: str | None,
        actor: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ValueError("Idempotency-Key is required")
        stream = payload.get("stream")
        if not callable(getattr(stream, "read", None)):
            raise ValueError("asset upload stream is required")
        result = self._upload_asset_uc.execute(
            idempotency_key=idempotency_key,
            actor=actor,
            stream=stream,
            filename=str(payload.get("filename") or "upload"),
            content_type=str(payload.get("content_type") or "application/octet-stream"),
        )
        return {
            "job_id": result.job_id,
            "asset_id": result.asset_id,
            "source_sha256": result.source_sha256,
            "state": result.state,
        }


def _parse_etag(value: str | None) -> tuple[str, str, int]:
    if value is None:
        raise ValueError("If-Match is required")
    match = _ETAG.fullmatch(value.strip())
    if match is None:
        raise ValueError("If-Match has an unsupported format")
    return match.group(1), match.group(2), int(match.group(3))


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
