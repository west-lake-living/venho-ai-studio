from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Mapping

from growth_engine.application.dto import (
    CandidateInput,
    ChannelConfigView,
    CommandClaims,
    DraftPackage,
    DraftRequest,
    EffectiveQcPolicy,
    FactSnapshot,
    MetricSpec,
    NormalizedImage,
    NotificationMessage,
    NotifyResult,
    PostEvidence,
    QcResult,
    RawMetric,
    StoredObject,
    TransportResult,
    VariantView,
)
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.content import CandidateSource, ContentGenerator, FactSource, QcEvaluator
from growth_engine.application.ports.media import ImageProcessor, MediaStore, SignedUrlIssuer
from growth_engine.application.ports.notify import Notifier
from growth_engine.application.ports.platform import MetricsSource, PlatformReader
from growth_engine.application.ports.publishing import CapabilityTokens, PublishTransport
from growth_engine.domain.media.media_policy import TransformSpec


# Synthetic fixtures here are local test data; replace with real fixtures from P0-T03/P0-T04.
SYNTHETIC_MARKER = {
    "_synthetic": True,
    "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
}


class FakeClock:
    def __init__(self, current_time_ms: int = 0) -> None:
        self.current_time_ms = current_time_ms

    def now_ms(self) -> int:
        return self.current_time_ms

    def set(self, value: int) -> None:
        self.current_time_ms = value


class SeqIds:
    def __init__(self, prefix: str = "synthetic-id") -> None:
        self.prefix = prefix
        self._next_value = 1

    def new_id(self) -> str:
        result = f"{self.prefix}-{self._next_value}"
        self._next_value += 1
        return result


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[NotificationMessage] = []

    def send(self, message: NotificationMessage) -> NotifyResult:
        self.messages.append(message)
        return NotifyResult(accepted=True, message_id=f"synthetic-message-{len(self.messages)}")


class FakePlatformReader:
    def __init__(self, posts: Mapping[str, PostEvidence] | None = None) -> None:
        self.posts = dict(posts or {})

    def read_post(self, channel: ChannelConfigView, post_id: str) -> PostEvidence:
        return self.posts.get(post_id, PostEvidence(post_id, "NOT_FOUND", "UNAVAILABLE"))

    def search_recent(
        self,
        channel: ChannelConfigView,
        since_ms: int,
        until_ms: int,
    ) -> list[PostEvidence]:
        return [
            post
            for post in self.posts.values()
            if post.created_at_ms is not None and since_ms <= post.created_at_ms <= until_ms
        ]


class FakeTransport:
    def __init__(self, result: TransportResult | None = None) -> None:
        self.result = result or TransportResult(accepted=True)
        self.deliveries: list[tuple[str, dict[str, object]]] = []

    def deliver(self, route_ref: str, envelope: dict[str, object]) -> TransportResult:
        self.deliveries.append((route_ref, dict(envelope)))
        return self.result


class FakeGenerator:
    def __init__(self, result: DraftPackage | None = None) -> None:
        self.result = result or DraftPackage(
            topic_key="synthetic-topic",
            pillar="synthetic-pillar",
            brief="synthetic brief",
            fact_keys=(),
            captions_by_profile={"default": "synthetic caption"},
        )
        self.requests: list[DraftRequest] = []

    def draft(self, request: DraftRequest) -> DraftPackage:
        self.requests.append(request)
        return self.result


class FakeQc:
    def __init__(self, result: QcResult | None = None) -> None:
        self.result = result or QcResult(
            decision="REVIEW",
            ruleset_hash="0" * 64,
            caption_hash="0" * 64,
            fact_snapshot_hash="0" * 64,
            coverage_gaps=("_synthetic_gap",),
            result_json='{"_synthetic":true}',
        )

    def evaluate(
        self,
        variant: VariantView,
        caption: str,
        facts: FactSnapshot,
        policy: EffectiveQcPolicy,
    ) -> QcResult:
        return self.result

    def compile_policy(self, project: str, subject: str, scenario: str | None) -> EffectiveQcPolicy:
        return EffectiveQcPolicy(project, subject, scenario, "0" * 64, ("_synthetic_rule",))


