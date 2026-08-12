from image_studio_runtime.action_composite.orchestration import (
    AuditTrail, CostLedger, IdempotencyStore, IterationRecord, RetryPolicy, StopCondition,
)
from image_studio_runtime.action_composite.validators import RegionalValidator


def test_audit_trail_and_idempotency_are_reproducible():
    trail = AuditTrail(job_id="job-1")
    trail.append(IterationRecord(iteration=0, provider="comfyui", workflow_version="v1"))
    trail.append(IterationRecord(iteration=1, provider="comfyui", workflow_version="v1", identity_score=91))
    assert trail.latest.identity_score == 91
    store = IdempotencyStore()
    key = store.key("job-1", b"payload")
    assert store.get(key) is None
    store.put(key, {"output": "image.png"})
    assert store.get(key) == {"output": "image.png"}


def test_retry_policy_and_stop_condition():
    policy = RetryPolicy(caps={"face": 2, "region": 1, "boundary": 1, "scene": 1})
    assert policy.allow("face") and policy.allow("face")
    assert not policy.allow("face")
    gate = StopCondition()
    passing = {name: 95 for name in gate.REQUIRED}
    assert gate.evaluate(passing)
    passing["outfit"] = 40
    assert not gate.evaluate(passing)


def test_stop_condition_honours_a_custom_validator_threshold():
    """A caller that lowers the identity bar must not be overruled by a second,
    hard-coded copy of the same threshold inside the gate."""
    gate = StopCondition()
    scores = {name: 95 for name in gate.REQUIRED}
    scores["identity"] = 86

    assert not gate.evaluate(scores)
    assert gate.evaluate(scores, validator=RegionalValidator(identity_threshold=85.0))


def test_retry_policy_tolerates_caps_without_a_region_default():
    policy = RetryPolicy(caps={"face": 1})
    assert policy.allow("face")
    assert not policy.allow("face")
    assert policy.allow("outfit")  # falls back to the documented region cap


def test_cost_ledger_snapshot():
    ledger = CostLedger()
    ledger.record(provider="comfyui", duration_seconds=2.5, cost=0, job_id="job-1")
    ledger.record(provider="nano_banana", duration_seconds=1, cost=0.04, job_id="job-1")
    assert ledger.total_duration_seconds == 3.5
    assert ledger.total_cost == 0.04
    assert len(ledger.snapshot()["entries"]) == 2
