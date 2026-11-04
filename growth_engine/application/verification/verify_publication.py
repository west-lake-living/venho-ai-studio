from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.channels.channel import ChannelConfig
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.publishing.execution import Execution, ExecutionState


_RETRY_MINUTES = (5, 15, 60, 360)


@dataclass(frozen=True)
class VerificationCandidate:
    delivery: Delivery
    channel_id: str
    remote_page_id: str
    platform_post_id: str
    expected_caption: str
    channel_config: ChannelConfig
    attempt_number: int = 0
    execution: Execution | None = None
    previous_visibility: str | None = None


@dataclass(frozen=True)
class PlatformPostResult:
    existence: str
    ownership: str
    media_present: bool | None = None
    caption_match: bool | None = None
    created_time: str | None = None
    error_kind: str | None = None


class PublicationReader(Protocol):
    def read_post(
        self,
        *,
        channel_config: ChannelConfig,
        remote_page_id: str,
        platform_post_id: str,
        expected_caption: str,
    ) -> PlatformPostResult: ...


class VerificationStore(Protocol):
    def read_candidate(self, delivery_id: str) -> VerificationCandidate | None: ...

    def commit_verification(
        self,
        candidate: VerificationCandidate,
        *,
        verification_id: str,
        existence: str,
        ownership: str,
        media_present: bool | None,
        caption_match: bool | None,
        quality: str,
        platform_created_at: str | None,
        updated_delivery: Delivery,
        updated_execution: Execution | None,
        observed_visibility: str | None,
        retry_at_ms: int | None,
        incident: dict[str, object] | None,
        at_ms: int,
    ) -> bool: ...


@dataclass(frozen=True)
class VerifyPublicationResult:
    outcome: str
    delivery_state: DeliveryState
    retry_at_ms: int | None = None
    platform_visibility: str | None = None


class VerifyPublication:
    def __init__(
        self,
        store: VerificationStore,
        reader: PublicationReader,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._store = store
        self._reader = reader
        self._clock = clock
        self._ids = ids

    def execute(self, delivery_id: str) -> VerifyPublicationResult:
        candidate = self._store.read_candidate(delivery_id)
        if candidate is None:
            raise ValueError("delivery verification target was not found")
        if candidate.delivery.state not in {DeliveryState.REPORTED_PUBLISHED, DeliveryState.PUBLISHED}:
            raise ValueError("only reported or published deliveries can be verified")

        now_ms = self._clock.now_ms()
        result = self._reader.read_post(
            channel_config=candidate.channel_config,
            remote_page_id=candidate.remote_page_id,
            platform_post_id=candidate.platform_post_id,
            expected_caption=candidate.expected_caption,
        )
        delivery = candidate.delivery
        execution = candidate.execution
        retry_at_ms: int | None = None
        incident: dict[str, object] | None = None
        visibility: str | None = None
        quality = _quality(result)
        outcome = "UNAVAILABLE"
        updated_execution = execution

        if delivery.state is DeliveryState.PUBLISHED and result.existence != "UNAVAILABLE":
            observed_visibility = "DELETED" if result.existence == "NOT_FOUND" else (
                "VISIBLE" if result.existence == "EXISTS" and result.ownership == "MATCH" else "UNKNOWN"
            )
            visibility = observed_visibility
            if candidate.previous_visibility != observed_visibility:
                delivery, _events = delivery.apply(
                    DeliveryEvent.VISIBILITY_CHANGE,
                    {"now_ms": now_ms},
                )
                outcome = "VISIBILITY_CHANGED"
            else:
                outcome = "VERIFIED"
        elif result.existence == "EXISTS" and result.ownership == "MATCH":
            delivery, _events = delivery.apply(
                DeliveryEvent.VERIFY_OK,
                {"now_ms": now_ms, "existence": "EXISTS", "ownership": "MATCH"},
            )
            outcome = "VERIFIED"
        elif result.existence in {"NOT_FOUND", "MISMATCH"}:
            delivery, _events = delivery.apply(
                DeliveryEvent.VERIFY_MISMATCH,
                {"now_ms": now_ms, "existence": result.existence, "ownership": result.ownership},
            )
            if execution is not None and execution.state is ExecutionState.REPORTED:
                updated_execution = execution.verify_mismatch()
            incident = {
                "incident_id": self._ids.new_id(),
                "incident_type": "PUBLICATION_MISMATCH",
                "severity": "CRITICAL",
                "delivery_id": delivery.id,
                "details": {"existence": result.existence, "ownership": result.ownership},
            }
            outcome = "MISMATCH"
        else:
            retry_index = min(max(candidate.attempt_number, 0), len(_RETRY_MINUTES) - 1)
            retry_at_ms = now_ms + _RETRY_MINUTES[retry_index] * 60_000
            if result.error_kind in {"AUTH", "PERMISSION"}:
                incident = {
                    "incident_id": self._ids.new_id(),
                    "incident_type": "META_READ_PERMISSION",
                    "severity": "HIGH",
                    "delivery_id": delivery.id,
                    "details": {"error_kind": result.error_kind},
                }
            outcome = "UNAVAILABLE"

        committed = self._store.commit_verification(
            candidate,
            verification_id=self._ids.new_id(),
            existence=result.existence,
            ownership=result.ownership,
            media_present=result.media_present,
            caption_match=result.caption_match,
            quality=quality,
            platform_created_at=result.created_time,
            updated_delivery=delivery,
            updated_execution=updated_execution,
            observed_visibility=visibility,
            retry_at_ms=retry_at_ms,
            incident=incident,
            at_ms=now_ms,
        )
        if not committed:
            return VerifyPublicationResult("STALE", candidate.delivery.state)
        return VerifyPublicationResult(outcome, delivery.state, retry_at_ms, visibility)


def _quality(result: PlatformPostResult) -> str:
    return (
        "PASS"
        if result.existence == "EXISTS"
        and result.ownership == "MATCH"
        and result.media_present is True
        and result.caption_match is True
        else "WARNING"
    )
