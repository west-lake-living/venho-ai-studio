from __future__ import annotations

import io
import json
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image

from identity_restoration.application.canonical_transform import canonicalize_candidate_v3
from identity_restoration.application.face_observability import FaceDetection, FaceObservabilityConfig, FaceObservabilityService
from identity_restoration.application.candidate_v3_route_policy import load_candidate_v3_route_policy
from identity_restoration.application.phase4_quality import (
    QualityBundleMerger,
    ScopedQcResult,
    append_qc_history,
    apply_boundary_color_continuity,
    evaluate_boundary_qc,
    evaluate_correctness_qc,
    inverse_composite_candidate_v3,
    load_candidate_v3_quality_policy,
    manifest_1_4_enrichment,
    _nearest_pairs,
    _rings,
    scenario_global_qc,
    write_immutable_qc_report,
)
from identity_restoration.domain.policies.candidate_v3_route_policy import evaluate_candidate_v3_route


ROOT = Path(__file__).resolve().parents[3]
SHA = "a" * 64


def _png(array: np.ndarray, mode: str) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(array, mode=mode).save(buffer, format="PNG")
    return buffer.getvalue()


def _eligible_inputs():
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    image[:, :, 0] = np.arange(256, dtype=np.uint8)[:, None]
    mask = np.zeros((256, 256), dtype=np.uint8)
    mask[45:210, 45:210] = 255
    image_bytes = _png(image, "RGB")
    mask_bytes = _png(mask, "L")
    detection = FaceDetection(
        0.95, (65, 65, 190, 190), ((95, 105), (160, 105), (128, 135), (108, 165), (150, 165)), 0, 0, 0
    )
    config = FaceObservabilityConfig("detector", "1", SHA, SHA, 0.6)
    observation = FaceObservabilityService(type("Detector", (), {"detect": lambda self, image: (detection,)})(), config).observe(image_bytes, mask_bytes)
    route = evaluate_candidate_v3_route(observation, load_candidate_v3_route_policy())
    return image_bytes, mask_bytes, observation, route


def test_policy_is_approved_and_hash_pinned():
    policy = load_candidate_v3_quality_policy()
    assert policy["policyId"] == "restoration-v3-quality-policy-1"
    assert policy["version"] == "1.0"
    assert policy["seamRing"]["radiusPx"] == 3
    assert policy["boundaryMetrics"]["maxChannelSeamDelta"]["passMax"] == 32


def test_inverse_composite_uses_transform_and_preserves_outside_mask():
    image, mask, observation, route = _eligible_inputs()
    canonical = canonicalize_candidate_v3(
        observation=observation,
        route_result=route,
        image_bytes=image,
        editable_mask_bytes=mask,
        feather_mask_bytes=mask,
    )
    restored = _png(np.full((512, 512, 3), 255, dtype=np.uint8), "RGB")
    result = inverse_composite_candidate_v3(
        base_canvas_png=image,
        restored_canonical_crop_png=restored,
        canonical_editable_mask_png=canonical.canonical_editable_mask_png,
        canonical_feather_mask_png=canonical.canonical_feather_mask_png,
        full_canvas_editable_mask_png=mask,
        transform=canonical.transform,
    )
    assert result.pixel_lock.passed
    assert result.pixel_lock.mutated_pixel_count == 0
    assert evaluate_correctness_qc(
        transform=canonical.transform,
        composite=result,
        full_canvas_editable_mask_png=mask,
        lineage_valid=True,
    ).status == "PASS"


