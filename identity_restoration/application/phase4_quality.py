"""Candidate v3 Phase 4 composite, boundary QC, and immutable evidence.

This module is deliberately CPU-only.  It consumes the already verified
``CanonicalFaceTransform`` and never changes legacy v2/v2.1 compositing.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image

from .canonical_transform import (
    CanonicalTransformError,
    inverse_warp_canonical_artifacts,
    load_candidate_v3_canonical_transform_policy,
    validate_canonical_transform,
)
from .dto.candidate_v3 import CanonicalFaceTransform
from ..domain.policies.pixel_preservation import PixelLockReport, assert_pixels_preserved


POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "candidate_v3_quality_policy_v1.json"
POLICY_ID = "restoration-v3-quality-policy-1"
POLICY_VERSION = "1.0"
SEAM_RADIUS_PX = 3
FACE_LOCAL_MINIMUM = 90.0
STATUSES = ("PASS", "FAIL", "UNVALIDATED", "NEEDS_REVIEW")


class Phase4QualityError(ValueError):
    """Raised when Phase 4 evidence cannot be trusted."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_candidate_v3_quality_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase4QualityError("QUALITY_POLICY_UNAVAILABLE") from exc
    if not isinstance(payload, dict) or payload.get("policyId") != POLICY_ID or payload.get("version") != POLICY_VERSION:
        raise Phase4QualityError("QUALITY_POLICY_VERSION_UNSUPPORTED")
    supplied = payload.get("policySha256")
    without_hash = {key: value for key, value in payload.items() if key != "policySha256"}
    if not isinstance(supplied, str) or len(supplied) != 64 or _sha256(_canonical_json(without_hash)) != supplied:
        raise Phase4QualityError("QUALITY_POLICY_SHA256_MISMATCH")
    if payload.get("seamRing", {}).get("radiusPx") != SEAM_RADIUS_PX:
        raise Phase4QualityError("SEAM_RING_POLICY_UNSUPPORTED")
    if payload.get("seamRing", {}).get("connectivity") != 8:
        raise Phase4QualityError("SEAM_RING_CONNECTIVITY_UNSUPPORTED")
    return payload


def _decode_png(data: bytes, mode: str) -> Image.Image:
    try:
        return Image.open(BytesIO(data)).convert(mode)
    except Exception as exc:  # PIL exposes several exception classes by version.
        raise Phase4QualityError("MALFORMED_ARTIFACT") from exc


def _encode_png(array: np.ndarray, mode: str) -> bytes:
    buffer = BytesIO()
    Image.fromarray(array.astype(np.uint8), mode=mode).save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass(frozen=True)
class CandidateV3CompositeResult:
    inverse_warped_crop_png: bytes
    inverse_editable_mask_png: bytes
    inverse_feather_mask_png: bytes
    approved_editable_mask_png: bytes
    final_composite_png: bytes
    pixel_lock: PixelLockReport

    def as_dict(self) -> dict[str, Any]:
        return {
            "inverseWarpedCropSha256": _sha256(self.inverse_warped_crop_png),
            "inverseEditableMaskSha256": _sha256(self.inverse_editable_mask_png),
            "inverseFeatherMaskSha256": _sha256(self.inverse_feather_mask_png),
            "approvedEditableMaskSha256": _sha256(self.approved_editable_mask_png),
            "finalCompositeSha256": _sha256(self.final_composite_png),
            "pixelLock": {
                "passed": self.pixel_lock.passed,
                "mutatedPixelCount": self.pixel_lock.mutated_pixel_count,
                "editableRegionHash": self.pixel_lock.editable_region_hash,
            },
        }


