from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPO_ROOT / "contracts" / "identity_restoration"
SCHEMA_NAMES = [
    "identity_pack_v1.schema.json",
    "scenario_authority_binding_v1.schema.json",
    "face_observability_v1.schema.json",
    "canonical_face_transform_v1.schema.json",
    "candidate_v3_request_v1.schema.json",
    "candidate_v3_result_v1.schema.json",
]

SHA = "a" * 64
TIMESTAMP = "2026-08-27T10:00:00Z"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _validate(payload: dict, schema_name: str) -> None:
    jsonschema.validate(
        payload,
        _schema(schema_name),
        format_checker=jsonschema.FormatChecker(),
    )


def _identity_reference(role: str = "PRIMARY_FRONTAL") -> dict:
    return {
        "referenceId": "linh-an-a2",
        "artifactPath": "identity/linh-an/a2.png",
        "artifactSha256": SHA,
        "role": role,
        "pose": {
            "yawDeg": 0,
            "pitchDeg": 0,
            "rollDeg": 0,
            "toleranceDeg": 15,
        },
        "faceBounds": {"left": 120, "top": 80, "right": 392, "bottom": 440},
        "usableRegions": ["eyes", "nose", "mouth", "jaw", "hairline"],
        "consentOrAuthorityRef": "consent/linh-an-2026",
        "approved": True,
    }


def _identity_pack() -> dict:
    return {
        "schemaVersion": "1.0",
        "identityPackId": "linh-an-production-2026-08",
        "identitySubjectId": "linh-an",
        "status": "APPROVED",
        "approvedAt": TIMESTAMP,
        "approvedBy": "identity-reviewer",
        "references": [_identity_reference()],
        "sha256": SHA,
    }


def _scenario_binding() -> dict:
    return {
        "schemaVersion": "1.0",
        "bindingId": "binding-west-lake-sunrise-2026",
        "scenarioId": "west-lake-sunrise",
        "imageQcProfileId": "restoration-v3-quality-policy-1",
        "imageQcProfileSha256": SHA,
        "allowedExclusions": ["hairstyle", "background"],
        "approvedBy": "scenario-reviewer",
        "approvedAt": TIMESTAMP,
        "status": "APPROVED",
    }


def _face_observability() -> dict:
    return {
        "schemaVersion": "1.0",
        "imageSha256": SHA,
        "imageWidth": 1024,
        "imageHeight": 1024,
        "maskSha256": SHA,
        "maskWidth": 1024,
        "maskHeight": 1024,
        "detectorId": "face-detector",
        "detectorVersion": "1.2.0",
        "detectorConfigSha256": SHA,
        "faceCount": 1,
        "selectedFaceIndex": 0,
        "selectedFaceConfidence": 0.98,
        "bbox": {"left": 100, "top": 70, "right": 420, "bottom": 450},
        "landmarks": [
            {"x": 210, "y": 180}, {"x": 330, "y": 180},
            {"x": 270, "y": 250}, {"x": 225, "y": 330}, {"x": 315, "y": 330},
        ],
        "detectedFaces": [{
            "confidence": 0.98,
            "bbox": {"left": 100, "top": 70, "right": 420, "bottom": 450},
            "landmarks": [
                {"x": 210, "y": 180}, {"x": 330, "y": 180},
                {"x": 270, "y": 250}, {"x": 225, "y": 330}, {"x": 315, "y": 330},
            ],
            "yawDeg": 4.2,
            "pitchDeg": -1.1,
            "rollDeg": 0.4,
        }],
        "bboxWidthPx": 320,
        "bboxHeightPx": 380,
        "interocularDistancePx": 98,
        "faceCenter": {"x": 260, "y": 260},
        "yawDeg": 4.2,
        "pitchDeg": -1.1,
        "rollDeg": 0.4,
        "borderClipped": False,
        "faceBboxIntersectsEditableMask": True,
        "faceBboxMaskOverlapAreaPx": 10000,
        "faceBboxMaskOverlapRatio": 0.08,
        "editableMaskNonzeroPixelCount": 12000,
        "editableMaskCoverageRatio": 0.011,
        "faceCenterInsideEditableMask": True,
        "status": "VALID",
        "qualityTier": "HIGH",
        "failureReasons": [],
        "measurementConfigSha256": SHA,
        "measurementSha256": SHA,
    }


