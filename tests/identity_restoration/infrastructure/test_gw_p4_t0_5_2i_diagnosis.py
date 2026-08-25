from __future__ import annotations

import hashlib
import inspect
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.domain.entities import A2Authority, MaskSet, RestorationRequest, RestoredCrop
from identity_restoration.domain.errors import RestorationError
from identity_restoration.domain.value_objects import RestorationParams
from identity_restoration.infrastructure.comfyui.graph_binder import bind_by_title
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient
from identity_restoration.infrastructure.restorers.comfyui_remote_restorer import ComfyUIRemoteRestorer


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v1.api.json"
WORKFLOW_V2 = ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json"
HISTORY = ROOT / "staging/gw-p3/mac-final-20260824/remote_history_response.json"
WORKFLOW_SHA = "7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8"
WORKFLOW_V2_SHA = "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"


def _png(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size, (20, 20, 20))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _request(crop_size: tuple[int, int]) -> RestorationRequest:
    crop = _png(crop_size)
    mask = _png(crop_size)
    return RestorationRequest(
        run_id="diagnosis",
        attempt_id="1",
        crop_png=crop,
        mask=MaskSet(editable=mask, feather=mask, version="test"),
        a2=A2Authority.from_bytes(b"a2"),
        workflow_id="face_restore_win_sd15_ipadapter_v1",
        seed=42,
        params=RestorationParams(denoise=0.35, steps=20, cfg=6, sampler="euler", scheduler="normal"),
    )


def test_frozen_workflow_hash_and_fixed_crop_are_the_dimension_change() -> None:
    workflow = json.loads(WORKFLOW.read_text())
    assert hashlib.sha256(WORKFLOW.read_bytes()).hexdigest() == WORKFLOW_SHA
    assert workflow["16"]["class_type"] == "ImagePadForOutpaint"
    assert workflow["16"]["inputs"]["right"] == 1
    assert workflow["16"]["inputs"]["bottom"] == 5
    assert workflow["19"]["class_type"] == "ImageCrop"
    assert workflow["19"]["inputs"] == {
        "height": 659, "image": ["13", 0], "width": 687, "x": 0, "y": 0,
    }
    assert workflow["14"]["inputs"]["images"] == ["19", 0]
    assert (687, 659) != (830, 1003)


def test_remote_binding_keeps_final_saveimage_output_selection() -> None:
    workflow = json.loads(WORKFLOW.read_text())
    bound = bind_by_title(workflow, {
        "VENHO_INPUT_CROP": "run/crop.png",
        "VENHO_INPUT_MASK": "run/mask.png",
        "VENHO_INPUT_A2_FRONT": "run/a2.png",
    })
    assert bound["2"]["inputs"]["image"] == "run/crop.png"
    assert bound["4"]["inputs"]["image"] == "run/mask.png"
    assert bound["3"]["inputs"]["image"] == "run/a2.png"
    assert bound["14"]["class_type"] == "SaveImage"
    assert bound["14"]["inputs"]["images"] == ["19", 0]

    history = json.loads(HISTORY.read_text())
    item = next(iter(history.values()))
    selected = ComfyUIHttpClient(base_url="http://unused")._first_output(item)
    assert selected == item["outputs"]["14"]["images"][0]


def test_remote_adapter_has_no_posthoc_resize_path() -> None:
    source = inspect.getsource(ComfyUIRemoteRestorer)
    assert ".resize(" not in source


def test_dimension_mismatch_remains_fail_closed_for_arbitrary_nonsquare_crop() -> None:
    request = _request((830, 1003))
    returned = RestoredCrop.from_png_bytes(_png((687, 659)))
    with pytest.raises(RestorationError, match="ERR_GW_GEOMETRY_MISMATCH"):
        returned.assert_geometry_matches(request)


def test_local_legacy_graph_has_no_fixed_remote_output_crop() -> None:
    workflow = json.loads((ROOT / "workflows/_archive/face_restore_v1_api.json").read_text())
    assert not any(node.get("class_type") == "ImageCrop" for node in workflow.values())
    assert workflow["9"]["class_type"] == "SaveImage"
    assert workflow["9"]["inputs"]["images"] == ["8", 0]


@pytest.mark.parametrize(
    ("size", "expected"),
    [((830, 1003), {"padRight": 2, "padBottom": 5, "finalCropWidth": 830, "finalCropHeight": 1003}),
     ((1024, 1024), {"padRight": 0, "padBottom": 0, "finalCropWidth": 1024, "finalCropHeight": 1024}),
     ((687, 659), {"padRight": 1, "padBottom": 5, "finalCropWidth": 687, "finalCropHeight": 659})],
)
def test_v2_binds_dynamic_padding_and_final_crop(size, expected) -> None:
    workflow = json.loads(WORKFLOW_V2.read_text())
    bound = bind_by_title(workflow, {}, geometry_values=expected)
    assert bound["16"]["inputs"]["right"] == expected["padRight"]
    assert bound["16"]["inputs"]["bottom"] == expected["padBottom"]
    assert bound["17"]["inputs"]["right"] == expected["padRight"]
    assert bound["17"]["inputs"]["bottom"] == expected["padBottom"]
    assert bound["19"]["inputs"]["width"] == size[0]
    assert bound["19"]["inputs"]["height"] == size[1]


def test_v2_is_a_new_deterministic_authority_and_contains_no_old_fixed_geometry() -> None:
    assert hashlib.sha256(WORKFLOW.read_bytes()).hexdigest() == WORKFLOW_SHA
    assert hashlib.sha256(WORKFLOW_V2.read_bytes()).hexdigest() == WORKFLOW_V2_SHA
    assert hashlib.sha256(WORKFLOW_V2.read_bytes()).hexdigest() == WORKFLOW_V2_SHA
    assert "687" not in WORKFLOW_V2.read_text()
    assert "659" not in WORKFLOW_V2.read_text()


def test_v2_runtime_geometry_requires_all_fields_and_fails_closed() -> None:
    workflow = json.loads(WORKFLOW_V2.read_text())
    with pytest.raises(ValueError, match="exactly"):
        bind_by_title(workflow, {}, geometry_values={"padRight": 2})
    with pytest.raises(ValueError, match="invalid dimensions"):
        bind_by_title(workflow, {}, geometry_values={
            "padRight": 8, "padBottom": 5,
            "finalCropWidth": 830, "finalCropHeight": 1003,
        })
