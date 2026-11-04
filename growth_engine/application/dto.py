from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class NormalizedImage:
    data: bytes
    width: int
    height: int
    sha256: str
    mime: str = "image/jpeg"


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    sha256: str
    byte_size: int


@dataclass(frozen=True)
class TransportResult:
    accepted: bool
    error_class: str | None = None
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class CommandClaims:
    command_id: str
    delivery_id: str
    revision_id: str
    channel_id: str
    remote_account_id: str
    payload_hash: str
    audience: str
    expires_at_ms: int


@dataclass(frozen=True)
class ChannelConfigView:
    channel_id: str
    remote_account_id: str
    platform: str
    graph_api_version: str


@dataclass(frozen=True)
class PostEvidence:
    post_id: str
    exists: str
    ownership: str
    created_at_ms: int | None = None
    caption: str | None = None
    media_present: str = "UNAVAILABLE"
    permalink: str | None = None


@dataclass(frozen=True)
class MetricSpec:
    name: str
    provider_field: str
    scope: str
    period: str


@dataclass(frozen=True)
class RawMetric:
    name: str
    value: int | None
    state: str
    observed_at_ms: int
    error_code: str | None = None


@dataclass(frozen=True)
class DraftRequest:
    project_id: str
    slot_id: str
    lane: str
    at_ms: int
    facts: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DraftPackage:
    topic_key: str
    pillar: str
    brief: str
    fact_keys: tuple[str, ...]
    captions_by_profile: Mapping[str, str] = field(default_factory=dict)
    image_options: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True)
class VariantView:
    variant_id: str
    sha256: str
    width: int
    height: int
    mime: str
    object_key: str
    qc_status: str


@dataclass(frozen=True)
class FactSnapshot:
    facts: Mapping[str, object]
    snapshot_hash: str


@dataclass(frozen=True)
class EffectiveQcPolicy:
    project: str
    subject: str
    scenario: str | None
    ruleset_hash: str
    forbidden: tuple[str, ...] = ()


@dataclass(frozen=True)
class QcResult:
    decision: str
    ruleset_hash: str
    caption_hash: str
    fact_snapshot_hash: str
    coverage_gaps: tuple[str, ...] = ()
    result_json: str = "{}"


@dataclass(frozen=True)
class CandidateInput:
    source: str
    external_key: str
    source_revision: str
    topic_key: str
    event_key: str | None
    event_start_at_ms: int | None
    event_end_at_ms: int | None
    expires_at_ms: int
    payload: Mapping[str, object]
    source_hash: str


@dataclass(frozen=True)
class NotificationMessage:
    severity: str
    title: str
    body: str
    delivery_id: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class NotifyResult:
    accepted: bool
    message_id: str | None = None
    error: str | None = None
