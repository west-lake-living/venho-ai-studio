"""Identity Measurement Authority R1: blur / framing over the pinned YuNet observer (occlusion is a human gate).

Local, deterministic, CPU-only, no network. Blur and framing, and their thresholds, are the
Human-approved policy ``linh-an-identity-measurement`` v1.1 (schema
``identity-measurement-policy-v1``); this module implements exactly the algorithm versions that
policy names and refuses any policy it does not implement. It never chooses a threshold.

OCCLUSION is not measured here. No local signal can tell a covered eye or nose from a visible one
(landmark proxy and face-parsing were both benchmarked and rejected), so the policy declares it a
``HUMAN_HARD_GATE``: a person must approve each candidate; a policy that names an automated
occlusion algorithm is refused.

* BLUR      ``laplacian-variance-gray256-v1``: variance of the Laplacian (OpenCV, CV_64F, ksize 3)
            of the grayscale face-bbox crop resized to 256x256 (INTER_AREA). Unit ``variance_px2``.
* FRAMING   ``bbox-visibility-v1``: exactly one face, bbox not clipped by the border, bbox
            height / frame height, bbox centre inside the frame. The face need not be centred.

A result is canonical JSON with no path, time, PID or host: same bytes + same policy give the same
``resultSha256``. ``pass`` is derived here and re-derived by the consumer from the recorded value,
operator, threshold and checks.
"""

from __future__ import annotations

import hashlib
import json
import math
from io import BytesIO
from typing import Any, Mapping, Protocol

import numpy as np
from PIL import Image

from .face_observability import _decode_image

POLICY_SCHEMA = "identity-measurement-policy-v1"
RESULT_SCHEMA = "identity-measurement-result-v1"
SET_SCHEMA = "identity-measurement-set-v1"
POLICY_ID = "linh-an-identity-measurement"

BLUR = "BLUR"
FRAMING = "FRAMING"
OCCLUSION = "OCCLUSION"
MEASUREMENT_TYPES = (BLUR, FRAMING)
HUMAN_HARD_GATE = "HUMAN_HARD_GATE"
HUMAN_GATES = (OCCLUSION,)

ALGORITHMS = {
    BLUR: "laplacian-variance-gray256-v1",
    FRAMING: "bbox-visibility-v1",
}
UNITS = {BLUR: "variance_px2", FRAMING: "ratio"}
OPERATORS = {BLUR: ">=", FRAMING: ">="}
CANONICAL_FACE_CROP = 256
ROUND = 6


class MeasurementPolicyError(ValueError):
    """The policy is missing, tampered with, or names something this runtime does not implement."""