def inverse_composite_candidate_v3(
    *,
    base_canvas_png: bytes,
    restored_canonical_crop_png: bytes,
    canonical_editable_mask_png: bytes,
    canonical_feather_mask_png: bytes,
    full_canvas_editable_mask_png: bytes,
    transform: CanonicalFaceTransform,
) -> CandidateV3CompositeResult:
    """Inverse-warp and composite using only the verified canonical transform.

    The inverse-warped editable mask is intersected with the full-canvas mask.
    Feathering is applied only to that approved intersection, so pixels outside
    the full-canvas editable mask remain byte-identical.
    """
    try:
        inverse_image, inverse_mask, inverse_feather = inverse_warp_canonical_artifacts(
            transform=transform,
            canonical_image_png=restored_canonical_crop_png,
            canonical_editable_mask_png=canonical_editable_mask_png,
            canonical_feather_mask_png=canonical_feather_mask_png,
        )
    except CanonicalTransformError:
        raise
    base = _decode_png(base_canvas_png, "RGB")
    restored = _decode_png(inverse_image, "RGB")
    full_mask = _decode_png(full_canvas_editable_mask_png, "L")
    restored_mask = _decode_png(inverse_mask, "L")
    feather = _decode_png(inverse_feather, "L")
    if base.size != restored.size or base.size != full_mask.size or base.size != restored_mask.size or base.size != feather.size:
        raise Phase4QualityError("COMPOSITE_DIMENSIONS_INVALID")

    full = np.asarray(full_mask, dtype=np.uint8)
    approved = (full >= 128) & (np.asarray(restored_mask, dtype=np.uint8) >= 128)
    approved_mask_png = _encode_png(np.where(approved, 255, 0).astype(np.uint8), "L")
    alpha = np.where(approved, np.asarray(feather, dtype=np.float32) / 255.0, 0.0)
    before = np.asarray(base, dtype=np.float32)
    patch = np.asarray(restored, dtype=np.float32)
    output = np.rint(before * (1.0 - alpha[..., None]) + patch * alpha[..., None]).clip(0, 255).astype(np.uint8)
    final_png = _encode_png(output, "RGB")
    pixel_lock = assert_pixels_preserved(
        before_canvas=base_canvas_png,
        after_canvas=final_png,
        editable_mask=full_canvas_editable_mask_png,
    )
    return CandidateV3CompositeResult(
        inverse_warped_crop_png=inverse_image,
        inverse_editable_mask_png=inverse_mask,
        inverse_feather_mask_png=inverse_feather,
        approved_editable_mask_png=approved_mask_png,
        final_composite_png=final_png,
        pixel_lock=pixel_lock,
    )


def _rings(editable_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    inside = editable_mask >= 128
    kernel = np.ones((3, 3), dtype=np.uint8)
    eroded = cv2.erode(inside.astype(np.uint8), kernel, iterations=1).astype(bool)
    dilated = cv2.dilate(inside.astype(np.uint8), kernel, iterations=1).astype(bool)
    inner_boundary = inside & ~eroded
    outer_boundary = ~inside & dilated
    offsets = np.arange(-SEAM_RADIUS_PX, SEAM_RADIUS_PX + 1)
    ring_kernel = (
        offsets[:, None] ** 2 + offsets[None, :] ** 2 <= SEAM_RADIUS_PX**2
    ).astype(np.uint8)
    inner_ring = inside & cv2.dilate(inner_boundary.astype(np.uint8), ring_kernel, iterations=1).astype(bool)
    outer_ring = (~inside) & cv2.dilate(outer_boundary.astype(np.uint8), ring_kernel, iterations=1).astype(bool)
    return inner_ring, outer_ring


def _nearest_pairs(inner: np.ndarray, outer: np.ndarray) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    inner_points = np.argwhere(inner)
    outer_points = np.argwhere(outer)
    if len(inner_points) == 0 or len(outer_points) == 0:
        return []
    pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for y, x in inner_points:
        distances = (outer_points[:, 0] - y) ** 2 + (outer_points[:, 1] - x) ** 2
        nearest_distance = distances.min()
        candidates = outer_points[distances == nearest_distance]
        # argwhere is row-major, making equal-distance ties deterministic.
        oy, ox = candidates[0]
        pairs.append(((int(y), int(x)), (int(oy), int(ox))))
    return pairs


@dataclass(frozen=True)
class BoundaryQcResult:
    status: str
    pixel_lock_passed: bool
    max_channel_seam_delta: float | None
    mean_seam_delta: float | None
    local_texture_discontinuity: float | None
    metric_statuses: Mapping[str, str]
    reasons: tuple[str, ...]
    policy_id: str = POLICY_ID
    policy_version: str = POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "validatorId": "candidate-v3-boundary-qc",
            "policyId": self.policy_id,
            "policyVersion": self.policy_version,
            "pixelLockPassed": self.pixel_lock_passed,
            "maxChannelSeamDelta": self.max_channel_seam_delta,
            "meanSeamDelta": self.mean_seam_delta,
            "localTextureDiscontinuity": self.local_texture_discontinuity,
            "metricStatuses": dict(self.metric_statuses),
            "reasons": list(self.reasons),
        }


def _metric_status(value: float | None, pass_max: float, review_max: float) -> str:
    if value is None or not np.isfinite(value):
        return "UNVALIDATED"
    if value <= pass_max:
        return "PASS"
    if value <= review_max:
        return "NEEDS_REVIEW"
    return "FAIL"


