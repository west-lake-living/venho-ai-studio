from pathlib import Path

from PIL import Image

from image_studio_runtime.action_composite.models import ActionCompositeJob
from image_studio_runtime.action_composite.production import ProductionRunner
from image_studio_runtime.action_composite.service import ActionCompositeService, JobStatus


class HealthyRestorer:
    def health_check(self):
        return True

    def restore(self, base, reference, mask, geometry, options):
        return base.copy()


def test_production_runner_verifies_artifacts(tmp_path: Path):
    base = tmp_path / "base.png"
    ref = tmp_path / "A2-front.png"
    Image.new("RGB", (128, 128), "white").save(base)
    ref.write_bytes(b"reference")
    job = ActionCompositeJob(job_id="job-p6", base_image=str(base), identity_reference=str(ref), face_bbox={"left": 32, "top": 32, "right": 96, "bottom": 96})
    service = ActionCompositeService(tmp_path / "audit")
    runner = ProductionRunner(service=service)
    envelope = runner.submit_and_run(job, HealthyRestorer(), output_dir=tmp_path / "run", identity_score=91, geometry_score=93)
    assert envelope.status == JobStatus.COMPLETED
    assert (tmp_path / "run" / "manifest.json").is_file()


def test_production_artifact_gate_rejects_missing_manifest(tmp_path: Path):
    image = tmp_path / "image.png"
    image.write_bytes(b"not-empty")
    try:
        ProductionRunner._verify_artifacts(str(image))
    except RuntimeError as exc:
        assert "manifest" in str(exc)
    else:
        raise AssertionError("artifact gate must reject missing manifest")