def _transform() -> dict:
    return {
        "version": "1.0",
        "sourceImage": {"width": 1536, "height": 1024, "sha256": SHA},
        "canvasCropBox": {"left": 80, "top": 20, "right": 500, "bottom": 500},
        "modelSize": 512,
        "landmarkSet": [
            {"x": 210, "y": 180, "confidence": 0.99},
            {"x": 330, "y": 180, "confidence": 0.99},
            {"x": 270, "y": 250, "confidence": 0.98},
            {"x": 225, "y": 330, "confidence": 0.97},
            {"x": 315, "y": 330, "confidence": 0.97},
        ],
        "forwardMatrix3x3": [1, 0, 0, 0, 1, 0, 0, 0, 1],
        "inverseMatrix3x3": [1, 0, 0, 0, 1, 0, 0, 0, 1],
        "borderMode": "REFLECT_101",
        "interpolation": "LANCZOS4",
        "transformSha256": SHA,
    }


def _artifact(path: str, width: int = 1536, height: int = 1024) -> dict:
    return {
        "path": path,
        "sha256": SHA,
        "width": width,
        "height": height,
        "mimeType": "image/png",
    }


def _canonical_artifact(path: str) -> dict:
    return _artifact(path, width=512, height=512)


def _request() -> dict:
    return {
        "contractVersion": "1.0",
        "runId": "run-candidate-v3-001",
        "attemptId": "attempt-001",
        "canonicalImage": _canonical_artifact("runs/run-candidate-v3-001/canonical.png"),
        "canonicalEditableMask": _canonical_artifact("runs/run-candidate-v3-001/editable.png"),
        "canonicalFeatherMask": _canonical_artifact("runs/run-candidate-v3-001/feather.png"),
        "transform": _transform(),
        "selectedIdentityReferences": [_artifact("identity/linh-an/a2.png")],
        "candidateProfileId": "candidate-v3-sd15-faceid-canonical-512",
        "seed": 42,
        "effectiveConfigSha256": SHA,
        "timeoutSeconds": 300,
    }


def _scoped_qc(scope: str) -> dict:
    return {
        "status": "PASS",
        "validatorId": f"{scope.lower()}-validator",
        "validatorConfigSha256": SHA,
        "authorityRef": {"id": f"{scope.lower()}-authority", "sha256": SHA},
        "report": _artifact(f"reports/{scope.lower()}.json"),
        "measuredAt": TIMESTAMP,
        "scores": {"quality": 0.99},
        "binaryGates": [{"id": f"{scope.lower()}-gate", "passed": True}],
    }


def _result() -> dict:
    return {
        "schemaVersion": "1.0",
        "candidateProfileId": "candidate-v3-sd15-faceid-canonical-512",
        "candidateVersion": "3.0.0",
        "effectiveConfigSha256": SHA,
        "inputArtifact": _artifact("runs/run-candidate-v3-001/base.png"),
        "identityPack": {
            "id": "linh-an-production-2026-08",
            "sha256": SHA,
            "selectedReferenceIds": ["linh-an-a2"],
        },
        "scenarioAuthority": {"id": "binding-west-lake-sunrise-2026", "sha256": SHA},
        "route": {"code": "ELIGIBLE", "reasons": []},
        "faceObservability": _face_observability(),
        "transforms": _transform(),
        "artifacts": {
            "canonicalInput": _canonical_artifact("runs/run-candidate-v3-001/canonical.png"),
            "canonicalEditableMask": _canonical_artifact("runs/run-candidate-v3-001/editable.png"),
            "canonicalFeatherMask": _canonical_artifact("runs/run-candidate-v3-001/feather.png"),
            "restoredCanonicalCrop": _canonical_artifact("runs/run-candidate-v3-001/restored.png"),
            "inverseWarpedCrop": _artifact("runs/run-candidate-v3-001/inverse.png", 480, 480),
            "finalComposite": _artifact("runs/run-candidate-v3-001/final.png"),
            "fullCanvasEditableMask": _artifact("runs/run-candidate-v3-001/full-mask.png"),
        },
        "quality": {
            "faceLocal": _scoped_qc("FACE_LOCAL"),
            "boundary": _scoped_qc("BOUNDARY"),
            "scenarioGlobal": _scoped_qc("SCENARIO_GLOBAL"),
            "merged": {
                "status": "PASS",
                "failedScopes": [],
                "decisiveReasons": [],
            },
        },
        "promotionEligibility": "UNVALIDATED",
    }


