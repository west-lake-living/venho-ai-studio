from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import jsonschema

from ...application.identity_pack import (
    FaceBounds,
    IdentityPack,
    IdentityPackError,
    IdentityPackIntegrityError,
    IdentityPackMalformedError,
    IdentityPackNotFoundError,
)


def canonical_pack_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return canonical UTF-8 JSON with the root ``sha256`` field omitted.

    The root hash therefore authenticates the complete pack payload without
    creating a self-hash paradox. JSON formatting and source key order do not
    affect the result.
    """

    without_hash = dict(payload)
    without_hash.pop("sha256", None)
    return json.dumps(
        without_hash,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_pack_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_pack_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class FileIdentityPackRepository:
    """Read-only server-side IdentityPack registry.

    The registry has no write or mutation operation. Artifact paths are
    repository-relative and are resolved only here, at the infrastructure
    boundary. Existing A2 authority is a repository-local symlink, so lexical
    containment is checked before reading the trusted path.
    """

    repo_root: str | Path
    pack_directory: str | Path | None = None
    schema_path: str | Path | None = None
    face_detector: Any | None = None

    def __post_init__(self) -> None:
        root = Path(self.repo_root).resolve()
        pack_directory = Path(self.pack_directory) if self.pack_directory is not None else (
            root / "config" / "identity_restoration" / "identity_packs"
        )
        schema_path = Path(self.schema_path) if self.schema_path is not None else (
            root / "contracts" / "identity_restoration" / "identity_pack_v1.schema.json"
        )
        if not pack_directory.is_absolute():
            pack_directory = root / pack_directory
        if not schema_path.is_absolute():
            schema_path = root / schema_path
        object.__setattr__(self, "repo_root", root)
        object.__setattr__(self, "pack_directory", pack_directory.resolve())
        object.__setattr__(self, "schema_path", schema_path.resolve())
        if self.face_detector is None:
            from image_studio_runtime.action_composite.geometry import YuNetGeometryExtractor

            object.__setattr__(self, "face_detector", YuNetGeometryExtractor())

    def get(self, identity_pack_id: str) -> IdentityPack:
        document = self._read_document(identity_pack_id)
        self._validate_schema(document)
        self._validate_pack_hash(document, identity_pack_id)
        pack = IdentityPack.from_mapping(document)
        if pack.status == "APPROVED":
            pack.validate_approved()
        self._validate_artifacts(pack)
        return pack

    def get_approved(self, identity_pack_id: str) -> IdentityPack:
        pack = self.get(identity_pack_id)
        pack.validate_approved()
        return pack

    def _read_document(self, identity_pack_id: str) -> dict[str, Any]:
        path = self._pack_path(identity_pack_id)
        if not path.is_file():
            raise IdentityPackNotFoundError(f"IdentityPack {identity_pack_id!r} was not found")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IdentityPackMalformedError(
                f"IdentityPack {identity_pack_id!r} is not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise IdentityPackMalformedError("IdentityPack root must be a JSON object")
        return payload

    def _pack_path(self, identity_pack_id: str) -> Path:
        if not isinstance(identity_pack_id, str) or not identity_pack_id:
            raise IdentityPackNotFoundError("identity_pack_id must be a non-empty stable ID")
        candidate_id = Path(identity_pack_id)
        if candidate_id.is_absolute() or candidate_id.name != identity_pack_id or ".." in candidate_id.parts:
            raise IdentityPackNotFoundError("identity_pack_id must not contain path traversal")
        path = Path(self.pack_directory) / f"{identity_pack_id}.json"
        try:
            path.relative_to(Path(self.pack_directory))
        except ValueError as exc:
            raise IdentityPackNotFoundError("identity_pack_id escapes the registry directory") from exc
        return path

    def _validate_schema(self, document: Mapping[str, Any]) -> None:
        try:
            schema = json.loads(Path(self.schema_path).read_text(encoding="utf-8"))
            validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
            errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
        except (OSError, UnicodeError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
            raise IdentityPackMalformedError("IdentityPack schema authority is unavailable or invalid") from exc
        if errors:
            raise IdentityPackMalformedError(f"IdentityPack schema validation failed: {errors[0].message}")

    def _validate_pack_hash(self, document: Mapping[str, Any], identity_pack_id: str) -> None:
        expected = document.get("sha256")
        actual = canonical_pack_sha256(document)
        if expected != actual:
            raise IdentityPackIntegrityError(
                f"IdentityPack {identity_pack_id!r} canonical sha256 mismatch: expected {expected}, got {actual}"
            )

    def _validate_artifacts(self, pack: IdentityPack) -> None:
        for reference in pack.references:
            artifact_path = self._artifact_path(reference.artifact_path)
            if not artifact_path.is_file():
                raise IdentityPackIntegrityError(
                    f"reference artifact is missing: {reference.artifact_path}"
                )
            actual_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_sha256 != reference.artifact_sha256:
                raise IdentityPackIntegrityError(
                    f"reference artifact sha256 mismatch for {reference.reference_id!r}: "
                    f"expected {reference.artifact_sha256}, got {actual_sha256}"
                )
            self._validate_one_detectable_face(reference.reference_id, artifact_path, reference.face_bounds)

    def _artifact_path(self, artifact_path: str) -> Path:
        relative = Path(artifact_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise IdentityPackIntegrityError(
                f"artifact path must be repository-relative and cannot traverse: {artifact_path!r}"
            )
        candidate = Path(self.repo_root) / relative
        try:
            candidate.relative_to(Path(self.repo_root))
        except ValueError as exc:
            raise IdentityPackIntegrityError(f"artifact path escapes repository root: {artifact_path!r}") from exc
        return candidate

    def _validate_one_detectable_face(
        self, reference_id: str, artifact_path: Path, expected_bounds: FaceBounds
    ) -> None:
        try:
            detector = self.face_detector
            if hasattr(detector, "extract"):
                detection = detector.extract(artifact_path)
            elif callable(detector):
                detection = detector(artifact_path)
            else:  # pragma: no cover - constructor prevents this in normal use
                raise TypeError("face_detector must be callable or expose extract")
            detected_bounds = getattr(detection, "face_bbox", None)
            if detected_bounds is None:
                raise ValueError("detector returned no face bounds")
            actual_bounds = FaceBounds(
                left=float(detected_bounds.left),
                top=float(detected_bounds.top),
                right=float(detected_bounds.right),
                bottom=float(detected_bounds.bottom),
            )
        except Exception as exc:
            if isinstance(exc, IdentityPackError):
                raise
            raise IdentityPackIntegrityError(
                f"reference {reference_id!r} does not contain exactly one detectable face: {exc}"
            ) from exc
        if actual_bounds != expected_bounds:
            raise IdentityPackIntegrityError(
                f"faceBounds mismatch for {reference_id!r}: "
                f"pack={expected_bounds.as_dict()}, detector={actual_bounds.as_dict()}"
            )
