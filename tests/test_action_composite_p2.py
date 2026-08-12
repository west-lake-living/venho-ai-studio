from PIL import Image

from image_studio_runtime.action_composite.regression_guard import assert_no_regression, unchanged_outside_mask
from image_studio_runtime.action_composite.selective_repair import SelectiveRepairController
from image_studio_runtime.action_composite.validators import RegionalValidator, ValidationStatus


def test_regional_validator_isolated_identity_gate():
    validator = RegionalValidator()
    results = validator.validate({"identity": 91, "facial_geometry": 94, "outfit": 40})
    assert results["identity"].status == ValidationStatus.PASS
    assert results["outfit"].status == ValidationStatus.PASS
    assert validator.overall_status(results) == ValidationStatus.PASS
    assert validator.validate({"identity": 89})["identity"].status == ValidationStatus.FAIL


def test_missing_score_is_unvalidated():
    result = RegionalValidator().validate({"identity": None})["identity"]
    assert result.status == ValidationStatus.UNVALIDATED


def test_regression_guard_detects_outside_mask_change():
    before = Image.new("RGB", (4, 4), "black")
    after = before.copy()
    after.putpixel((0, 0), (255, 0, 0))
    mask = Image.new("L", (4, 4), 0)
    assert not unchanged_outside_mask(before, after, mask)
    try:
        assert_no_regression(before, after, mask)
    except ValueError as exc:
        assert "outside repair mask" in str(exc)
    else:
        raise AssertionError("guard must reject an outside-mask mutation")


def test_selective_repair_routes_and_caps_retries():
    controller = SelectiveRepairController(retry_caps={"face": 2, "boundary": 1, "region": 3, "scene": 3})
    assert controller.choose(["identity"])[0].repair_type == "face"
    assert controller.choose(["facial_geometry"])[0].allowed
    assert not controller.choose(["identity"])[0].allowed
    assert controller.choose(["boundary_seam"])[0].allowed
    assert not controller.choose(["boundary_seam"])[0].allowed
