from __future__ import annotations

import hashlib
import json
import dataclasses
import enum
from io import BytesIO
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from PIL import Image

from ..application.dto.candidate_v3 import (
    ArtifactRef,
    BoundingBox,
    CandidateV3Request,
    CanonicalFaceTransform,
    Landmark,
    SourceImage,
)
from ..application.dto.restore_command import RestoreCommand
from ..application.dto.restoration_result import RestorationResult
from ..application.use_cases.validate_restoration_artifact import ValidateRestorationArtifactCommand
from ..domain.entities import CropTransform, MaskSet
from ..domain.value_objects import RestorationParams
from .candidate_v3_schema import (
    CandidateV3ContractError,
    validate_candidate_v3_request_payload,
    validate_candidate_v3_result_payload as _validate_candidate_v3_result_payload,
)

# stdin/stdout contract for venho-os (GW-D3: subprocess + JSON, same pattern
# as the existing generate_image.py / validate_generated.py bridge). This is
# the shape contracts/restoration_request.schema.json §5.1 abbreviates —
# baseCanvas/mask/cropBox fields are spelled out fully here because the use
# case needs them to composite back into the canvas; see
# contracts/identity_restoration/restoration_request.schema.json (own
# subdirectory — Growth Phase 1's contracts/*.schema.json registry test
# enumerates the flat contracts/ directory by an explicit whitelist, so this
# bounded context's schemas live one level down, not mixed into it) for the
# authoritative, versioned shape.


