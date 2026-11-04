from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from growth_engine.domain.media.asset import (
    MediaAsset,
    MediaVariant,
    VariantQcStatus,
)
from growth_engine.domain.media.media_policy import (
    FACEBOOK_PHOTO_V1,
    INSTAGRAM_PHOTO_V1,
    AspectRatioPolicy,
    MediaProfile,
    TransformSpec,
)
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.publishing.preflight import PreflightInput, run_preflight


# Dữ liệu test tự tạo; cần thay bằng fixture thật từ P0-T03/P0-T04.
SYNTHETIC_MARKER = {
    "_synthetic": True,
    "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
}


def valid_input() -> PreflightInput:
    return PreflightInput(
        approval_valid=True,
        channel_enabled=True,
        config_hash_matches=True,
        media_exists=True,
        media_hash_matches=True,
        media_policy_valid=True,
        media_fetch_ok=True,
        caption_hash_matches=True,
        caption_has_placeholder=False,
        facts_valid=True,
        qc_revoked=False,
        now_ms=10,
        deadline_at_ms=20,
        mode_allows=True,
        paused=False,
        epoch_matches=True,
    )


@pytest.mark.parametrize(
    ("field", "value", "code", "blocking"),
    [
        ("approval_valid", False, "PF_APPROVAL_INVALID", True),
        ("channel_enabled", False, "PF_CHANNEL_DISABLED", True),
        ("config_hash_matches", False, "PF_CONFIG_MISMATCH", True),
        ("media_exists", False, "PF_MEDIA_MISSING", True),
        ("media_hash_matches", False, "PF_MEDIA_HASH_MISMATCH", True),
        ("media_policy_valid", False, "PF_MEDIA_POLICY", True),
        ("media_fetch_ok", False, "PF_MEDIA_FETCH_FAILED", False),
        ("caption_hash_matches", False, "PF_CAPTION_HASH_MISMATCH", True),
        ("caption_has_placeholder", True, "PF_CAPTION_PLACEHOLDER", True),
        ("facts_valid", False, "PF_FACT_EXPIRED", True),
        ("qc_revoked", True, "PF_QC_REVOKED", True),
        ("now_ms", 21, "PF_WINDOW_CLOSED", True),
        ("mode_allows", False, "PF_MODE_FORBIDS", False),
        ("paused", True, "PF_PAUSED", False),
        ("epoch_matches", False, "PF_EPOCH_MISMATCH", True),
    ],
)
def test_each_pf_code_has_trigger_and_clear_case(
    field: str,
    value: object,
    code: str,
    blocking: bool,
) -> None:
    synthetic = {**SYNTHETIC_MARKER, "case": field}
    assert synthetic["_synthetic"] is True
    baseline = valid_input()
    assert all(issue.code != code for issue in run_preflight(baseline))
    before = asdict(baseline)
    issues = run_preflight(replace(baseline, **{field: value}))
    match = next(issue for issue in issues if issue.code == code)
    assert match.blocking is blocking
    assert asdict(baseline) == before


def test_all_blocking_issues_are_returned_without_short_circuiting() -> None:
    value = replace(
        valid_input(),
        approval_valid=False,
        channel_enabled=False,
        config_hash_matches=False,
        media_exists=False,
        media_hash_matches=False,
        media_policy_valid=False,
        caption_hash_matches=False,
        caption_has_placeholder=True,
        facts_valid=False,
        qc_revoked=True,
        now_ms=21,
        epoch_matches=False,
    )
    codes = {issue.code for issue in run_preflight(value)}
    assert len(codes) >= 12


def test_media_value_objects_and_profile_values_match_plan() -> None:
    assert FACEBOOK_PHOTO_V1.spec.aspect_ratio is AspectRatioPolicy.KEEP
    assert INSTAGRAM_PHOTO_V1.spec.aspect_ratio is AspectRatioPolicy.PAD_4_5
    assert FACEBOOK_PHOTO_V1.spec.max_long_side_px == 2048
    assert FACEBOOK_PHOTO_V1.spec.max_bytes == 5_242_880
    assert FACEBOOK_PHOTO_V1.spec.jpeg_quality == 88
    assert FACEBOOK_PHOTO_V1.mime == "image/jpeg"
    assert FACEBOOK_PHOTO_V1.spec.background == "#F7F4EF"
    assert FACEBOOK_PHOTO_V1.spec.transform_version_includes == (
        "profile",
        "pillow_version",
        "pillow_heif_version",
    )

    asset = MediaAsset(
        id="asset-synthetic-1",
        source_type="library",
        source_ref="synthetic-asset-ref",
        source_revision="1",
        source_sha256="a" * 64,
        original_key="originals/aa/synthetic.jpg",
        metadata_json='{"_synthetic":true}',
        created_at_ms=1_000,
    )
    variant = MediaVariant(
        id="variant-synthetic-1",
        asset_id=asset.id,
        transform_version="facebook_photo_v1|synthetic-pillow",
        sha256="b" * 64,
        object_key="variants/bb/synthetic.jpg",
        width=1536,
        height=1024,
        mime="image/jpeg",
        byte_size=100_000,
        qc_status=VariantQcStatus.PENDING,
        created_at_ms=1_001,
    )
    report = QcReport(
        id="qc-synthetic-1",
        variant_id=variant.id,
        caption_hash="c" * 64,
        ruleset_hash="d" * 64,
        fact_snapshot_hash="e" * 64,
        decision=QcDecision.REVIEW,
        coverage_gaps=("_synthetic_detector_gap",),
        result_json='{"_synthetic":true}',
        created_at_ms=1_002,
    )
    assert report.variant_id == variant.id
    assert report.decision is QcDecision.REVIEW
    with pytest.raises(ValueError):
        MediaVariant(
            id="bad",
            asset_id=asset.id,
            transform_version="x",
            sha256="b" * 64,
            object_key="variants/bad.jpg",
            width=1,
            height=1,
            mime="image/png",
            byte_size=1,
            qc_status=VariantQcStatus.PASS,
            created_at_ms=1_001,
        )


def test_media_policy_rejects_invalid_transform_values() -> None:
    with pytest.raises(ValueError):
        TransformSpec(
            max_long_side_px=0,
            max_bytes=5_242_880,
            jpeg_quality=88,
            aspect_ratio=AspectRatioPolicy.KEEP,
            background="#F7F4EF",
            transform_version_includes=("profile",),
        )
    with pytest.raises(ValueError):
        MediaProfile(name="", mime="image/jpeg", spec=FACEBOOK_PHOTO_V1.spec)