def evaluate_boundary_qc(*, before_canvas_png: bytes, final_composite_png: bytes, full_canvas_editable_mask_png: bytes) -> BoundaryQcResult:
    """Evaluate the approved 3 px boundary policy without external services."""
    policy = load_candidate_v3_quality_policy()
    before = np.asarray(_decode_png(before_canvas_png, "RGB"), dtype=np.uint8)
    after = np.asarray(_decode_png(final_composite_png, "RGB"), dtype=np.uint8)
    mask = np.asarray(_decode_png(full_canvas_editable_mask_png, "L"), dtype=np.uint8)
    if before.shape != after.shape or before.shape[:2] != mask.shape:
        raise Phase4QualityError("BOUNDARY_DIMENSIONS_INVALID")
    pixel_lock = assert_pixels_preserved(
        before_canvas=before_canvas_png,
        after_canvas=final_composite_png,
        editable_mask=full_canvas_editable_mask_png,
    )
    inner, outer = _rings(mask)
    pairs = _nearest_pairs(inner, outer)
    if not pairs:
        return BoundaryQcResult(
            status="UNVALIDATED",
            pixel_lock_passed=pixel_lock.passed,
            max_channel_seam_delta=None,
            mean_seam_delta=None,
            local_texture_discontinuity=None,
            metric_statuses={"seam": "UNVALIDATED", "texture": "UNVALIDATED"},
            reasons=("NO_VALID_SEAM_SAMPLE_PAIRS",),
        )
    deltas: list[float] = []
    channel_max: list[float] = []
    for (iy, ix), (oy, ox) in pairs:
        difference = np.abs(after[iy, ix].astype(np.int16) - after[oy, ox].astype(np.int16))
        channel_max.append(float(difference.max()))
        deltas.extend(float(value) for value in difference)
    gray = cv2.cvtColor(after, cv2.COLOR_RGB2GRAY)
    gradient = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    mean_inner = float(np.mean(gradient[inner])) if np.any(inner) else float("nan")
    mean_outer = float(np.mean(gradient[outer])) if np.any(outer) else float("nan")
    texture = abs(mean_inner - mean_outer) / max(mean_outer, 1.0) if np.isfinite(mean_inner) and np.isfinite(mean_outer) else None
    max_delta = max(channel_max)
    mean_delta = float(np.mean(deltas))
    statuses = {
        "maxChannelSeamDelta": _metric_status(max_delta, 32, 48),
        "meanSeamDelta": _metric_status(mean_delta, 12, 20),
        "localTextureDiscontinuity": _metric_status(texture, 0.25, 0.40),
    }
    reasons: list[str] = []
    if not pixel_lock.passed:
        reasons.append("PIXEL_LOCK_OUTSIDE_MASK_FAILED")
    if any(value == "FAIL" for value in statuses.values()):
        reasons.append("BOUNDARY_METRIC_FAILED")
    elif any(value == "UNVALIDATED" for value in statuses.values()):
        reasons.append("BOUNDARY_METRIC_UNVALIDATED")
    elif any(value == "NEEDS_REVIEW" for value in statuses.values()):
        reasons.append("BOUNDARY_METRIC_NEEDS_REVIEW")
    if not pixel_lock.passed or "FAIL" in statuses.values():
        status = "FAIL"
    elif "UNVALIDATED" in statuses.values():
        status = "UNVALIDATED"
    elif "NEEDS_REVIEW" in statuses.values():
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"
    return BoundaryQcResult(status, pixel_lock.passed, max_delta, mean_delta, texture, statuses, tuple(reasons))


@dataclass(frozen=True)
class ScopedQcResult:
    scope: str
    status: str
    validator_id: str
    validator_config_sha256: str
    authority_ref: Mapping[str, str] | None
    report_ref: Mapping[str, Any] | None
    scores: Mapping[str, float]
    binary_gates: tuple[Mapping[str, Any], ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.scope not in ("FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL") or self.status not in STATUSES:
            raise Phase4QualityError("SCOPED_QC_STATUS_INVALID")

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "status": self.status,
            "validatorId": self.validator_id,
            "validatorConfigSha256": self.validator_config_sha256,
            "authorityRef": dict(self.authority_ref or {}),
            "report": dict(self.report_ref or {}),
            "scores": dict(self.scores),
            "binaryGates": [dict(gate) for gate in self.binary_gates],
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class MergedQcResult:
    status: str
    failed_scopes: tuple[str, ...]
    decisive_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "failedScopes": list(self.failed_scopes),
            "decisiveReasons": list(self.decisive_reasons),
        }


