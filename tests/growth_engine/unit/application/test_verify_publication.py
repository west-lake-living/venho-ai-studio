from __future__ import annotations

import json
from dataclasses import replace

import pytest

from growth_engine.adapters.outbound.meta.platform_reader import PlatformReader
from growth_engine.application.verification.verify_publication import (
    PlatformPostResult,
    VerificationCandidate,
    VerifyPublication,
)
from growth_engine.domain.channels.channel import ChannelConfig
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.publishing.execution import Execution, ExecutionState


class FixedClock:
    def now_ms(self) -> int:
        return 1_800_000_000_000


class FixedIds:
    def __init__(self) -> None:
        self._index = 0

    def new_id(self) -> str:
        self._index += 1
        return f"synthetic-id-{self._index}"


class FakeReader:
    def __init__(self, result: PlatformPostResult) -> None:
        self.result = result
        self.calls = []

    def read_post(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeStore:
    def __init__(self, candidate: VerificationCandidate) -> None:
        self.candidate = candidate
        self.commit = None

    def read_candidate(self, delivery_id: str):
        assert delivery_id == self.candidate.delivery.id
        return self.candidate

    def commit_verification(self, candidate, **kwargs):
        self.commit = kwargs
        return True


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")


class FakeTransport:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse(self.body)


def _candidate(state: DeliveryState = DeliveryState.REPORTED_PUBLISHED) -> VerificationCandidate:
    execution = Execution(
        id="synthetic-execution",
        delivery_id="synthetic-delivery",
        command_id="synthetic-command",
        grant_id="synthetic-grant",
        state=ExecutionState.REPORTED,
        grant_expires_at_ms=1_800_000_060_000,
        receipt_due_at_ms=1_800_000_900_000,
        platform_post_id="synthetic-post",
    )
    capability = {
        "_synthetic": True,
        "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
    }
    config = ChannelConfig(
        id="synthetic-config",
        channel_id="synthetic-channel",
        version=1,
        make_route_ref="GE_MAKE_WEBHOOK_URL_SYNTHETIC",
        graph_api_version="v-synthetic",
        capability=capability,
    )
    return VerificationCandidate(
        delivery=Delivery("synthetic-delivery", state),
        channel_id="synthetic-channel",
        remote_page_id="synthetic-page",
        platform_post_id="synthetic-post",
        expected_caption="synthetic caption",
        channel_config=config,
        execution=execution,
        previous_visibility="VISIBLE" if state is DeliveryState.PUBLISHED else None,
    )


def test_exists_and_page_match_transitions_to_published() -> None:
    store = FakeStore(_candidate())
    reader = FakeReader(PlatformPostResult("EXISTS", "MATCH", True, True, "synthetic-time"))

    result = VerifyPublication(store, reader, FixedClock(), FixedIds()).execute("synthetic-delivery")

    assert result.outcome == "VERIFIED"
    assert result.delivery_state is DeliveryState.PUBLISHED
    assert store.commit["quality"] == "PASS"
    assert store.commit["updated_execution"].state is ExecutionState.REPORTED


def test_expired_read_token_keeps_reported_state_and_schedules_retry() -> None:
    store = FakeStore(_candidate())
    reader = FakeReader(PlatformPostResult("UNAVAILABLE", "UNKNOWN", error_kind="AUTH"))

    result = VerifyPublication(store, reader, FixedClock(), FixedIds()).execute("synthetic-delivery")

    assert result.outcome == "UNAVAILABLE"
    assert result.delivery_state is DeliveryState.REPORTED_PUBLISHED
    assert result.retry_at_ms == FixedClock().now_ms() + 5 * 60_000
    assert store.commit["incident"]["incident_type"] == "META_READ_PERMISSION"
    assert store.commit["updated_delivery"].state is DeliveryState.REPORTED_PUBLISHED


def test_confirmed_not_found_moves_to_unknown_and_opens_critical_incident() -> None:
    store = FakeStore(_candidate())
    reader = FakeReader(PlatformPostResult("NOT_FOUND", "UNKNOWN"))

    result = VerifyPublication(store, reader, FixedClock(), FixedIds()).execute("synthetic-delivery")

    assert result.outcome == "MISMATCH"
    assert result.delivery_state is DeliveryState.UNKNOWN
    assert store.commit["updated_execution"].state is ExecutionState.UNKNOWN
    assert store.commit["incident"]["severity"] == "CRITICAL"


def test_deleted_post_updates_visibility_without_republishing() -> None:
    store = FakeStore(_candidate(DeliveryState.PUBLISHED))
    reader = FakeReader(PlatformPostResult("NOT_FOUND", "UNKNOWN"))

    result = VerifyPublication(store, reader, FixedClock(), FixedIds()).execute("synthetic-delivery")

    assert result.outcome == "VISIBILITY_CHANGED"
    assert result.delivery_state is DeliveryState.PUBLISHED
    assert result.platform_visibility == "DELETED"
    assert store.commit["observed_visibility"] == "DELETED"
    assert store.commit["retry_at_ms"] is None


def test_verification_retry_schedule_caps_at_six_hours() -> None:
    candidate = replace(_candidate(), attempt_number=8)
    store = FakeStore(candidate)
    reader = FakeReader(PlatformPostResult("UNAVAILABLE", "UNKNOWN", error_kind="TRANSIENT"))

    result = VerifyPublication(store, reader, FixedClock(), FixedIds()).execute("synthetic-delivery")

    assert result.retry_at_ms == FixedClock().now_ms() + 6 * 60 * 60_000


def test_platform_reader_uses_configured_version_and_synthetic_fields() -> None:
    capability = {
        "_synthetic": True,
        "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
        "post_fields": ["synthetic_id", "synthetic_owner", "synthetic_caption", "synthetic_created", "synthetic_media"],
        "post_collection_edge": "synthetic-post-edge",
        "post_id_path": "synthetic_id",
        "owner_page_id_path": "synthetic_owner.page_id",
        "caption_path": "synthetic_caption",
        "created_time_path": "synthetic_created",
        "media_path": "synthetic_media",
    }
    config = replace(_candidate().channel_config, capability=capability)
    transport = FakeTransport(
        {
            "_synthetic": True,
            "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
            "synthetic_id": "synthetic-post",
            "synthetic_owner": {"page_id": "synthetic-page"},
            "synthetic_caption": "synthetic caption  \nsecond line",
            "synthetic_created": "synthetic-time",
            "synthetic_media": {"present": True},
        }
    )

    result = PlatformReader(access_token="synthetic-token", transport=transport).read_post(
        channel_config=config,
        remote_page_id="synthetic-page",
        platform_post_id="synthetic-post",
        expected_caption="synthetic caption\nsecond line",
    )

    assert result.existence == "EXISTS"
    assert result.ownership == "MATCH"
    assert result.media_present is True
    assert result.caption_match is True
    assert "/v-synthetic/synthetic-post" in transport.calls[0]["url"]
    assert "synthetic-token" not in transport.calls[0]["url"]


def test_platform_reader_verifies_instagram_media_id_and_account_with_configured_paths() -> None:
    capability = {
        "_synthetic": True,
        "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
        "post_fields": [
            "synthetic_media_identifier",
            "synthetic_ig_owner",
            "synthetic_caption",
            "synthetic_created",
            "synthetic_media",
        ],
        "post_collection_edge": "synthetic-ig-media-edge",
        "platform_post_id_path": "synthetic_media_identifier",
        "owner_account_id_path": "synthetic_ig_owner.account_id",
        "caption_path": "synthetic_caption",
        "created_time_path": "synthetic_created",
        "media_path": "synthetic_media",
    }
    config = replace(_candidate().channel_config, capability=capability)
    transport = FakeTransport(
        {
            "_synthetic": True,
            "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
            "synthetic_media_identifier": "ig-media-synthetic-123",
            "synthetic_ig_owner": {"account_id": "ig-business-synthetic"},
            "synthetic_caption": "synthetic caption",
            "synthetic_created": "synthetic-time",
            "synthetic_media": {"present": True},
        }
    )

    result = PlatformReader(access_token="synthetic-token", transport=transport).read_post(
        channel_config=config,
        remote_account_id="ig-business-synthetic",
        platform_post_id="ig-media-synthetic-123",
        expected_caption="synthetic caption",
    )

    assert result.existence == "EXISTS"
    assert result.ownership == "MATCH"
    assert result.media_present is True
    assert result.caption_match is True
    assert "/v-synthetic/ig-media-synthetic-123" in transport.calls[0]["url"]


def test_platform_reader_refuses_unverified_meta_fields() -> None:
    config = replace(_candidate().channel_config, capability={"post_fields": ["REQUIRED_FROM_P0"]})
    reader = PlatformReader(access_token="synthetic-token", transport=FakeTransport({}))

    with pytest.raises(ValueError, match="verified Meta post fields"):
        reader.read_post(
            channel_config=config,
            remote_page_id="synthetic-page",
            platform_post_id="synthetic-post",
            expected_caption="synthetic caption",
        )