class Observer(Protocol):
    def observe(self, image_bytes: bytes, editable_mask: bytes) -> Any: ...


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def policy_hash(policy: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of the policy without its own ``policyHash`` field."""
    return sha256_hex(canonical_json({k: v for k, v in policy.items() if k != "policyHash"}))


def load_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Verify hash, identity and that every named algorithm/operator/unit is implemented here."""
    if not isinstance(policy, Mapping):
        raise MeasurementPolicyError("policy is not an object")
    if policy.get("schemaVersion") != POLICY_SCHEMA or policy.get("policyId") != POLICY_ID:
        raise MeasurementPolicyError("policy schema or id is not supported")
    if not isinstance(policy.get("policyVersion"), str) or not policy["policyVersion"]:
        raise MeasurementPolicyError("policy version is missing")
    if policy.get("policyHash") != policy_hash(policy):
        raise MeasurementPolicyError("policy hash does not match its canonical payload")
    measurements = policy.get("measurements")
    if not isinstance(measurements, Mapping) or set(measurements) != set(MEASUREMENT_TYPES):
        raise MeasurementPolicyError("policy must define exactly BLUR and FRAMING measurements")
    gates = policy.get("humanGates")
    if not isinstance(gates, Mapping) or set(gates) != set(HUMAN_GATES):
        raise MeasurementPolicyError("policy must declare OCCLUSION as its only human gate")
    for kind in HUMAN_GATES:
        if gates[kind] != {"authority": HUMAN_HARD_GATE, "automatedMeasurement": False}:
            raise MeasurementPolicyError(f"{kind} must be a HUMAN_HARD_GATE without automation")
    for kind in MEASUREMENT_TYPES:
        entry = measurements[kind]
        if (
            entry.get("algorithmVersion") != ALGORITHMS[kind]
            or entry.get("unit") != UNITS[kind]
            or entry.get("operator") != OPERATORS[kind]
            or not isinstance(entry.get("threshold"), (int, float))
            or isinstance(entry.get("threshold"), bool)
            or not math.isfinite(float(entry["threshold"]))
        ):
            raise MeasurementPolicyError(f"{kind} definition is not implemented by this runtime")
    return dict(policy)


def compare(value: float | None, operator: str, threshold: float) -> bool:
    if value is None:
        return False
    if operator == ">=":
        return value >= threshold
    if operator == "==":
        return value == threshold
    raise MeasurementPolicyError(f"unsupported operator {operator}")


def _full_mask(size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("L", size, 255).save(buffer, format="PNG")
    return buffer.getvalue()


def _round(value: float) -> float:
    return round(float(value), ROUND)


def _result(
    kind: str,
    policy: Mapping[str, Any],
    *,
    input_sha256: str,
    face_region_hash: str | None,
    measured: float | None,
    checks: Mapping[str, bool],
    reasons: list[str],
) -> dict[str, Any]:
    entry = policy["measurements"][kind]
    threshold = float(entry["threshold"])
    passed = compare(measured, entry["operator"], threshold) and all(checks.values())
    body = {
        "schemaVersion": RESULT_SCHEMA,
        "measurementType": kind,
        "measurementVersion": entry["algorithmVersion"],
        "inputSha256": input_sha256,
        "faceRegionHash": face_region_hash,
        "measuredValue": None if measured is None else _round(measured),
        "unit": entry["unit"],
        "thresholdOperator": entry["operator"],
        "thresholdValue": threshold,
        "checks": dict(sorted(checks.items())),
        "pass": passed,
        "failureReasons": sorted(set(reasons)),
        "policyId": policy["policyId"],
        "policyVersion": policy["policyVersion"],
        "policyHash": policy["policyHash"],
    }
    body["resultSha256"] = sha256_hex(canonical_json(body))
    return body


def _bbox_crop(image: Image.Image, bbox: Mapping[str, float]) -> np.ndarray:
    import cv2

    left = max(0, int(math.floor(bbox["left"])))
    top = max(0, int(math.floor(bbox["top"])))
    right = min(image.width, int(math.ceil(bbox["right"])))
    bottom = min(image.height, int(math.ceil(bbox["bottom"])))
    crop = np.asarray(image.crop((left, top, right, bottom)).convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    return cv2.resize(gray, (CANONICAL_FACE_CROP, CANONICAL_FACE_CROP), interpolation=cv2.INTER_AREA)


def measure_blur(image: Image.Image, observation: Mapping[str, Any], policy: Mapping[str, Any], input_sha256: str) -> dict[str, Any]:
    import cv2

    bbox = observation.get("bbox")
    if observation.get("faceCount") != 1 or not bbox:
        return _result(BLUR, policy, input_sha256=input_sha256, face_region_hash=None, measured=None,
                       checks={"single_face_region": False}, reasons=["NO_SINGLE_FACE_REGION"])
    gray = _bbox_crop(image, bbox)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F, ksize=3).var())
    return _result(BLUR, policy, input_sha256=input_sha256,
                   face_region_hash=sha256_hex(gray.tobytes()), measured=variance,
                   checks={"single_face_region": True},
                   reasons=[] if compare(variance, OPERATORS[BLUR], float(policy["measurements"][BLUR]["threshold"])) else ["BLUR_BELOW_THRESHOLD"])


def _region_hash(bbox: Mapping[str, float] | None, landmarks: list[Mapping[str, float]]) -> str | None:
    if not bbox:
        return None
    payload = {
        "bbox": {k: round(float(v), 4) for k, v in sorted(bbox.items())},
        "landmarks": [{k: round(float(v), 4) for k, v in sorted(p.items())} for p in landmarks],
    }
    return sha256_hex(canonical_json(payload))


def measure_framing(observation: Mapping[str, Any], policy: Mapping[str, Any], input_sha256: str) -> dict[str, Any]:
    face_count = observation.get("faceCount")
    bbox = observation.get("bbox") if face_count == 1 else None
    height = float(observation["imageHeight"])
    width = float(observation["imageWidth"])
    ratio = None
    centre_inside = False
    if bbox:
        ratio = (bbox["bottom"] - bbox["top"]) / height if height > 0 else None
        cx, cy = (bbox["left"] + bbox["right"]) / 2.0, (bbox["top"] + bbox["bottom"]) / 2.0
        centre_inside = 0 <= cx <= width and 0 <= cy <= height
    checks = {
        "bbox_center_inside_frame": centre_inside,
        "border_not_clipped": observation.get("borderClipped") is False,
        "exactly_one_face": face_count == 1 and bbox is not None,
    }
    reasons = [name.upper() + "_FAILED" for name, ok in checks.items() if not ok]
    if ratio is not None and not compare(ratio, OPERATORS[FRAMING], float(policy["measurements"][FRAMING]["threshold"])):
        reasons.append("FACE_TOO_SMALL")
    return _result(FRAMING, policy, input_sha256=input_sha256, face_region_hash=_region_hash(bbox, list(observation.get("landmarks") or [])),
                   measured=ratio, checks=checks, reasons=reasons)


def measure_identity(image_bytes: bytes, policy: Mapping[str, Any], observer: Observer) -> dict[str, Any]:
    """Measure blur and framing; a frame with no/many faces still yields deterministic FAIL results."""
    policy = load_policy(policy)
    input_sha256 = sha256_hex(image_bytes)
    image = _decode_image(image_bytes)
    observation = observer.observe(image_bytes, _full_mask(image.size)).as_dict()
    results = [
        measure_blur(image, observation, policy, input_sha256),
        measure_framing(observation, policy, input_sha256),
    ]
    body = {
        "schemaVersion": SET_SCHEMA,
        "inputSha256": input_sha256,
        "imageWidth": image.width,
        "imageHeight": image.height,
        "policyId": policy["policyId"],
        "policyVersion": policy["policyVersion"],
        "policyHash": policy["policyHash"],
        "detector": {
            "id": observation["detectorId"],
            "version": observation["detectorVersion"],
            "configSha256": observation["detectorConfigSha256"],
        },
        "faceCount": observation["faceCount"],
        "observabilityStatus": observation["status"],
        "humanGates": list(HUMAN_GATES),
        "results": results,
    }
    body["setSha256"] = sha256_hex(canonical_json(body))
    return body


__all__ = [
    "ALGORITHMS", "BLUR", "FRAMING", "HUMAN_GATES", "HUMAN_HARD_GATE", "MEASUREMENT_TYPES", "OCCLUSION",
    "MeasurementPolicyError",
    "POLICY_ID", "POLICY_SCHEMA", "RESULT_SCHEMA", "SET_SCHEMA", "canonical_json", "compare",
    "load_policy", "measure_identity", "policy_hash", "sha256_hex",
]
