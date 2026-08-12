import pytest

from image_studio_runtime.action_composite.audit_store import AuditStore
from image_studio_runtime.action_composite.models import ActionCompositeJob
from image_studio_runtime.action_composite.service import ActionCompositeService, JobStatus


def make_job(tmp_path):
    base = tmp_path / "base.png"
    ref = tmp_path / "A2-front.png"
    base.write_bytes(b"base")
    ref.write_bytes(b"reference")
    return ActionCompositeJob(job_id="job-p5", base_image=str(base), identity_reference=str(ref))


def test_service_idempotency_and_resume(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    first = service.submit(job, request_payload=b"same")
    assert service.submit(job, request_payload=b"same") is first
    result = service.run(job.job_id, lambda _: {"path": "image.png"})
    assert result.status == JobStatus.COMPLETED
    assert service.run(job.job_id, lambda _: {"path": "other.png"}).result == {"path": "image.png"}


def test_service_failure_and_resume(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    service.submit(job)
    failed = service.run(job.job_id, lambda _: (_ for _ in ()).throw(RuntimeError("provider down")))
    assert failed.status == JobStatus.FAILED
    resumed = service.resume(job.job_id, lambda _: {"path": "image.png"})
    assert resumed.status == JobStatus.COMPLETED
    assert resumed.audit_path


def test_resume_keeps_the_failed_attempt_in_the_audit_trail(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    service.submit(job)
    service.run(job.job_id, lambda _: (_ for _ in ()).throw(RuntimeError("provider down")))
    service.resume(job.job_id, lambda _: {"path": "image.png"})

    trail = AuditStore(tmp_path / "audit").load(job.job_id)
    states = [event.state for event in trail.events]
    assert states == ["RUNNING", "FAILED", "RUNNING", "FINALIZE"]
    assert [event.iteration for event in trail.events] == [0, 1, 2, 3]


def test_conflicting_payload_for_the_same_job_id_is_rejected(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    service.submit(job, request_payload=b"first")

    with pytest.raises(ValueError, match="different request payload"):
        service.submit(job, request_payload=b"second")


def test_running_job_cannot_be_started_twice(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    service.submit(job)

    def reenter(_):
        with pytest.raises(RuntimeError, match="already running"):
            service.run(job.job_id, lambda _: {"path": "duplicate.png"})
        return {"path": "image.png"}

    assert service.run(job.job_id, reenter).status == JobStatus.COMPLETED


def test_replayed_request_is_not_executed_again(tmp_path):
    service = ActionCompositeService(tmp_path / "audit")
    job = make_job(tmp_path)
    service.submit(job, request_payload=b"same")
    service.run(job.job_id, lambda _: {"path": "image.png"})

    # A fresh envelope for an already-completed request (worker restart, retried
    # HTTP call) must replay the stored result rather than regenerate.
    service.jobs.clear()
    replayed = service.submit(job, request_payload=b"same")
    assert replayed.status == JobStatus.COMPLETED
    assert replayed.result == {"path": "image.png"}
