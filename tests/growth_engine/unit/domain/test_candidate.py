from __future__ import annotations

from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate
from growth_engine.domain.content.package import ContentPackage


def make_candidate(
    *,
    state: CandidateState = CandidateState.APPROVED,
    expires_at_ms: int = 100,
    event_end_at_ms: int | None = 200,
) -> ResearchCandidate:
    return ResearchCandidate(
        id="candidate-synthetic-1",
        project_id="venho_hotel",
        source="trend_radar",
        external_key="event-synthetic-1",
        source_revision="1",
        event_key="event-synthetic-1",
        topic_key="synthetic-topic",
        event_start_at_ms=50,
        event_end_at_ms=event_end_at_ms,
        expires_at_ms=expires_at_ms,
        source_hash="a" * 64,
        state=state,
    )


def test_candidate_usable_before_expiry_and_event_end_only_when_approved() -> None:
    candidate = make_candidate()
    assert candidate.is_usable(99)
    assert not candidate.is_usable(100)
    assert not candidate.is_usable(200)
    assert not make_candidate(state=CandidateState.NEW).is_usable(99)
    assert make_candidate(event_end_at_ms=None).is_usable(99)


def test_content_package_keeps_immutable_snapshots_and_hash() -> None:
    package = ContentPackage(
        id="package-synthetic-1",
        slot_id="slot-synthetic-1",
        topic_key="synthetic-topic",
        pillar="local_discovery",
        lane="regular",
        source_snapshot_json='{"_synthetic":true}',
        fact_snapshot_json='{"_synthetic":true}',
        fact_snapshot_hash="b" * 64,
        generation_version="test-generator",
        created_at_ms=1_000,
        candidate_id=None,
    )
    assert package.fact_snapshot_hash == "b" * 64
