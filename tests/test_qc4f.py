import json
from pathlib import Path

from PIL import Image

from image_studio_runtime.action_composite.regional_score_gateway import StagePreservationEvidenceAdapter


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4f/qc4f-report.json"


def test_qc4f_existing_candidate_has_deterministic_preservation_pass():
    report = json.loads(REPORT.read_text())
    assert report["adapter"]["stage"] == "post_identity_restoration"
    assert report["adapter"]["thresholds_changed"] is False
    assert report["regional"]["regional_gate_failures"] == ["global_composite_unvalidated"]
    for item in report["regions"]:
        assert item["region"] in {"anatomy", "outfit", "environment"}
        assert item["protected_pixel_count"] == 1301277
        assert item["changed_protected_pixel_count"] == 0
        assert item["preservation_score"] == 100.0
        assert item["status"] == "PASS"


def test_qc4f_mutation_cannot_pass_preservation_adapter(tmp_path):
    source = tmp_path / "source.png"
    candidate = tmp_path / "candidate.png"
    mask = tmp_path / "mask.png"
    Image.new("RGBA", (4, 4), (10, 10, 10, 255)).save(source)
    changed = Image.new("RGBA", (4, 4), (10, 10, 10, 255))
    changed.putpixel((3, 3), (11, 10, 10, 255))
    changed.save(candidate)
    Image.new("L", (4, 4), 0).save(mask)
    evidence = StagePreservationEvidenceAdapter().produce(
        source_artifact=source, candidate_artifact=candidate, mask_artifact=mask,
        crop_box={"left": 0, "top": 0, "right": 4, "bottom": 4},
    )
    assert all(item.changed_protected_pixel_count == 1 for item in evidence)
    assert all(item.status == "FAIL" for item in evidence)
    assert all(item.preservation_score < 100 for item in evidence)


def test_qc4f_preservation_is_region_and_stage_isolated():
    report = json.loads(REPORT.read_text())
    assert {item["region"] for item in report["regions"]} == {"anatomy", "outfit", "environment"}
    assert "global_composite" not in {item["region"] for item in report["regions"]}
    assert all(item["stage"] == "post_identity_restoration" for item in report["regions"])
    assert report["regression"]["no_scene_candidate_scores"] is True
