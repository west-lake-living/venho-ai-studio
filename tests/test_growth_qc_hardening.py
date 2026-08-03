from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from knowledge_studio.facts.fact_store import FactStore
from publishing_gateway.callback_receiver import parse_callback, verify_callback_signature
from publishing_gateway.publication_registry import PublicationRegistry
from research_engine.adapters.notebooklm_handoff import NotebookLMHandoff
from research_engine.application.collect_sources import collect_source_note
from shared.jobs.job_store import JobStore


def test_job_store_claim_is_race_free_under_concurrent_workers(tmp_path) -> None:
    """Two workers racing to claim the single READY job must never both win it.

    Regression guard for the SELECT-then-UPDATE race in JobStore.claim(): the
    old implementation could let two concurrent claim() calls both read the
    same READY row before either UPDATE landed, handing the same job to two
    workers at once.
    """
    store = JobStore(tmp_path / "growth.db")
    scheduled_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    store.enqueue(
        job_id="job-1",
        idempotency_key="key-1",
        job_type="daily_dispatch",
        version="1",
        scheduled_at=scheduled_at,
        trace_id="trace-1",
        payload={},
    )
    first = store.claim(owner="worker-a")
    second = store.claim(owner="worker-b")
    assert first is not None
    assert first["id"] == "job-1"
    assert second is None


def test_callback_signature_binds_timestamp_against_replay() -> None:
    """A signature computed over a body+timestamp must reject a forged timestamp.

    Regression guard: the previous implementation signed only `body`, so an
    attacker could replay an old valid (body, signature) pair with a
    manually bumped `timestamp` argument and pass the replay-window check.
    """
    body = b'{"publication_id": "p1"}'
    secret = "test-secret"
    original_timestamp = int(time.time())

    import hashlib
    import hmac as hmac_module

    message = f"{original_timestamp}.".encode("utf-8") + body
    signature = hmac_module.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    assert verify_callback_signature(body, signature, secret, timestamp=original_timestamp) is True
    forged_timestamp = original_timestamp + 1
    assert verify_callback_signature(body, signature, secret, timestamp=forged_timestamp) is False


def test_parse_callback_rejects_forged_timestamp_with_old_signature() -> None:
    body = b'{"publication_id": "p1", "idempotency_key": "k1", "platform": "facebook", "status": "PUBLISHED", "platform_post_id": "123", "permalink": "https://x", "published_at": "2026-08-03T00:00:00+07:00"}'
    secret = "test-secret"

    import hashlib
    import hmac as hmac_module

    original_timestamp = int(time.time())
    message = f"{original_timestamp}.".encode("utf-8") + body
    signature = hmac_module.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    parsed = parse_callback(body, signature=signature, secret=secret, timestamp=original_timestamp)
    assert parsed["publication_id"] == "p1"

    forged_timestamp = original_timestamp + 5
    with pytest.raises(ValueError, match="invalid callback signature"):
        parse_callback(body, signature=signature, secret=secret, timestamp=forged_timestamp)


def test_fact_store_rejects_path_traversal_fact_key(tmp_path) -> None:
    store = FactStore(project="venho_hotel", data_root=tmp_path)
    with pytest.raises(ValueError, match="fact_key"):
        store.save({"fact_key": "../../etc/passwd", "value": 1})
    with pytest.raises(ValueError, match="fact_key"):
        store.get("../../etc/passwd")


def test_notebooklm_handoff_rejects_path_traversal_topic_slug(tmp_path) -> None:
    handoff = NotebookLMHandoff(root=tmp_path)
    with pytest.raises(ValueError, match="topic_slug"):
        handoff.create_inbox("../../escape", "question?", [])


def test_collect_source_note_rejects_path_traversal_identifiers(tmp_path) -> None:
    with pytest.raises(ValueError):
        collect_source_note(
            rs_id="../../escape",
            domain="guest_voice",
            source_uri="https://example.com",
            title="title",
            body="body",
            vault_root=tmp_path,
        )


def test_publication_registry_reserve_is_race_free_under_concurrent_threads(tmp_path) -> None:
    """20 threads racing to reserve the same idempotency key must produce exactly one publication.

    Regression guard for PublicationRegistry.reserve()/update(): the previous
    implementation did an unlocked JSON load-modify-save, so two concurrent
    callers (e.g. a retried dispatch racing a webhook callback) could both
    read the file before either write landed, and the second writer silently
    clobbered the first — breaking the exact idempotency guarantee the
    "duplicate chaos" test (sequential, single-threaded) was meant to prove.
    """
    registry = PublicationRegistry(data_root=tmp_path)
    command = {
        "content_package_id": "pkg-race-001",
        "idempotency_key": "race-key",
        "platform": "facebook",
    }

    def _reserve(index: int) -> dict:
        return registry.reserve({**command, "publication_id": f"pub-race-{index}"})

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(_reserve, range(20)))

    stored = registry.load()["publications"]
    assert len(stored) == 1
    assert sum(1 for result in results if result.get("duplicate")) == 19