class FakeFactSource:
    def __init__(self, facts: Mapping[str, object] | None = None) -> None:
        self.facts = dict(facts or {"_synthetic": True})

    def approved_facts(self, keys: list[str], at_ms: int) -> FactSnapshot:
        return FactSnapshot(
            facts={key: self.facts[key] for key in keys if key in self.facts},
            snapshot_hash="0" * 64,
        )


class FakeCandidateSource:
    def __init__(self, candidates: list[CandidateInput] | None = None) -> None:
        self.candidates = list(candidates or [])

    def scan(self, now_ms: int) -> list[CandidateInput]:
        return list(self.candidates)


class FakeTokens:
    def __init__(self) -> None:
        self._claims_by_token: dict[str, CommandClaims] = {}
        self._counter = 1

    def issue(self, claims: CommandClaims) -> str:
        token = f"synthetic-capability-{self._counter}"
        self._counter += 1
        self._claims_by_token[token] = claims
        return token

    def verify(self, token: str, audience: str, now_ms: int) -> CommandClaims:
        claims = self._claims_by_token.get(token)
        if claims is None or claims.audience != audience or now_ms >= claims.expires_at_ms:
            raise ValueError("synthetic capability is invalid or expired")
        return claims


class FakeImageProcessor:
    def normalize(self, original: Path, spec: TransformSpec) -> NormalizedImage:
        data = b"synthetic-image-bytes"
        return NormalizedImage(
            data=data,
            width=min(100, spec.max_long_side_px),
            height=min(80, spec.max_long_side_px),
            sha256=sha256(data).hexdigest(),
        )


class FakeMediaStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_original(self, stream: BinaryIO, max_bytes: int) -> StoredObject:
        data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("synthetic media exceeds max_bytes")
        digest = sha256(data).hexdigest()
        key = f"synthetic/original/{digest}"
        self.objects[key] = data
        return StoredObject(key, digest, len(data))

    def put_variant(self, data: bytes, sha256_value: str) -> str:
        if sha256(data).hexdigest() != sha256_value:
            raise ValueError("variant hash does not match bytes")
        key = f"synthetic/variant/{sha256_value}"
        self.objects[key] = data
        return key

    def open(self, object_key: str) -> BinaryIO:
        try:
            return BytesIO(self.objects[object_key])
        except KeyError as exc:
            raise FileNotFoundError(object_key) from exc

    def verify(self, object_key: str, sha256_value: str) -> bool:
        data = self.objects.get(object_key)
        return data is not None and sha256(data).hexdigest() == sha256_value


class FakeSignedUrlIssuer:
    def media_url(self, sha256_value: str, command_id: str, expires_at_ms: int) -> str:
        return f"fake-media://{sha256_value}/{command_id}?expires_at_ms={expires_at_ms}"


class FakeMetricsSource:
    def __init__(self, metrics: list[RawMetric] | None = None) -> None:
        self.metrics = list(metrics or [])

    def fetch(
        self,
        channel: ChannelConfigView,
        post_id: str,
        metrics: list[MetricSpec],
    ) -> list[RawMetric]:
        names = {item.name for item in metrics}
        return [metric for metric in self.metrics if metric.name in names]


def assert_fakes_match_ports() -> None:
    pairs = (
        (FakeClock(), Clock),
        (SeqIds(), IdGenerator),
        (FakeNotifier(), Notifier),
        (FakePlatformReader(), PlatformReader),
        (FakeTransport(), PublishTransport),
        (FakeGenerator(), ContentGenerator),
        (FakeQc(), QcEvaluator),
        (FakeFactSource(), FactSource),
        (FakeCandidateSource(), CandidateSource),
        (FakeTokens(), CapabilityTokens),
        (FakeImageProcessor(), ImageProcessor),
        (FakeMediaStore(), MediaStore),
        (FakeSignedUrlIssuer(), SignedUrlIssuer),
        (FakeMetricsSource(), MetricsSource),
    )
    for fake, protocol in pairs:
        assert isinstance(fake, protocol), f"{type(fake).__name__} does not satisfy {protocol.__name__}"
