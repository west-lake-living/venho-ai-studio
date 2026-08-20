"""Build the Action Composite regional-score DTO from explicit QC evidence.

This module is deliberately an adapter, not a second validator.  Validator
Studio remains responsible for observing and scoring images; this gateway only
maps scores whose provenance is explicit and refuses to manufacture missing
regions.
"""

from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field
from PIL import Image

from validator_studio.schemas.validation_base import ValidationReport

from .models import FaceGeometry
from .workflow_v2 import SceneCandidate


REGIONAL_FIELDS = (
    "identity", "eyes_brows", "geometry", "anatomy", "outfit",
    "environment", "global_composite",
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RegionalScoreBlocked(RuntimeError):
    """Raised when a required regional score has no evidence source."""


class PreservationRegionEvidence(BaseModel):
    """Measured post-restoration preservation evidence for one region."""

    stage: Literal["post_identity_restoration"]
    region: Literal["anatomy", "outfit", "environment"]
    source_sha256: str
    candidate_sha256: str
    mask_sha256: str
    pixel_validator_version: str
    formula: str
    protected_pixel_count: int = Field(ge=1)
    changed_protected_pixel_count: int = Field(ge=0)
    changed_percentage: float = Field(ge=0, le=100)
    mean_rgb_delta: float = Field(ge=0)
    max_rgb_delta: int = Field(ge=0)
    preservation_score: float = Field(ge=0, le=100)
    threshold: float = Field(ge=0, le=100)
    status: Literal["PASS", "FAIL", "BLOCKED"]
    applicability: str
    adapter_version: str


class ValidatorExecutionContext(BaseModel):
    """Configuration recorded for a future real Validator Studio invocation."""

    provider: Literal["gemini"] = "gemini"
    model: str = "gemini-flash-latest"
    samples: int = Field(default=3, ge=1)
    project: Optional[str] = None
    image_dna_subject: Optional[str] = None
    scenario_profile_id: Optional[str] = None
    reference_set_id: Optional[str] = None
    reference_set_version: Optional[str] = None
    reference_set_sha256: Optional[str] = None
    validation_config_sha256: Optional[str] = None
    authority_origin: Optional[str] = None
    identity_reference: Optional[str] = None
    pose_reference: Optional[str] = None
    outfit_reference: Optional[str] = None
    environment_reference: Optional[str] = None
    composition_reference: Optional[str] = None
    reference_artifacts: list[str] = Field(default_factory=list)
    source_artifacts: list[str] = Field(default_factory=list)
    config_path: str = "config/validation.yaml"

    def has_complete_global_authority(self) -> bool:
        """Return whether semantic global-validation provenance is complete."""
        required = (
            self.project, self.image_dna_subject, self.scenario_profile_id,
            self.reference_set_id, self.reference_set_version,
            self.reference_set_sha256, self.validation_config_sha256,
            self.provider, self.model, self.samples,
        )
        return all(value not in (None, "", []) for value in required)


class RegionalScoreEvidence(BaseModel):
    """Evidence supplied by upstream producers; no field has a default score."""

    face_report: Optional[ValidationReport] = None
    image_report: Optional[ValidationReport] = None
    geometry_score: Optional[float] = Field(default=None, ge=0, le=100)
    anatomy_score: Optional[float] = Field(default=None, ge=0, le=100)
    outfit_score: Optional[float] = Field(default=None, ge=0, le=100)
    environment_score: Optional[float] = Field(default=None, ge=0, le=100)
    geometry_expected: Optional[FaceGeometry] = None
    geometry_observed: Optional[FaceGeometry] = None
    geometry_source_artifacts: list[str] = Field(default_factory=list)
    scene_candidate: Optional[SceneCandidate] = None
    scene_source_artifacts: list[str] = Field(default_factory=list)
    preservation_evidence: list[PreservationRegionEvidence] = Field(default_factory=list)


class RegionalScoreResult(BaseModel):
    scores: dict[str, float]
    sources: dict[str, str]
    provenance: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RegionalScoreGateway:
    """Map existing validator/producer evidence to the RegionalGate DTO.

    Face and image reports may be produced by ``validator_studio`` before this
    adapter is called.  Scene-region values are accepted only when the scene
    producer supplied them explicitly.  This keeps CandidateSelector scores
    traceable and prevents a missing report from becoming a PASS.
    """

    def build(self, evidence: RegionalScoreEvidence) -> RegionalScoreResult:
        scores: dict[str, float] = {}
        sources: dict[str, str] = {}
        provenance: dict[str, dict[str, Any]] = {}

        face = evidence.face_report
        if face is not None:
            scores["identity"] = _report_score(face.dna_match_score, "face_report.dna_match_score", sources, "identity")
            provenance["identity"] = _report("validator_studio.face_validator", "face_report.dna_match_score", face.dna_match_score,
                                               [face.artifact_ref.file], "regional-evidence-v1")
            eyes = face.category_scores.get("eyes_and_brows")
            scores["eyes_brows"] = _required_number(eyes, "face_report.category_scores.eyes_and_brows")
            sources["eyes_brows"] = "validator_studio.face_validator.category_scores.eyes_and_brows"
            provenance["eyes_brows"] = _report("validator_studio.face_validator", "face_report.category_scores.eyes_and_brows", eyes,
                                                 [face.artifact_ref.file], "regional-evidence-v1")

        if evidence.geometry_expected is not None or evidence.geometry_observed is not None:
            if evidence.geometry_expected is None or evidence.geometry_observed is None:
                raise RegionalScoreBlocked("geometry evidence is incomplete: expected and observed are both required")
            geometry = GeometryEvidenceProducer().produce(
                evidence.geometry_expected, evidence.geometry_observed,
                source_artifacts=evidence.geometry_source_artifacts,
            )
            scores["geometry"], sources["geometry"], provenance["geometry"] = geometry
        else:
            _copy_explicit(scores, sources, "geometry", evidence.geometry_score, "geometry producer")
            if evidence.geometry_score is not None:
                provenance["geometry"] = _report("geometry producer", "explicit geometry score", evidence.geometry_score,
                                                  evidence.geometry_source_artifacts, "regional-evidence-v1")

        if evidence.scene_candidate is not None:
            scene_scores = SceneEvidenceProducer().produce(
                evidence.scene_candidate, source_artifacts=evidence.scene_source_artifacts,
            )
            for field, (score, source, detail) in scene_scores.items():
                scores[field], sources[field], provenance[field] = score, source, detail
        else:
            _copy_explicit(scores, sources, "anatomy", evidence.anatomy_score, "scene candidate/anatomy producer")
            _copy_explicit(scores, sources, "outfit", evidence.outfit_score, "scene candidate/outfit producer")
            _copy_explicit(scores, sources, "environment", evidence.environment_score, "scene candidate/environment producer")
            for field, value in (("anatomy", evidence.anatomy_score), ("outfit", evidence.outfit_score),
                                 ("environment", evidence.environment_score)):
                if value is not None:
                    provenance[field] = _report("scene candidate producer", f"explicit {field} score", value,
                                                evidence.scene_source_artifacts, "regional-evidence-v1")

        if evidence.preservation_evidence:
            for item in evidence.preservation_evidence:
                if item.stage != "post_identity_restoration":
                    raise RegionalScoreBlocked("preservation evidence is unsupported outside post_identity_restoration")
                if item.status != "PASS":
                    raise RegionalScoreBlocked(f"preservation evidence failed for {item.region}")
                scores[item.region] = item.preservation_score
                sources[item.region] = "StagePreservationEvidenceAdapter.pixel-preservation-v1"
                provenance[item.region] = item.model_dump(mode="json")

        image = evidence.image_report
        if image is not None:
            scores["global_composite"] = _report_score(
                image.overall_score, "image_report.overall_score", sources, "global_composite"
            )
            provenance["global_composite"] = _report("validator_studio.image_validator", "image_report.overall_score",
                                                       image.overall_score, [image.artifact_ref.file], "regional-evidence-v1")

        missing = [name for name in REGIONAL_FIELDS if name not in scores]
        if missing:
            raise RegionalScoreBlocked(
                "Regional scores blocked; missing evidence for: " + ", ".join(missing)
            )
        return RegionalScoreResult(scores=scores, sources=sources, provenance=provenance)

    def replay(
        self,
        run_dir: str | Path,
        *,
        evidence: RegionalScoreEvidence,
        persist: bool = True,
    ) -> RegionalScoreResult:
        """Score an existing run without touching ComfyUI.

        Persistence is limited to QC metadata in the existing run directory;
        image artifacts are never regenerated or replaced.
        """
        result = self.build(evidence)
        if persist:
            root = Path(run_dir)
            manifest_path = root / "composite" / "manifest.json"
            if not manifest_path.is_file():
                raise FileNotFoundError(f"Golden-Master manifest not found: {manifest_path}")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["regional_scores"] = result.model_dump()
            (root / "regional_scores.json").write_text(
                json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return result


class ValidatorStudioScoreProducer:
    """Run the existing Validator Studio producers, then hand off to gateway.

    ``provider`` is mandatory on purpose.  The Validator Studio mock observer is
    useful in unit tests, but it is not evidence for a production Golden-Master.
    """

    def produce(
        self,
        *,
        project: str,
        subject: str,
        restored_path: str | Path,
        identity_reference_path: str | Path,
        image_subject: str,
        provider: str,
        geometry_score: Optional[float],
        anatomy_score: Optional[float],
        outfit_score: Optional[float],
        environment_score: Optional[float],
        samples: int = 3,
    ) -> RegionalScoreEvidence:
        if not provider or provider == "mock":
            raise RegionalScoreBlocked("real Validator Studio provider is required; mock evidence is forbidden")
        from validator_studio.face_validator import validate_face
        from validator_studio.image_validator import validate_image

        face_report = validate_face(
            project, subject, Path(restored_path), provider=provider,
            reference_image_paths=[Path(identity_reference_path)], samples=samples,
        )
        image_report = validate_image(
            project, image_subject, Path(restored_path), provider=provider, samples=samples,
        )
        return RegionalScoreEvidence(
            face_report=face_report, image_report=image_report,
            geometry_score=geometry_score, anatomy_score=anatomy_score,
            outfit_score=outfit_score, environment_score=environment_score,
        )


class GeometryEvidenceProducer:
    """Compute geometry agreement from two explicit FaceGeometry observations.

    The score is not a boolean-lock conversion.  It is a deterministic weighted
    agreement: 50% face-box IoU, 30% pose agreement, and 20% face-scale ratio.
    The weights and normalization are versioned in the provenance record.
    """

    VERSION = "geometry-evidence-v1"

    def produce(self, expected: FaceGeometry, observed: FaceGeometry, *,
                source_artifacts: list[str]) -> tuple[float, str, dict[str, Any]]:
        expected_box, observed_box = expected.face_bbox, observed.face_bbox
        iou = _bbox_iou(expected_box, observed_box)
        pose_delta = max(abs(expected.yaw - observed.yaw), abs(expected.pitch - observed.pitch),
                         abs(expected.roll - observed.roll))
        pose_agreement = max(0.0, 1.0 - pose_delta / 180.0)
        scale_agreement = min(expected.face_scale, observed.face_scale) / max(expected.face_scale, observed.face_scale)
        score = round(100.0 * (0.50 * iou + 0.30 * pose_agreement + 0.20 * scale_agreement), 2)
        raw = {"bbox_iou": round(iou, 6), "max_pose_delta_deg": round(pose_delta, 6),
               "pose_agreement": round(pose_agreement, 6), "scale_agreement": round(scale_agreement, 6),
               "weights": {"bbox_iou": 0.50, "pose_agreement": 0.30, "scale_agreement": 0.20}}
        return score, "GeometryEvidenceProducer.geometry-evidence-v1", _report(
            "GeometryEvidenceProducer", "FaceGeometry.expected_vs_observed", score,
            source_artifacts, self.VERSION, raw_evidence=raw,
        )


class StageCorrectGeometryEvidenceAdapter:
    """Opt-in post-restoration adapter using one extractor for both artifacts.

    The normal scene path and the historical ``BBoxFaceDetector`` geometry
    lock are unchanged.  Callers handling identity restoration can use this
    narrow seam to populate the existing ``geometry_expected`` /
    ``geometry_observed`` evidence boundary with compatible observations.
    """

    stage = "post_identity_restoration"
    reference_semantics = "insightface_geometry"
    observed_semantics = "insightface_geometry"

    def __init__(self, extractor: Any) -> None:
        self.extractor = extractor

    def produce(self, *, reference_artifact: str | Path,
                observed_artifact: str | Path) -> tuple[FaceGeometry, FaceGeometry, dict[str, Any]]:
        reference_path = Path(reference_artifact)
        observed_path = Path(observed_artifact)
        reference = self.extractor.extract(reference_path)
        reference_provenance = deepcopy(getattr(self.extractor, "last_provenance", None) or {})
        observed = self.extractor.extract(observed_path)
        observed_provenance = deepcopy(getattr(self.extractor, "last_provenance", None) or {})
        context = {
            "stage": self.stage,
            "reference_semantics": self.reference_semantics,
            "observed_semantics": self.observed_semantics,
            "reference_sha": reference_provenance.get("original_sha256"),
            "observed_sha": observed_provenance.get("original_sha256"),
            "extractor": type(self.extractor).__name__,
            "extractor_method_version": getattr(self.extractor, "method_version", None),
            "landmark_contract": list(getattr(self.extractor, "landmark_order", ())),
            "coordinate_convention": "original artifact pixel coordinates after deterministic analysis preprocessing remap",
            "reference_provenance": reference_provenance,
            "observed_provenance": observed_provenance,
        }
        if not context["reference_sha"] or not context["observed_sha"]:
            raise RegionalScoreBlocked("stage-correct geometry evidence lacks source SHA provenance")
        return reference, observed, context


class StagePreservationEvidenceAdapter:
    """Opt-in post-restoration preservation producer for scene regions.

    It measures only pixels protected by the production effective mask.  The
    three stage-applicable regions share this same deterministic protected
    region; no semantic scene score is inferred from it.
    """

    VERSION = "stage-preservation-evidence-v1"
    PIXEL_VALIDATOR_VERSION = "unchanged_outside_mask-v1"
    STAGE = "post_identity_restoration"
    REGIONS = ("anatomy", "outfit", "environment")
    FORMULA = "100 * (1 - changed_protected_pixels / protected_pixel_count)"

    def produce(self, *, source_artifact: str | Path, candidate_artifact: str | Path,
                mask_artifact: str | Path, crop_box: dict[str, int],
                threshold: float = 90.0) -> list[PreservationRegionEvidence]:
        source_path, candidate_path, mask_path = map(Path, (source_artifact, candidate_artifact, mask_artifact))
        source = Image.open(source_path).convert("RGBA")
        candidate = Image.open(candidate_path).convert("RGBA")
        crop_mask = Image.open(mask_path).convert("L")
        if source.size != candidate.size:
            raise RegionalScoreBlocked("preservation source and candidate dimensions differ")
        expected_size = (crop_box["right"] - crop_box["left"], crop_box["bottom"] - crop_box["top"])
        if crop_mask.size != expected_size:
            raise RegionalScoreBlocked("preservation mask dimensions do not match cropTransform")
        full_mask = Image.new("L", source.size, 0)
        full_mask.paste(crop_mask, (crop_box["left"], crop_box["top"]))
        locked = np.asarray(full_mask) == 0
        left, right = np.asarray(source)[locked], np.asarray(candidate)[locked]
        delta = np.abs(left.astype("int16") - right.astype("int16"))
        changed = np.any(delta != 0, axis=1)
        protected_count = int(locked.sum())
        changed_count = int(changed.sum())
        score = round(100.0 * (1.0 - changed_count / protected_count), 6)
        status = "PASS" if changed_count == 0 and score >= threshold else "FAIL"
        common = {
            "stage": self.STAGE,
            "source_sha256": _file_sha(source_path),
            "candidate_sha256": _file_sha(candidate_path),
            "mask_sha256": _file_sha(mask_path),
            "pixel_validator_version": self.PIXEL_VALIDATOR_VERSION,
            "formula": self.FORMULA,
            "protected_pixel_count": protected_count,
            "changed_protected_pixel_count": changed_count,
            "changed_percentage": round(changed_count / protected_count * 100.0, 8),
            "mean_rgb_delta": float(delta.mean()) if protected_count else 0.0,
            "max_rgb_delta": int(delta.max()) if protected_count else 0,
            "preservation_score": score,
            "threshold": threshold,
            "status": status,
            "applicability": "VERIFY_BY_PIXEL_PRESERVATION",
            "adapter_version": self.VERSION,
        }
        return [PreservationRegionEvidence(region=region, **common) for region in self.REGIONS]


class SceneEvidenceProducer:
    """Expose only candidate scores explicitly named for the target regions."""

    VERSION = "scene-candidate-evidence-v1"

    def produce(self, candidate: SceneCandidate, *, source_artifacts: list[str]) -> dict[str, tuple[float, str, dict[str, Any]]]:
        result: dict[str, tuple[float, str, dict[str, Any]]] = {}
        for field in ("anatomy", "outfit", "environment"):
            value = candidate.scores.get(field)
            if value is None:
                continue
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 100:
                raise RegionalScoreBlocked(f"malformed scene candidate evidence for {field}")
            result[field] = (float(value), f"SceneCandidate.scores.{field}", _report(
                "SceneEvidenceProducer", f"candidate.scores.{field}", value, source_artifacts,
                self.VERSION, raw_evidence={"candidate_id": candidate.candidate_id, "score": value},
            ))
        return result


def _required_number(value: Any, source: str) -> float:
    if value is None:
        raise RegionalScoreBlocked(f"Regional score blocked; missing evidence: {source}")
    if not isinstance(value, (int, float)):
        raise RegionalScoreBlocked(f"Regional score blocked; non-numeric evidence: {source}")
    return float(value)


def _report_score(value: Any, source: str, sources: dict[str, str], field: str) -> float:
    score = _required_number(value, source)
    sources[field] = f"validator_studio.{source}"
    return score


def _copy_explicit(scores: dict[str, float], sources: dict[str, str], field: str,
                   value: Optional[float], source: str) -> None:
    if value is not None:
        scores[field] = float(value)
        sources[field] = source


def _report(producer: str, source: str, score: Any, source_artifacts: list[str],
            method_version: str, *, raw_evidence: Any = None) -> dict[str, Any]:
    if not source_artifacts:
        raise RegionalScoreBlocked(f"missing source artifact for {producer}:{source}")
    numeric = _required_number(score, source)
    return {
        "producer": producer,
        "source_artifacts": list(source_artifacts),
        "method_version": method_version,
        "raw_evidence": raw_evidence if raw_evidence is not None else {"source": source, "value": numeric},
        "resulting_score": numeric,
    }


def _bbox_iou(first: Any, second: Any) -> float:
    left = max(first.left, second.left)
    top = max(first.top, second.top)
    right = min(first.right, second.right)
    bottom = min(first.bottom, second.bottom)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = first.width * first.height + second.width * second.height - intersection
    if union <= 0:
        raise RegionalScoreBlocked("malformed geometry evidence: non-positive bounding-box union")
    return intersection / union