@dataclass(frozen=True)
class CorrectnessQcResult:
    status: str
    transform_valid: bool
    geometry_valid: bool
    mask_containment_valid: bool
    pixel_lock_passed: bool
    lineage_valid: bool | None
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "transformValid": self.transform_valid,
            "geometryValid": self.geometry_valid,
            "maskContainmentValid": self.mask_containment_valid,
            "pixelLockPassed": self.pixel_lock_passed,
            "lineageValid": self.lineage_valid,
            "reasons": list(self.reasons),
        }


def evaluate_correctness_qc(
    *,
    transform: CanonicalFaceTransform,
    composite: CandidateV3CompositeResult,
    full_canvas_editable_mask_png: bytes,
    lineage_valid: bool | None,
) -> CorrectnessQcResult:
    """Apply the Phase 4 correctness gate before quality-scope merging."""
    transform_valid = True
    reasons: list[str] = []
    try:
        validate_canonical_transform(transform, policy=load_candidate_v3_canonical_transform_policy())
    except CanonicalTransformError:
        transform_valid = False
        reasons.append("CANONICAL_TRANSFORM_INVALID")
    full_mask = np.asarray(_decode_png(full_canvas_editable_mask_png, "L"), dtype=np.uint8)
    inverse_mask = np.asarray(_decode_png(composite.approved_editable_mask_png, "L"), dtype=np.uint8)
    geometry_valid = full_mask.shape == inverse_mask.shape
    if not geometry_valid:
        reasons.append("MASK_GEOMETRY_INVALID")
    mask_containment_valid = bool(geometry_valid and not np.any((inverse_mask >= 128) & (full_mask < 128)))
    if not mask_containment_valid:
        reasons.append("EDITABLE_MASK_CONTAINMENT_FAILED")
    if not composite.pixel_lock.passed:
        reasons.append("PIXEL_LOCK_OUTSIDE_MASK_FAILED")
    if lineage_valid is False:
        reasons.append("AUTHORITY_LINEAGE_INVALID")
    elif lineage_valid is None:
        reasons.append("AUTHORITY_LINEAGE_MISSING")
    if not transform_valid or not geometry_valid or not mask_containment_valid or not composite.pixel_lock.passed or lineage_valid is False:
        status = "FAIL"
    elif lineage_valid is None:
        status = "UNVALIDATED"
    else:
        status = "PASS"
    return CorrectnessQcResult(status, transform_valid, geometry_valid, mask_containment_valid, composite.pixel_lock.passed, lineage_valid, tuple(reasons))


class QualityBundleMerger:
    """Fail-closed implementation of the roadmap's exact merge precedence."""

    @staticmethod
    def merge(scopes: Sequence[ScopedQcResult]) -> MergedQcResult:
        required = ("FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL")
        if len({scope.scope for scope in scopes}) != len(scopes):
            return MergedQcResult("UNVALIDATED", (), ("DUPLICATE_QC_SCOPE",))
        unknown = tuple(scope.scope for scope in scopes if scope.scope not in required)
        if unknown:
            return MergedQcResult("UNVALIDATED", (), tuple(f"UNKNOWN_QC_SCOPE:{scope}" for scope in unknown))
        by_scope = {scope.scope: scope for scope in scopes}
        missing = [scope for scope in required if scope not in by_scope]
        if missing:
            return MergedQcResult("UNVALIDATED", (), tuple(f"MISSING_SCOPE:{scope}" for scope in missing))
        failed = tuple(scope for scope in required if by_scope[scope].status == "FAIL")
        if failed:
            return MergedQcResult("FAIL", failed, tuple(f"SCOPE_FAIL:{scope}" for scope in failed))
        unvalidated = tuple(
            scope for scope in required
            if by_scope[scope].status == "UNVALIDATED"
            or (by_scope[scope].status == "PASS" and (not by_scope[scope].authority_ref or not by_scope[scope].report_ref))
        )
        if unvalidated:
            return MergedQcResult("UNVALIDATED", (), tuple(f"SCOPE_UNVALIDATED:{scope}" for scope in unvalidated))
        review = tuple(scope for scope in required if by_scope[scope].status == "NEEDS_REVIEW")
        if review:
            return MergedQcResult("NEEDS_REVIEW", (), tuple(f"SCOPE_NEEDS_REVIEW:{scope}" for scope in review))
        return MergedQcResult("PASS", (), ())


