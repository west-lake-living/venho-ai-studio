"""Identity Measurement Authority R1: contract, determinism, and calibration on A2/B01."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application import identity_measurement as im
from identity_restoration.application.face_observability import FaceDetection
from identity_restoration.application.identity_measurement_fixtures import (
    calibrate,
    pixel_sha256,
)

REPO = Path(__file__).resolve().parents[3]
A2 = REPO / "assets/linh_an/A2_Front.png"
B01_MANIFEST = REPO / "artifacts/identity-restoration/benchmark-geometry/v2.1/B01/geometry_manifest.json"


def _policy(**overrides: object) -> dict:
    """The Human-approved v1.1 numbers (blur 70 / framing 0.08, occlusion = human gate) for tests."""
    policy = {
        "schemaVersion": im.POLICY_SCHEMA, "policyId": im.POLICY_ID, "policyVersion": "1.1",
        "measurements": {
            "BLUR": {"algorithmVersion": im.ALGORITHMS["BLUR"], "unit": "variance_px2", "operator": ">=", "threshold": 70.0},
            "FRAMING": {"algorithmVersion": im.ALGORITHMS["FRAMING"], "unit": "ratio", "operator": ">=", "threshold": 0.08},
        },
        "humanGates": {"OCCLUSION": {"authority": im.HUMAN_HARD_GATE, "automatedMeasurement": False}},
    }
    policy.update(overrides)
    policy["policyHash"] = im.policy_hash(policy)
    return policy


class _Obs:
    def __init__(self, data: dict) -> None:
        self.data = data

    def as_dict(self) -> dict:
        return self.data


class _Observer:
    """Returns a scripted observation for whatever image it is given."""

    def __init__(self, faces: list[FaceDetection], size: tuple[int, int]) -> None:
        self.faces, self.size = faces, size

    def observe(self, image_bytes: bytes, mask: bytes) -> _Obs:
        w, h = self.size
        one = len(self.faces) == 1
        face = self.faces[0] if one else None
        left, top, right, bottom = face.bbox if face else (0, 0, 0, 0)
        return _Obs({
            "imageWidth": w, "imageHeight": h, "faceCount": len(self.faces),
            "bbox": {"left": left, "top": top, "right": right, "bottom": bottom} if face else None,
            "landmarks": [{"x": x, "y": y} for x, y in face.landmarks] if face else [],
            "borderClipped": (left <= 0 or top <= 0 or right >= w or bottom >= h) if face else None,
            "status": "VALID" if one else "AMBIGUOUS", "detectorId": "d", "detectorVersion": "1",
            "detectorConfigSha256": "0" * 64,
        })


def _png(size: tuple[int, int] = (200, 200), noise: bool = True) -> bytes:
    import numpy as np

    rng = np.random.default_rng(7)
    array = rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8) if noise else np.full((size[1], size[0], 3), 128, np.uint8)
    buffer = BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()


def _face(bbox=(50.0, 40.0, 150.0, 160.0)) -> FaceDetection:
    l, t, r, b = bbox
    marks = ((l + 25, t + 40), (r - 25, t + 40), ((l + r) / 2, t + 65), (l + 30, b - 25), (r - 30, b - 25))
    return FaceDetection(confidence=0.95, bbox=bbox, landmarks=marks)


def test_policy_hash_binds_payload_and_unimplemented_algorithms_are_refused() -> None:
    policy = _policy()
    assert im.load_policy(policy)["policyHash"] == im.policy_hash(policy)
    tampered = json.loads(json.dumps(policy))
    tampered["measurements"]["BLUR"]["threshold"] = 10.0  # hash not recomputed
    with pytest.raises(im.MeasurementPolicyError, match="hash"):
        im.load_policy(tampered)
    other = json.loads(json.dumps(policy))
    other["measurements"]["FRAMING"]["algorithmVersion"] = "bbox-visibility-v2"
    other["policyHash"] = im.policy_hash(other)
    with pytest.raises(im.MeasurementPolicyError, match="not implemented"):
        im.load_policy(other)
    automated = json.loads(json.dumps(policy))
    automated["measurements"]["OCCLUSION"] = {"algorithmVersion": "OCCLUSION_PROXY_V1", "unit": "ratio", "operator": "==", "threshold": 1.0}
    automated["policyHash"] = im.policy_hash(automated)
    with pytest.raises(im.MeasurementPolicyError):  # occlusion may not be re-automated by a policy edit
        im.load_policy(automated)
    no_gate = {k: v for k, v in policy.items() if k != "humanGates"}
    no_gate["policyHash"] = im.policy_hash(no_gate)
    with pytest.raises(im.MeasurementPolicyError, match="human gate"):
        im.load_policy(no_gate)
    missing = {k: v for k, v in policy.items() if k != "measurements"}
    missing["policyHash"] = im.policy_hash(missing)
    with pytest.raises(im.MeasurementPolicyError):
        im.load_policy(missing)


def test_three_results_are_canonical_replayable_and_bound_to_bytes_and_policy() -> None:
    data, observer = _png(), _Observer([_face()], (200, 200))
    first = im.measure_identity(data, _policy(), observer)
    again = im.measure_identity(data, _policy(), observer)
    assert first == again and first["setSha256"] == again["setSha256"]
    assert [r["measurementType"] for r in first["results"]] == ["BLUR", "FRAMING"]
    assert first["humanGates"] == ["OCCLUSION"]  # declared, never measured: no OCCLUSION result exists
    for result in first["results"]:
        assert set(result) >= {"measurementVersion", "inputSha256", "faceRegionHash", "measuredValue", "unit",
                               "thresholdOperator", "thresholdValue", "pass", "policyHash", "resultSha256"}
        body = {k: v for k, v in result.items() if k != "resultSha256"}
        assert result["resultSha256"] == im.sha256_hex(im.canonical_json(body))
        assert result["policyHash"] == _policy()["policyHash"]
    assert "/" not in json.dumps(first)  # no path anywhere in canonical evidence

    changed = im.measure_identity(_png(noise=False), _policy(), observer)
    assert changed["inputSha256"] != first["inputSha256"] and changed["setSha256"] != first["setSha256"]
    stricter = _policy(policyVersion="1.2")
    new_policy = im.measure_identity(data, stricter, observer)
    assert new_policy["policyHash"] != first["policyHash"] and new_policy["setSha256"] != first["setSha256"]


def test_pass_is_derived_from_value_operator_threshold_and_checks() -> None:
    sharp = im.measure_identity(_png(), _policy(), _Observer([_face()], (200, 200)))
    assert all(r["pass"] for r in sharp["results"])
    flat = im.measure_identity(_png(noise=False), _policy(), _Observer([_face()], (200, 200)))
    blur = flat["results"][0]
    assert blur["measuredValue"] == 0.0 and blur["pass"] is False and "BLUR_BELOW_THRESHOLD" in blur["failureReasons"]


def test_no_face_and_many_faces_fail_closed_with_deterministic_results() -> None:
    for faces in ([], [_face(), _face((10.0, 10.0, 60.0, 80.0))]):
        out = im.measure_identity(_png(), _policy(), _Observer(faces, (200, 200)))
        assert not any(r["pass"] for r in out["results"])
        assert out["results"][1]["checks"]["exactly_one_face"] is False


def test_framing_rules_small_face_border_clip_and_off_centre_is_allowed() -> None:
    small = im.measure_identity(_png((200, 1000)), _policy(), _Observer([_face((80.0, 400.0, 130.0, 460.0))], (200, 1000)))
    assert small["results"][1]["pass"] is False and "FACE_TOO_SMALL" in small["results"][1]["failureReasons"]
    clipped = im.measure_identity(_png(), _policy(), _Observer([_face((0.0, 40.0, 100.0, 160.0))], (200, 200)))
    assert clipped["results"][1]["checks"]["border_not_clipped"] is False
    corner = im.measure_identity(_png(), _policy(), _Observer([_face((100.0, 60.0, 190.0, 190.0))], (200, 200)))
    assert corner["results"][1]["pass"] is True  # not centred, large enough, not clipped


# ── real detector, real A2 / B01 ──
def _real_setup():
    pytest.importorskip("cv2")
    from identity_restoration.infrastructure.face_observability_yunet import (
        create_pinned_yunet_observability_service,
    )

    if not A2.is_file() or not B01_MANIFEST.is_file():
        pytest.skip("A2 / B01 authority frames are not present")
    b01 = Path(json.loads(B01_MANIFEST.read_text())["sourceB01Path"])
    if not b01.is_file():
        pytest.skip("B01 source frame not present on this machine")
    return Image.open(A2), Image.open(b01), create_pinned_yunet_observability_service()


def test_calibration_positives_pass_and_blur_and_framing_negatives_fail() -> None:
    a2, b01, observer = _real_setup()
    report = calibrate(a2, b01, observer, _policy())
    rows = {row["id"]: row for row in report["fixtures"]}
    for name in ("A2", "B01", "A2_blur_sigma_2"):
        assert all(v["pass"] for v in rows[name]["results"].values()), name
    for name in ("A2_blur_sigma_4", "A2_blur_sigma_8", "A2_blur_sigma_12"):
        assert rows[name]["results"]["BLUR"]["pass"] is False, name
    for name in ("A2_face_below_8pct", "A2_face_cut_at_edge", "A2_B01_two_faces"):
        assert rows[name]["results"]["FRAMING"]["pass"] is False, name
    assert "FACE_TOO_SMALL" in rows["A2_face_below_8pct"]["results"]["FRAMING"]["reasons"]
    assert rows["A2_B01_two_faces"]["faceCount"] == 2
    # Replay: identical fixture pixels and identical outcomes.
    again = calibrate(a2, b01, observer, _policy())
    assert [r["pixelSha256"] for r in again["fixtures"]] == [r["pixelSha256"] for r in report["fixtures"]]
    assert pixel_sha256(a2) == rows["A2"]["pixelSha256"]
