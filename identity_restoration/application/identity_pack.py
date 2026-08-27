from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Mapping


IdentityPackStatus = Literal["DRAFT", "APPROVED", "RETIRED"]
IdentityReferenceRole = Literal["PRIMARY_FRONTAL", "THREE_QUARTER", "PROFILE"]
UsableRegion = Literal["eyes", "nose", "mouth", "jaw", "hairline"]


class IdentityPackError(ValueError):
    """Base error for fail-closed IdentityPack validation."""


class IdentityPackNotFoundError(IdentityPackError):
    pass


class IdentityPackMalformedError(IdentityPackError):
    pass


class IdentityPackIntegrityError(IdentityPackError):
    pass


class IdentityPackNotApprovedError(IdentityPackError):
    pass


@dataclass(frozen=True)
class IdentityPose:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    tolerance_deg: float

    def __post_init__(self) -> None:
        values = (self.yaw_deg, self.pitch_deg, self.roll_deg, self.tolerance_deg)
        if not all(math.isfinite(float(value)) for value in values):
            raise IdentityPackMalformedError("identity reference pose must contain finite numbers")
        if self.tolerance_deg < 0:
            raise IdentityPackMalformedError("identity reference pose tolerance must be non-negative")


@dataclass(frozen=True)
class FaceBounds:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if not all(math.isfinite(float(value)) for value in values):
            raise IdentityPackMalformedError("face bounds must contain finite numbers")
        if min(self.left, self.top, self.right, self.bottom) < 0:
            raise IdentityPackMalformedError("face bounds must be non-negative")
        if self.right <= self.left or self.bottom <= self.top:
            raise IdentityPackMalformedError("face bounds must have positive width and height")

    def as_dict(self) -> dict[str, float]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
        }


@dataclass(frozen=True)
class IdentityReference:
    reference_id: str
    artifact_path: str
    artifact_sha256: str
    role: IdentityReferenceRole
    pose: IdentityPose
    face_bounds: FaceBounds
    usable_regions: tuple[UsableRegion, ...]
    consent_or_authority_ref: str
    approved: bool

    def __post_init__(self) -> None:
        if not self.reference_id or not self.artifact_path or not self.artifact_sha256:
            raise IdentityPackMalformedError("identity reference identifiers and hash are required")
        if not self.usable_regions or len(set(self.usable_regions)) != len(self.usable_regions):
            raise IdentityPackMalformedError("identity reference usable regions must be unique and non-empty")
        if not self.consent_or_authority_ref:
            raise IdentityPackMalformedError("identity reference authority is required")


@dataclass(frozen=True)
class IdentityPack:
    """Immutable application authority; approved packs have no mutation API."""

    schema_version: str
    identity_pack_id: str
    identity_subject_id: str
    status: IdentityPackStatus
    references: tuple[IdentityReference, ...]
    sha256: str
    approved_at: str | None = None
    approved_by: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "references", tuple(self.references))
        if self.schema_version != "1.0":
            raise IdentityPackMalformedError("unsupported IdentityPack schema version")
        if not self.identity_pack_id or self.identity_subject_id != "linh-an":
            raise IdentityPackMalformedError("invalid IdentityPack identity")
        if self.status not in {"DRAFT", "APPROVED", "RETIRED"}:
            raise IdentityPackMalformedError("invalid IdentityPack status")
        reference_ids = [reference.reference_id for reference in self.references]
        if len(reference_ids) != len(set(reference_ids)):
            raise IdentityPackMalformedError("duplicate referenceId exists")
        if self.status == "APPROVED" and (not self.approved_at or not self.approved_by):
            raise IdentityPackMalformedError("APPROVED IdentityPack requires approval metadata")

    def references_for_role(self, role: IdentityReferenceRole) -> tuple[IdentityReference, ...]:
        return tuple(reference for reference in self.references if reference.role == role)

    def validate_approved(self) -> None:
        if self.status != "APPROVED":
            raise IdentityPackNotApprovedError(
                f"IdentityPack {self.identity_pack_id!r} status is {self.status}, not APPROVED"
            )
        primary_count = len(self.references_for_role("PRIMARY_FRONTAL"))
        if primary_count != 1:
            raise IdentityPackMalformedError(
                f"APPROVED IdentityPack requires exactly one PRIMARY_FRONTAL; found {primary_count}"
            )
        unapproved = [reference.reference_id for reference in self.references if not reference.approved]
        if unapproved:
            raise IdentityPackMalformedError(
                "APPROVED IdentityPack contains unapproved references: " + ", ".join(unapproved)
            )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "IdentityPack":
        references = tuple(
            _reference_from_mapping(reference)
            for reference in _as_sequence(payload.get("references"), "references")
        )
        return cls(
            schema_version=_as_string(payload.get("schemaVersion"), "schemaVersion"),
            identity_pack_id=_as_string(payload.get("identityPackId"), "identityPackId"),
            identity_subject_id=_as_string(payload.get("identitySubjectId"), "identitySubjectId"),
            status=_as_string(payload.get("status"), "status"),  # type: ignore[arg-type]
            references=references,
            sha256=_as_string(payload.get("sha256"), "sha256"),
            approved_at=_optional_string(payload.get("approvedAt")),
            approved_by=_optional_string(payload.get("approvedBy")),
        )


def _reference_from_mapping(payload: object) -> IdentityReference:
    mapping = _as_mapping(payload, "reference")
    pose = _as_mapping(mapping.get("pose"), "pose")
    bounds = _as_mapping(mapping.get("faceBounds"), "faceBounds")
    return IdentityReference(
        reference_id=_as_string(mapping.get("referenceId"), "referenceId"),
        artifact_path=_as_string(mapping.get("artifactPath"), "artifactPath"),
        artifact_sha256=_as_string(mapping.get("artifactSha256"), "artifactSha256"),
        role=_as_string(mapping.get("role"), "role"),  # type: ignore[arg-type]
        pose=IdentityPose(
            yaw_deg=_as_number(pose.get("yawDeg"), "yawDeg"),
            pitch_deg=_as_number(pose.get("pitchDeg"), "pitchDeg"),
            roll_deg=_as_number(pose.get("rollDeg"), "rollDeg"),
            tolerance_deg=_as_number(pose.get("toleranceDeg"), "toleranceDeg"),
        ),
        face_bounds=FaceBounds(
            left=_as_number(bounds.get("left"), "left"),
            top=_as_number(bounds.get("top"), "top"),
            right=_as_number(bounds.get("right"), "right"),
            bottom=_as_number(bounds.get("bottom"), "bottom"),
        ),
        usable_regions=tuple(_as_string(region, "usableRegion") for region in _as_sequence(
            mapping.get("usableRegions"), "usableRegions"
        )),  # type: ignore[arg-type]
        consent_or_authority_ref=_as_string(
            mapping.get("consentOrAuthorityRef"), "consentOrAuthorityRef"
        ),
        approved=_as_bool(mapping.get("approved"), "approved"),
    )


def _as_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise IdentityPackMalformedError(f"{name} must be an object")
    return value


def _as_sequence(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise IdentityPackMalformedError(f"{name} must be an array")
    return value


def _as_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise IdentityPackMalformedError(f"{name} must be a non-empty string")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _as_string(value, "approval metadata")


def _as_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IdentityPackMalformedError(f"{name} must be numeric")
    return float(value)


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise IdentityPackMalformedError(f"{name} must be boolean")
    return value