def _candidate_v3_artifact_ref(payload: dict[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        path=payload["path"],
        sha256=payload["sha256"],
        width=payload["width"],
        height=payload["height"],
        mime_type=payload["mimeType"],
    )


def _candidate_v3_transform(payload: dict[str, Any]) -> CanonicalFaceTransform:
    source_image = payload["sourceImage"]
    crop_box = payload["canvasCropBox"]
    landmarks = tuple(
        Landmark(x=item["x"], y=item["y"], confidence=item["confidence"])
        for item in payload["landmarkSet"]
    )
    return CanonicalFaceTransform(
        version=payload["version"],
        source_image=SourceImage(
            width=source_image["width"],
            height=source_image["height"],
            sha256=source_image["sha256"],
        ),
        canvas_crop_box=BoundingBox(
            left=crop_box["left"],
            top=crop_box["top"],
            right=crop_box["right"],
            bottom=crop_box["bottom"],
        ),
        model_size=payload["modelSize"],
        landmark_set=landmarks,
        forward_matrix_3x3=tuple(payload["forwardMatrix3x3"]),
        inverse_matrix_3x3=tuple(payload["inverseMatrix3x3"]),
        border_mode=payload["borderMode"],
        interpolation=payload["interpolation"],
        transform_sha256=payload["transformSha256"],
    )


def parse_candidate_v3_request(payload: dict[str, Any]) -> CandidateV3Request:
    """Validate and convert an internal Candidate v3 request at the boundary."""
    validated = validate_candidate_v3_request_payload(payload)
    return CandidateV3Request(
        contract_version=validated["contractVersion"],
        run_id=validated["runId"],
        attempt_id=validated["attemptId"],
        canonical_image=_candidate_v3_artifact_ref(validated["canonicalImage"]),
        canonical_editable_mask=_candidate_v3_artifact_ref(validated["canonicalEditableMask"]),
        canonical_feather_mask=_candidate_v3_artifact_ref(validated["canonicalFeatherMask"]),
        transform=_candidate_v3_transform(validated["transform"]),
        selected_identity_references=tuple(
            _candidate_v3_artifact_ref(item)
            for item in validated["selectedIdentityReferences"]
        ),
        candidate_profile_id=validated["candidateProfileId"],
        seed=validated["seed"],
        effective_config_sha256=validated["effectiveConfigSha256"],
        timeout_seconds=validated["timeoutSeconds"],
    )


def load_candidate_v3_request(path: Path) -> CandidateV3Request:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CandidateV3ContractError(
            f"candidate-v3 request invalid JSON at {path}: {exc.msg}"
        ) from exc
    return parse_candidate_v3_request(payload)


def validate_candidate_v3_result_payload(payload: Any) -> dict[str, Any]:
    """Normalize a result boundary value, then validate its complete evidence shape."""
    normalized = _json_safe(payload)
    return _validate_candidate_v3_result_payload(normalized)


def dump_candidate_v3_result(result: Any) -> str:
    """Validate a Candidate v3 result before deterministic JSON serialization."""
    return serialize_json(validate_candidate_v3_result_payload(result))


def parse_restore_command(payload: dict[str, Any]) -> RestoreCommand:
    box = payload["cropBox"]
    transform = CropTransform.from_box(
        left=int(box["left"]), top=int(box["top"]), right=int(box["right"]), bottom=int(box["bottom"]),
        target_size=int(box.get("targetSize", box["right"] - box["left"])),
    )
    params = payload["params"]
    crop_bytes = Path(payload["cropPath"]).read_bytes()
    base_bytes = Path(payload["basePath"]).read_bytes()
    mask = MaskSet(
        editable=Path(payload["maskEditablePath"]).read_bytes(),
        feather=Path(payload.get("maskFeatherPath", payload["maskEditablePath"])).read_bytes(),
        version=payload.get("maskVersion", "hierarchical_face_v1"),
    )
    full_canvas_path = Path(payload["fullCanvasMaskPath"])
    full_canvas_bytes = full_canvas_path.read_bytes()
    expected_full_canvas_sha = payload["fullCanvasMaskSha256"]
    actual_full_canvas_sha = hashlib.sha256(full_canvas_bytes).hexdigest()
    if actual_full_canvas_sha != expected_full_canvas_sha:
        raise ValueError(
            "full-canvas mask SHA-256 mismatch: "
            f"expected {expected_full_canvas_sha}, got {actual_full_canvas_sha}"
        )
    full_canvas_mask = MaskSet(
        editable=full_canvas_bytes,
        feather=Path(payload.get("fullCanvasMaskFeatherPath", full_canvas_path)).read_bytes(),
        version=payload.get("fullCanvasMaskVersion", "hierarchical_face_v1_full_canvas"),
    )
    base_size = Image.open(BytesIO(base_bytes)).size
    crop_size = Image.open(BytesIO(crop_bytes)).size
    crop_mask_size = Image.open(BytesIO(mask.editable)).size
    full_mask_size = Image.open(BytesIO(full_canvas_mask.editable)).size
    if crop_mask_size != crop_size:
        raise ValueError(f"crop-local mask {crop_mask_size} must match crop {crop_size}")
    if full_mask_size != base_size:
        raise ValueError(f"full-canvas mask {full_mask_size} must match base {base_size}")
    return RestoreCommand(
        run_id=payload["runId"],
        attempt_id=payload["attemptId"],
        restorer_id=payload["restorerId"],
        crop_png=crop_bytes,
        mask=mask,
        full_canvas_mask=full_canvas_mask,
        base_canvas_png=base_bytes,
        crop_transform=transform,
        a2_path=payload["a2Path"],
        a2_sha256=payload["a2Sha256"],
        workflow_id=payload["workflowId"],
        seed=int(payload["seed"]),
        params=RestorationParams(**params),
        timeout_seconds=int(payload.get("timeoutSeconds", 600)),
    )


def load_restore_command(path: Path) -> RestoreCommand:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_restore_command(payload)


def parse_validate_restoration_artifact(payload: dict[str, Any]) -> ValidateRestorationArtifactCommand:
    if payload.get("contractVersion") != "1.0":
        raise ValueError("validation request contractVersion must be 1.0")
    required = ("runId", "attemptId", "compositePath", "a2Path", "artifactAttemptId")
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
        raise ValueError("validation request is missing required fields")
    return ValidateRestorationArtifactCommand(
        run_id=payload["runId"],
        attempt_id=payload["attemptId"],
        composite_path=payload["compositePath"],
        a2_path=payload["a2Path"],
        artifact_attempt_id=payload["artifactAttemptId"],
    )


def load_validate_restoration_artifact(path: Path) -> ValidateRestorationArtifactCommand:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("validation request must be an object")
    return parse_validate_restoration_artifact(payload)


def _json_safe(value: Any) -> Any:
    """Normalize boundary values without falling back to Python repr()."""
    if isinstance(value, enum.Enum):
        return _json_safe(value.value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return value


def serialize_json(payload: Any) -> str:
    """Return one deterministic, UTF-8-safe machine-readable JSON document."""
    return json.dumps(_json_safe(payload), ensure_ascii=False, sort_keys=True, default=_json_default)


def _json_default(value: Any) -> Any:
    """Fail closed for values not covered by the explicit normalizer."""
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def emit_json(payload: Any) -> None:
    """Write exactly one JSON document to stdout, followed by one newline."""
    print(serialize_json(payload))


def dump_result(result: RestorationResult) -> str:
    """Sanitized stdout payload; retained for callers/tests of the bridge."""
    return serialize_json(result.to_json_dict())