def test_boundary_passes_for_unchanged_image_and_requires_exact_pixel_lock():
    image, mask, *_ = _eligible_inputs()
    flat = _png(np.full((256, 256, 3), 32, dtype=np.uint8), "RGB")
    report = evaluate_boundary_qc(before_canvas_png=flat, final_composite_png=flat, full_canvas_editable_mask_png=mask)
    assert report.status == "PASS"
    assert report.max_channel_seam_delta == 0
    assert report.mean_seam_delta == 0
    assert report.local_texture_discontinuity == 0

    altered = np.asarray(Image.open(io.BytesIO(flat)).convert("RGB")).copy()
    altered[5, 5] = (255, 255, 255)
    altered_bytes = _png(altered, "RGB")
    failed = evaluate_boundary_qc(before_canvas_png=flat, final_composite_png=altered_bytes, full_canvas_editable_mask_png=mask)
    assert failed.status == "FAIL"
    assert "PIXEL_LOCK_OUTSIDE_MASK_FAILED" in failed.reasons


def test_boundary_continuity_only_changes_inner_ring_and_respects_policy_limit():
    before = np.zeros((32, 32, 3), dtype=np.uint8)
    before[:, 16:] = (240, 180, 120)
    composite = before.copy()
    mask = np.zeros((32, 32), dtype=np.uint8)
    mask[5:27, 5:27] = 255
    composite[5:27, 5:27] = (255, 255, 255)

    result = apply_boundary_color_continuity(
        before_canvas=before,
        composite=composite,
        editable_mask=mask,
    )
    inner, outer = _rings(mask)
    pairs = _nearest_pairs(inner, outer)
    assert np.array_equal(result[~(mask >= 128)], composite[~(mask >= 128)])
    assert np.any(result[inner] != composite[inner])
    assert all(
        np.max(np.abs(result[iy, ix].astype(np.int16) - before[oy, ox].astype(np.int16))) <= 32
        for (iy, ix), (oy, ox) in pairs
    )


def _scope(name: str, status: str) -> ScopedQcResult:
    return ScopedQcResult(name, status, "test", "", {"id": "authority", "sha256": "a" * 64}, {"path": f"{name}.json", "sha256": "b" * 64}, {}, ())


def test_quality_merger_is_fail_closed_and_deterministic():
    assert QualityBundleMerger.merge([_scope("FACE_LOCAL", "PASS"), _scope("BOUNDARY", "PASS"), _scope("SCENARIO_GLOBAL", "PASS")]).status == "PASS"
    assert QualityBundleMerger.merge([_scope("FACE_LOCAL", "FAIL"), _scope("BOUNDARY", "PASS"), _scope("SCENARIO_GLOBAL", "PASS")]).status == "FAIL"
    assert QualityBundleMerger.merge([_scope("FACE_LOCAL", "NEEDS_REVIEW"), _scope("BOUNDARY", "PASS"), _scope("SCENARIO_GLOBAL", "UNVALIDATED")]).status == "UNVALIDATED"
    assert QualityBundleMerger.merge([_scope("FACE_LOCAL", "PASS")]).status == "UNVALIDATED"
    assert scenario_global_qc(binding_ref=None, passed=True).status == "UNVALIDATED"


def test_immutable_reports_and_manifest_14_schema(tmp_path: Path):
    report = {"scope": "BOUNDARY", "status": "PASS"}
    path = tmp_path / "qc" / "boundary.json"
    digest = write_immutable_qc_report(path, report)
    assert write_immutable_qc_report(path, report) == digest
    append_qc_history(tmp_path / "qc" / "history.jsonl", {"sha256": digest})
    assert len((tmp_path / "qc" / "history.jsonl").read_text().splitlines()) == 1

    refs = {scope: {"path": f"{scope}.json", "sha256": "b" * 64} for scope in ("FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL")}
    merged = QualityBundleMerger.merge([_scope("FACE_LOCAL", "PASS"), _scope("BOUNDARY", "PASS"), _scope("SCENARIO_GLOBAL", "PASS")])
    enrichment = manifest_1_4_enrichment(report_refs=refs, quality_policy_sha256=load_candidate_v3_quality_policy()["policySha256"], merged=merged)
    schema = json.loads((ROOT / "contracts/identity_restoration/restoration_manifest_1_4.schema.json").read_text())
    jsonschema.validate(enrichment, schema)