def test_all_candidate_v3_schemas_are_valid_draft_2020_12_schemas() -> None:
    for name in SCHEMA_NAMES:
        jsonschema.Draft202012Validator.check_schema(_schema(name))


def test_valid_identity_pack() -> None:
    _validate(_identity_pack(), "identity_pack_v1.schema.json")


def test_malformed_sha_is_rejected() -> None:
    payload = _identity_pack()
    payload["sha256"] = "abc123"
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "identity_pack_v1.schema.json")


def test_invalid_identity_role_is_rejected() -> None:
    payload = _identity_pack()
    payload["references"][0]["role"] = "SIDE_LEFT"
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "identity_pack_v1.schema.json")


def test_invalid_scenario_exclusion_is_rejected() -> None:
    payload = _scenario_binding()
    payload["allowedExclusions"] = ["skin_color"]
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "scenario_authority_binding_v1.schema.json")


def test_valid_face_observability() -> None:
    _validate(_face_observability(), "face_observability_v1.schema.json")


def test_invalid_route_code_is_rejected() -> None:
    payload = _result()
    payload["route"]["code"] = "AUTO_PASS"
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")


def test_valid_canonical_face_transform() -> None:
    _validate(_transform(), "canonical_face_transform_v1.schema.json")


def test_model_size_other_than_512_is_rejected() -> None:
    payload = _transform()
    payload["modelSize"] = 256
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "canonical_face_transform_v1.schema.json")


def test_matrix_wrong_cardinality_is_rejected() -> None:
    payload = _transform()
    payload["forwardMatrix3x3"] = payload["forwardMatrix3x3"][:8]
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "canonical_face_transform_v1.schema.json")


def test_valid_candidate_v3_request() -> None:
    _validate(_request(), "candidate_v3_request_v1.schema.json")


def test_non_512_canonical_artifact_is_rejected() -> None:
    payload = _request()
    payload["canonicalImage"]["width"] = 768
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_request_v1.schema.json")


def test_valid_candidate_v3_result() -> None:
    _validate(_result(), "candidate_v3_result_v1.schema.json")


@pytest.mark.parametrize("missing", ["scenarioAuthority", "quality"])
def test_missing_required_result_evidence_is_rejected(missing: str) -> None:
    payload = _result()
    payload.pop(missing)
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")


@pytest.mark.parametrize("missing_scope", ["boundary", "scenarioGlobal"])
def test_missing_qc_scope_is_rejected(missing_scope: str) -> None:
    payload = _result()
    payload["quality"].pop(missing_scope)
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")


def test_invalid_promotion_eligibility_is_rejected() -> None:
    payload = _result()
    payload["promotionEligibility"] = "PRODUCTION_APPROVED"
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")


def test_unknown_critical_property_is_rejected() -> None:
    payload = _result()
    payload["unsafeOverride"] = True
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")


def test_unknown_nested_critical_property_is_rejected() -> None:
    payload = _result()
    payload["quality"]["faceLocal"]["unsafeOverride"] = True
    with pytest.raises(jsonschema.ValidationError):
        _validate(payload, "candidate_v3_result_v1.schema.json")