def face_local_qc(*, score: float | None, evidence_valid: bool, authority_ref: Mapping[str, str] | None = None) -> ScopedQcResult:
    policy = load_candidate_v3_quality_policy()
    if not evidence_valid or score is None or not np.isfinite(score):
        status, reasons = "UNVALIDATED", ("MISSING_FACE_LOCAL_EVIDENCE",)
    elif score < FACE_LOCAL_MINIMUM:
        status, reasons = "FAIL", ("FACE_QC_BELOW_90",)
    else:
        status, reasons = "PASS", ()
    return ScopedQcResult("FACE_LOCAL", status, "validator-studio-face-qc", policy["policySha256"], authority_ref, None, {"faceScore": float(score)} if score is not None else {}, (), reasons)


def face_local_qc_candidate_v3(
    *,
    canonical_crop_png: bytes | None,
    selected_reference_ids: Sequence[str],
    score: float | None,
    authority_ref: Mapping[str, str] | None,
    report_ref: Mapping[str, Any] | None = None,
) -> ScopedQcResult:
    """Require the canonical 512 px crop and selected approved pack refs."""
    valid_input = bool(canonical_crop_png and selected_reference_ids and authority_ref and report_ref)
    if valid_input:
        try:
            valid_input = _decode_png(canonical_crop_png or b"", "RGB").size == (512, 512)
        except Phase4QualityError:
            valid_input = False
    result = face_local_qc(score=score, evidence_valid=valid_input, authority_ref=authority_ref)
    return ScopedQcResult(
        result.scope,
        result.status,
        result.validator_id,
        result.validator_config_sha256,
        result.authority_ref,
        report_ref,
        {**result.scores, "selectedReferenceCount": float(len(selected_reference_ids))},
        result.binary_gates,
        result.reasons,
    )


def scenario_global_qc(*, binding_ref: Mapping[str, str] | None, passed: bool | None) -> ScopedQcResult:
    policy = load_candidate_v3_quality_policy()
    if not binding_ref or passed is None:
        return ScopedQcResult("SCENARIO_GLOBAL", "UNVALIDATED", "candidate-v3-scenario-global-qc", policy["policySha256"], binding_ref, None, {}, (), ("MISSING_APPROVED_SCENARIO_BINDING",))
    status = "PASS" if passed else "FAIL"
    return ScopedQcResult("SCENARIO_GLOBAL", status, "candidate-v3-scenario-global-qc", policy["policySha256"], binding_ref, None, {}, (), () if passed else ("SCENARIO_GLOBAL_GATE_FAILED",))


def split_qc_decision(*, correctness_status: str, scopes: Sequence[ScopedQcResult]) -> MergedQcResult:
    if correctness_status not in STATUSES:
        raise Phase4QualityError("CORRECTNESS_STATUS_UNKNOWN")
    if correctness_status == "FAIL":
        return MergedQcResult("FAIL", (), ("CORRECTNESS_GATE_FAILED",))
    if correctness_status == "UNVALIDATED":
        return MergedQcResult("UNVALIDATED", (), ("CORRECTNESS_EVIDENCE_MISSING",))
    merged = QualityBundleMerger.merge(scopes)
    if correctness_status == "NEEDS_REVIEW" and merged.status == "PASS":
        return MergedQcResult("NEEDS_REVIEW", (), ("CORRECTNESS_REVIEW_REQUIRED",))
    return merged


def write_immutable_qc_report(path: Path, report: Mapping[str, Any]) -> str:
    """Create a report once; reject a different overwrite."""
    data = _canonical_json(report) + b"\n"
    digest = _sha256(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if path.read_bytes() != data:
            raise Phase4QualityError("IMMUTABLE_REPORT_OVERWRITE")
        return digest
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return digest


def append_qc_history(path: Path, report_ref: Mapping[str, Any]) -> None:
    """Append one immutable history record without rewriting prior records."""
    line = _canonical_json(report_ref) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def manifest_1_4_enrichment(*, report_refs: Mapping[str, Mapping[str, Any]], quality_policy_sha256: str, merged: MergedQcResult) -> dict[str, Any]:
    """Return additive Candidate v3 Manifest 1.4 evidence, without v2 mutation."""
    load_candidate_v3_quality_policy()
    if len(quality_policy_sha256) != 64:
        raise Phase4QualityError("QUALITY_POLICY_SHA256_INVALID")
    if set(report_refs) != {"FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL"}:
        raise Phase4QualityError("QC_REPORT_SET_INCOMPLETE")
    return {
        "manifestVersion": "1.4",
        "candidateV3": {
            "qualityPolicy": {"id": POLICY_ID, "version": POLICY_VERSION, "sha256": quality_policy_sha256},
            "qualityReports": {scope: dict(report_refs[scope]) for scope in ("FACE_LOCAL", "BOUNDARY", "SCENARIO_GLOBAL")},
            "mergedQuality": merged.as_dict(),
            "historyMode": "APPEND_ONLY",
        },
    }
