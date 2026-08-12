import json

from image_studio_runtime.action_composite.analytics import build_analytics
from image_studio_runtime.action_composite.audit_store import AuditStore
from image_studio_runtime.action_composite.orchestration import AuditTrail, CostLedger, IterationRecord
from image_studio_runtime.action_composite.workflow_registry import WorkflowRegistry


def test_workflow_registry_hash_and_metadata(tmp_path):
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "face_restore_v1_api.json").write_text(json.dumps({"1": {"class_type": "LoadImage"}}))
    registry = WorkflowRegistry(workflow_dir)
    descriptor = registry.descriptor("face_restore_v1")
    assert len(descriptor["sha256"]) == 64
    registry.validate_metadata({"workflow_version": "face_restore_v1", "workflow_sha256": descriptor["sha256"]}, version="face_restore_v1")


def test_audit_store_round_trip_and_analytics(tmp_path):
    trail = AuditTrail(job_id="job-p4")
    trail.append(IterationRecord(iteration=0, provider="comfyui", workflow_version="v1", state="FINALIZE"))
    store = AuditStore(tmp_path / "audit")
    store.save(trail)
    loaded = store.load("job-p4")
    ledger = CostLedger()
    ledger.record(provider="comfyui", duration_seconds=3.0, cost=0.0, job_id="job-p4")
    report = build_analytics([loaded], ledger)
    assert report["approved_jobs"] == 1
    assert report["approval_rate"] == 1.0
    assert report["cost"]["total_duration_seconds"] == 3.0
