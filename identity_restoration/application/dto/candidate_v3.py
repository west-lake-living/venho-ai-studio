from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str
    width: int
    height: int
    mime_type: str


@dataclass(frozen=True)
class SourceImage:
    width: int
    height: int
    sha256: str


@dataclass(frozen=True)
class BoundingBox:
    left: int | float
    top: int | float
    right: int | float
    bottom: int | float


@dataclass(frozen=True)
class Landmark:
    x: int | float
    y: int | float
    confidence: int | float


@dataclass(frozen=True)
class CanonicalFaceTransform:
    version: str
    source_image: SourceImage
    canvas_crop_box: BoundingBox
    model_size: int
    landmark_set: tuple[Landmark, ...]
    forward_matrix_3x3: tuple[int | float, ...]
    inverse_matrix_3x3: tuple[int | float, ...]
    border_mode: str
    interpolation: str
    transform_sha256: str


@dataclass(frozen=True)
class CandidateV3Request:
    contract_version: str
    run_id: str
    attempt_id: str
    canonical_image: ArtifactRef
    canonical_editable_mask: ArtifactRef
    canonical_feather_mask: ArtifactRef
    transform: CanonicalFaceTransform
    selected_identity_references: tuple[ArtifactRef, ...]
    candidate_profile_id: str
    seed: int
    effective_config_sha256: str
    timeout_seconds: int
