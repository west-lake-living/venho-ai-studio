from __future__ import annotations

import time

import pytest

from identity_restoration.application.ports.ledger import LedgerEntry
from identity_restoration.domain.errors import RestorationError
from identity_restoration.infrastructure.persistence.file_concurrency_lease import FileConcurrencyLease
from identity_restoration.infrastructure.persistence.jsonl_restoration_ledger import JsonlRestorationLedger

# GW-P5-T5 — "job gián đoạn retry an toàn (attempt_id mới, không ghi đè)".
# These exercise the real FileConcurrencyLease/JsonlRestorationLedger
# implementations (not the FakeLease used by the use-case-level exception
# test), because the failure mode that matters here is a process that dies
# without running any `finally` — not a clean exception. 0 network/GPU calls.


def test_crashed_holder_lock_is_reclaimed_after_ttl(tmp_path):
    """A worker that dies mid-job (no `finally` ever runs, e.g. kill -9 or a
    Windows reboot) leaves an orphaned lock file. A short ttl_seconds must let
    a *new* attempt reclaim it instead of permanently deadlocking retries."""
    lock_path = tmp_path / "gpu_worker.lock"
    lease = FileConcurrencyLease(lock_path=lock_path)

    # Simulate the crashed holder: lock file written, but timestamp is
    # already older than the ttl this new attempt will use.
    lock_path.write_text(f"99999:gpu_worker:{time.time() - 120}", encoding="utf-8")

    with lease.acquire(key="gpu_worker", ttl_seconds=60) as held:
        assert held.key == "gpu_worker"
    assert not lock_path.exists()  # released cleanly on the way out


def test_live_holder_lock_fails_fast_not_hang(tmp_path):
    """A genuinely in-flight job (lock younger than ttl) must reject a
    concurrent attempt immediately and retryably — never block/hang waiting
    for the GPU (v2.0 §6: max_concurrent=1, 6 GB VRAM cannot take two)."""
    lock_path = tmp_path / "gpu_worker.lock"
    lease = FileConcurrencyLease(lock_path=lock_path)
    lock_path.write_text(f"12345:gpu_worker:{time.time()}", encoding="utf-8")

    with pytest.raises(RestorationError) as exc_info:
        with lease.acquire(key="gpu_worker", ttl_seconds=600):
            pass  # pragma: no cover - must not be entered

    assert exc_info.value.code == "ERR_GW_LEASE_UNAVAILABLE"
    assert exc_info.value.retryable is True
    assert lock_path.exists()  # the live holder's lock is untouched


def test_retry_after_interruption_writes_new_attempt_without_overwrite(tmp_path):
    """After an interrupted attempt, retrying with a new attempt_id must add
    a ledger row, not overwrite the failed one — a lost failed attempt makes
    a benchmark lie (ledger.py docstring, v1.0 §9 rule 3)."""
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = JsonlRestorationLedger(path=ledger_path)

    ledger.append(LedgerEntry(run_id="run-1", attempt_id="attempt-1", status="FAILED",
                               payload={"code": "ERR_GW_WORKER_TIMEOUT"}))
    ledger.append(LedgerEntry(run_id="run-1", attempt_id="attempt-2", status="SUCCESS",
                               payload={"faceQc": 92.1}))

    rows = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 2
    import json
    parsed = [json.loads(row) for row in rows]
    assert parsed[0]["attemptId"] == "attempt-1" and parsed[0]["status"] == "FAILED"
    assert parsed[1]["attemptId"] == "attempt-2" and parsed[1]["status"] == "SUCCESS"
    assert parsed[0]["runId"] == parsed[1]["runId"] == "run-1"
