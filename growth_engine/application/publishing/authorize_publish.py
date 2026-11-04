from __future__ import annotations

import hashlib
import re
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.channels.channel import Channel, ChannelConfig, config_hash
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.media_policy import FACEBOOK_PHOTO_V1
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.execution import Execution
from growth_engine.domain.publishing.preflight import PreflightInput, run_preflight
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
from growth_engine.domain.publishing.window import PublishingPolicy


@dataclass(frozen=True)
class AuthorizePublishCommand:
    command_token: str
    payload_hash: str
    media_report_http_status: int
    media_report_content_type: str
    principal_id: str
    principal_channel_key: str
    correlation_id: str


@dataclass(frozen=True)
class AuthorizePublishResult:
    execute: bool
    reason: str | None = None
    execution_id: str | None = None
    grant_id: str | None = None
    grant_expires_at_ms: int | None = None
    remote_page_id: str | None = None
    caption: str | None = None


@dataclass(frozen=True)
class AuthorizeCandidate:
    command: OutboxCommand
    command_payload_hash: str
    command_dispatch_epoch: str
    delivery: Delivery
    current_revision_id: str
    active_approval_id: str | None
    revision: DeliveryRevision
    approval: ApprovalDecision | None
    approval_revoked: bool
    channel: Channel
    channel_config: ChannelConfig
    variant: MediaVariant | None
    qc_report: QcReport | None
    facts_valid: bool
    has_live_execution: bool

    def __post_init__(self) -> None:
        for name in ("command_payload_hash", "command_dispatch_epoch", "current_revision_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.approval_revoked) is not bool or type(self.facts_valid) is not bool:
            raise ValueError("candidate validity flags must be boolean")
        if type(self.has_live_execution) is not bool:
            raise ValueError("has_live_execution must be a boolean")


class VerifiedCommandClaims(Protocol):
    command_id: str
    revision_id: str
    channel_id: str
    payload_hash: str
    dispatch_epoch: str
    audience: str
    expires_at_ms: int


class CapabilityVerifier(Protocol):
    def verify(self, token: str, audience: str, now_ms: int) -> VerifiedCommandClaims: ...


class MediaVerifier(Protocol):
    def verify(self, object_key: str, sha256: str) -> bool: ...


class AuthorizeTransaction(Protocol):
    def current_controls(self) -> RuntimeControls | None: ...
    def get_candidate(self, command_id: str) -> AuthorizeCandidate | None: ...

    def commit_authorized(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        execution: Execution,
        *,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool: ...

    def commit_blocked(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        *,
        expected_row_version: int,
        blocked_reason: str,
        audit_event_id: str,
        incident_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool: ...

    def commit_expired(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        *,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool: ...


class AuthorizePublishStore(Protocol):
    def resolve_channel_by_key(self, channel_key: str) -> Channel | None: ...
    def read_candidate(self, command_id: str) -> AuthorizeCandidate | None: ...
    def begin_immediate(self) -> AbstractContextManager[AuthorizeTransaction]: ...


class AuthorizePublish:
    """Single-gate command authorization with local preflight and an atomic commit port."""

    def __init__(
        self,
        store: AuthorizePublishStore,
        tokens: CapabilityVerifier,
        media_store: MediaVerifier,
        clock: Clock,
        ids: IdGenerator,
        policy: PublishingPolicy,
    ) -> None:
        self._store = store
        self._tokens = tokens
        self._media_store = media_store
        self._clock = clock
        self._ids = ids
        self._policy = policy

    def execute(self, command: AuthorizePublishCommand) -> AuthorizePublishResult:
        _validate_command(command)
        now_ms = self._clock.now_ms()
        principal_channel = self._store.resolve_channel_by_key(command.principal_channel_key)
        if principal_channel is None:
            raise _forbidden()
        audience = f"make-route:{principal_channel.id}"
        try:
            claims = self._tokens.verify(command.command_token, audience, now_ms)
        except ValueError as error:
            raise _capability_invalid() from error
        if claims.channel_id != principal_channel.id or claims.audience != audience:
            raise _forbidden()
        if claims.payload_hash != command.payload_hash:
            raise _capability_invalid()

        if command.media_report_http_status != 200 or command.media_report_content_type.strip().casefold() != "image/jpeg":
            return AuthorizePublishResult(False, reason="MEDIA_FETCH_FAILED")

        outside = self._store.read_candidate(claims.command_id)
        if outside is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy lệnh đăng.")
        if not _claims_match_candidate(outside, claims, command, principal_channel):
            raise _capability_invalid()
        outside_identity = _publish_identity(outside)
        media_hash_matches = _verify_media(self._media_store, outside)

        with self._store.begin_immediate() as tx:
            candidate = tx.get_candidate(claims.command_id)
            if candidate is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy lệnh đăng.")
            if candidate.command.state is CommandState.AUTHORIZED:
                return AuthorizePublishResult(False, reason="ALREADY_AUTHORIZED")
            if not _same_publish_identity(outside_identity, candidate):
                return AuthorizePublishResult(False, reason="PREFLIGHT_BLOCKED")
            if not _claims_match_candidate(candidate, claims, command, principal_channel):
                return AuthorizePublishResult(False, reason="PREFLIGHT_BLOCKED")
            if candidate.command.state not in {CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED}:
                return AuthorizePublishResult(False, reason="PREFLIGHT_BLOCKED")
            if candidate.delivery.state is not DeliveryState.QUEUED or candidate.has_live_execution:
                return AuthorizePublishResult(False, reason="PREFLIGHT_BLOCKED")

            controls = tx.current_controls()
            if controls is None:
                return AuthorizePublishResult(False, reason="PAUSED")
            if (
                controls.mode is not PublishMode.LIVE_MANUAL
                or controls.global_pause
                or not candidate.channel.enabled
                or candidate.channel.paused
            ):
                return AuthorizePublishResult(False, reason="PAUSED")

            payload = candidate.revision.payload
            if (
                claims.dispatch_epoch != candidate.command_dispatch_epoch
                or candidate.command_dispatch_epoch != controls.dispatch_epoch
            ):
                return self._block(
                    tx,
                    candidate,
                    now_ms=now_ms,
                    correlation_id=command.correlation_id,
                    blocked_reason="PF_EPOCH_MISMATCH",
                    response_reason="EPOCH_MISMATCH",
                )

            deadline_at_ms = _integer(payload.get("deadline_at_ms"), "deadline_at_ms")
            if now_ms > deadline_at_ms:
                updated_command = candidate.command.expire(now_ms=now_ms)
                updated_delivery, _events = candidate.delivery.apply(
                    DeliveryEvent.EXPIRE,
                    {
                        "now_ms": now_ms,
                        "deadline_at_ms": deadline_at_ms,
                        "no_execution_live": not candidate.has_live_execution,
                    },
                )
                committed = tx.commit_expired(
                    candidate,
                    updated_command,
                    updated_delivery,
                    expected_row_version=candidate.delivery.row_version,
                    audit_event_id=self._ids.new_id(),
                    correlation_id=command.correlation_id,
                    at_ms=now_ms,
                )
                return AuthorizePublishResult(False, reason="WINDOW_CLOSED") if committed else AuthorizePublishResult(False, reason="PREFLIGHT_BLOCKED")

            preflight = _preflight_input(candidate, now_ms, deadline_at_ms, media_hash_matches)
            issues = run_preflight(preflight)
            blocking_issue = next((issue for issue in issues if issue.blocking), None)
            if blocking_issue is not None:
                return self._block(
                    tx,
                    candidate,
                    now_ms=now_ms,
                    correlation_id=command.correlation_id,
                    blocked_reason=blocking_issue.code,
                    response_reason="PREFLIGHT_BLOCKED",
                )
            if issues:
                reason = "PAUSED" if any(issue.code in {"PF_MODE_FORBIDS", "PF_PAUSED"} for issue in issues) else "MEDIA_FETCH_FAILED"
                return AuthorizePublishResult(False, reason=reason)

            execution = Execution.authorize(
                execution_id=self._ids.new_id(),
                delivery_id=candidate.delivery.id,
                command_id=candidate.command.id,
                grant_id=self._ids.new_id(),
                now_ms=now_ms,
                deadline_at_ms=deadline_at_ms,
                policy=self._policy,
            )
            updated_command = candidate.command.authorize()
            updated_delivery, _events = candidate.delivery.apply(
                DeliveryEvent.AUTHORIZE,
                {"preflight_pass": True, "now_ms": now_ms},
            )
            committed = tx.commit_authorized(
                candidate,
                updated_command,
                updated_delivery,
                execution,
                expected_row_version=candidate.delivery.row_version,
                audit_event_id=self._ids.new_id(),
                correlation_id=command.correlation_id,
                at_ms=now_ms,
            )
            if not committed:
                return AuthorizePublishResult(False, reason="ALREADY_AUTHORIZED")
            return AuthorizePublishResult(
                True,
                execution_id=execution.id,
                grant_id=execution.grant_id,
                grant_expires_at_ms=execution.grant_expires_at_ms,
                remote_page_id=candidate.channel.remote_account_id,
                caption=payload.get("caption") if isinstance(payload.get("caption"), str) else None,
            )

    def _block(
        self,
        tx: AuthorizeTransaction,
        candidate: AuthorizeCandidate,
        *,
        now_ms: int,
        correlation_id: str,
        blocked_reason: str,
        response_reason: str,
    ) -> AuthorizePublishResult:
        updated_command = candidate.command.cancel()
        updated_delivery, _events = candidate.delivery.apply(
            DeliveryEvent.PREFLIGHT_BLOCK,
            {"preflight_blocking": True, "now_ms": now_ms},
        )
        committed = tx.commit_blocked(
            candidate,
            updated_command,
            updated_delivery,
            expected_row_version=candidate.delivery.row_version,
            blocked_reason=blocked_reason,
            audit_event_id=self._ids.new_id(),
            incident_id=self._ids.new_id(),
            correlation_id=correlation_id,
            at_ms=now_ms,
        )
        return AuthorizePublishResult(False, reason=response_reason if committed else "PREFLIGHT_BLOCKED")


def authorize_publish(use_case: AuthorizePublish, command: AuthorizePublishCommand) -> AuthorizePublishResult:
    return use_case.execute(command)


def _validate_command(command: AuthorizePublishCommand) -> None:
    for name in ("command_token", "principal_id", "principal_channel_key", "correlation_id"):
        value = getattr(command, name)
        if not isinstance(value, str) or not value.strip():
            raise DomainError(ErrorCode.VALIDATION, "Yêu cầu cấp quyền đăng không hợp lệ.")
    if len(command.payload_hash) != 64 or any(char not in "0123456789abcdef" for char in command.payload_hash):
        raise DomainError(ErrorCode.VALIDATION, "Yêu cầu cấp quyền đăng không hợp lệ.")
    if type(command.media_report_http_status) is not int:
        raise DomainError(ErrorCode.VALIDATION, "Yêu cầu cấp quyền đăng không hợp lệ.")
    if not isinstance(command.media_report_content_type, str):
        raise DomainError(ErrorCode.VALIDATION, "Yêu cầu cấp quyền đăng không hợp lệ.")


def _claims_match_candidate(
    candidate: AuthorizeCandidate,
    claims: VerifiedCommandClaims,
    command: AuthorizePublishCommand,
    principal_channel: Channel,
) -> bool:
    return (
        candidate.command.id == claims.command_id
        and candidate.command.delivery_id == candidate.delivery.id
        and candidate.command.revision_id == claims.revision_id
        and candidate.current_revision_id == claims.revision_id
        and candidate.command_payload_hash == claims.payload_hash == command.payload_hash
        and candidate.channel.id == claims.channel_id == principal_channel.id
        and candidate.channel.channel_key == command.principal_channel_key
        and candidate.channel.environment in {"test", "production"}
    )


def _publish_identity(candidate: AuthorizeCandidate) -> tuple[object, ...]:
    variant = candidate.variant
    approval = candidate.approval
    return (
        candidate.command.id,
        candidate.command.delivery_id,
        candidate.command.revision_id,
        candidate.command_payload_hash,
        candidate.command_dispatch_epoch,
        candidate.delivery.id,
        candidate.delivery.state,
        candidate.current_revision_id,
        candidate.active_approval_id,
        candidate.approval_revoked,
        None if approval is None else (approval.id, approval.revision_id, approval.payload_hash, approval.decision),
        candidate.revision.payload_hash,
        None if variant is None else (variant.id, variant.sha256, variant.object_key),
        candidate.channel.id,
        candidate.channel.environment,
        candidate.channel.channel_key,
        candidate.channel.platform,
        candidate.channel.remote_account_id,
        candidate.channel.enabled,
        candidate.channel.paused,
        config_hash(candidate.channel_config),
        None if candidate.qc_report is None else (
            candidate.qc_report.id,
            candidate.qc_report.variant_id,
            candidate.qc_report.caption_hash,
            candidate.qc_report.ruleset_hash,
            candidate.qc_report.fact_snapshot_hash,
            candidate.qc_report.decision,
        ),
        candidate.facts_valid,
    )


def _same_publish_identity(identity: tuple[object, ...], candidate: AuthorizeCandidate) -> bool:
    return identity == _publish_identity(candidate)


def _verify_media(media_store: MediaVerifier, candidate: AuthorizeCandidate) -> bool:
    variant = candidate.variant
    if variant is None:
        return False
    media = candidate.revision.payload.get("media")
    if not isinstance(media, list) or not media or not isinstance(media[0], dict):
        return False
    expected_sha = media[0].get("sha256")
    if not isinstance(expected_sha, str) or expected_sha != variant.sha256:
        return False
    try:
        return media_store.verify(variant.object_key, expected_sha)
    except (OSError, ValueError):
        return False


def _preflight_input(
    candidate: AuthorizeCandidate,
    now_ms: int,
    deadline_at_ms: int,
    media_hash_matches: bool,
) -> PreflightInput:
    payload = candidate.revision.payload
    variant = candidate.variant
    report = candidate.qc_report
    approval = candidate.approval
    caption = payload.get("caption")
    caption = caption if isinstance(caption, str) else ""
    media = payload.get("media")
    media_ref = media[0] if isinstance(media, list) and media and isinstance(media[0], dict) else {}
    qc_report_id = payload.get("qc_report_id")
    config_matches = payload.get("channel_config_hash") == config_hash(candidate.channel_config)
    approval_valid = (
        candidate.active_approval_id is not None
        and approval is not None
        and approval.id == candidate.active_approval_id
        and approval.decision is ApprovalType.APPROVE
        and approval.revision_id == candidate.current_revision_id
        and approval.payload_hash == candidate.revision.payload_hash
        and not candidate.approval_revoked
    )
    qc_valid = (
        variant is not None
        and report is not None
        and report.id == qc_report_id
        and report.variant_id == variant.id
        and report.ruleset_hash == payload.get("ruleset_hash")
        and report.fact_snapshot_hash == payload.get("fact_snapshot_hash")
        and report.caption_hash == hashlib.sha256(caption.encode("utf-8")).hexdigest()
        and report.decision in {QcDecision.PASS, QcDecision.REVIEW}
    )
    variant_safe = variant is not None and variant.qc_status is not VariantQcStatus.QUARANTINED
    profile = FACEBOOK_PHOTO_V1.spec
    media_policy_valid = (
        variant is not None
        and variant.mime == "image/jpeg"
        and max(variant.width, variant.height) <= profile.max_long_side_px
        and variant.byte_size <= profile.max_bytes
    )
    caption_hash_matches = bool(
        report is not None
        and report.caption_hash == hashlib.sha256(caption.encode("utf-8")).hexdigest()
    )
    return PreflightInput(
        approval_valid=approval_valid,
        channel_enabled=candidate.channel.enabled,
        config_hash_matches=config_matches,
        media_exists=variant is not None and bool(variant.object_key),
        media_hash_matches=media_hash_matches and media_ref.get("sha256") == (variant.sha256 if variant else None),
        media_policy_valid=media_policy_valid,
        media_fetch_ok=True,
        caption_hash_matches=caption_hash_matches,
        caption_has_placeholder=_caption_has_placeholder(caption),
        facts_valid=candidate.facts_valid,
        qc_revoked=not qc_valid or not variant_safe,
        now_ms=now_ms,
        deadline_at_ms=deadline_at_ms,
        mode_allows=True,
        paused=False,
        epoch_matches=True,
    )


_PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}|\b(?:TODO|TBD|PLACEHOLDER|REPLACE_ME|INSERT_HERE)\b", re.IGNORECASE)


def _caption_has_placeholder(caption: str) -> bool:
    return _PLACEHOLDER.search(caption) is not None


def _integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise DomainError(ErrorCode.VALIDATION, f"Trường {name} không hợp lệ.")
    return value


def _forbidden() -> DomainError:
    return DomainError(ErrorCode.FORBIDDEN, "Bạn không có quyền thực hiện thao tác này.")


def _capability_invalid() -> DomainError:
    return DomainError(ErrorCode.CAPABILITY_INVALID, "Lệnh đăng không hợp lệ hoặc đã hết hạn.")
