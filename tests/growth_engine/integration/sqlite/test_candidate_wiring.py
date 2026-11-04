from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.bootstrap import build_container
from growth_engine.application.content.decide_candidate import (
    CandidateDecisionKind,
    DecideCandidateCommand,
)
from growth_engine.settings import Settings


def test_research_ingest_is_mounted_and_persisted_idempotently(tmp_path: Path) -> None:
    token = "synthetic-research-ingest-token"
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        service_tokens=f"research-ingest:{hashlib.sha256(token.encode()).hexdigest()}",
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    client = TestClient(create_app(container))
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "schema_version": "growth.research_ingest.v2",
        "project_id": "venho_hotel",
        "source": "trend_radar",
        "external_key": "synthetic-event-1",
        "source_revision": "rev-1",
        "topic_key": "synthetic-event-1",
        "event_key": "synthetic-event-1",
        "event_start_at_ms": 1_900_000_000_000,
        "event_end_at_ms": 1_900_000_100_000,
        "expires_at_ms": 1_900_000_200_000,
        "payload": {"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"},
    }

    first = client.post("/internal/growth/v2/research/ingest", headers=headers, json=body)
    replay = client.post("/internal/growth/v2/research/ingest", headers=headers, json=body)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert first.json()["candidate_id"] == replay.json()["candidate_id"]
    assert first.headers["cache-control"] == "no-store"
    with container.uow_factory().read_only() as tx:
        source_hash = tx.connection.execute(
            "SELECT source_hash FROM research_candidates WHERE id=?",
            (first.json()["candidate_id"],),
        ).fetchone()["source_hash"]
    decision = container.decide_candidate.execute(
        DecideCandidateCommand(
            candidate_id=first.json()["candidate_id"],
            source_hash=source_hash,
            decision=CandidateDecisionKind.APPROVE,
            actor="synthetic-operator",
            reason="synthetic integration decision",
        )
    )
    with container.uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE research_candidates SET expires_at=0 WHERE id=?",
            (decision.candidate.id,),
        )
    expired = container.expire_candidates.execute()
    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            "SELECT state, payload_json FROM research_candidates WHERE id=?",
            (first.json()["candidate_id"],),
        ).fetchone()
        decision_count = tx.connection.execute(
            "SELECT count(*) FROM candidate_decisions WHERE candidate_id=?",
            (first.json()["candidate_id"],),
        ).fetchone()[0]
        audit_count = tx.connection.execute(
            "SELECT count(*) FROM audit_events WHERE aggregate_id=?",
            (first.json()["candidate_id"],),
        ).fetchone()[0]
    assert row["state"] == "EXPIRED"
    assert decision_count == 1
    assert audit_count == 3
    assert expired.expired_candidate_ids == (first.json()["candidate_id"],)
    assert json.loads(row["payload_json"])["_synthetic"] is True
