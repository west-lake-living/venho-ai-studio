from __future__ import annotations

import pytest

from identity_restoration.domain.errors import RestorationError
from identity_restoration.infrastructure.comfyui.graph_binder import bind_by_title


def test_graph_binder_survives_node_id_renumbering() -> None:
    """Bind by title, not by node id — ids renumber every time ComfyUI's UI
    re-saves a graph (v2.0 PHẦN 12.3 #7)."""
    workflow_v1 = {"3": {"_meta": {"title": "VENHO_INPUT_CROP"}, "inputs": {}}}
    workflow_v2_renumbered = {"17": {"_meta": {"title": "VENHO_INPUT_CROP"}, "inputs": {}}}

    bound_v1 = bind_by_title(workflow_v1, {"VENHO_INPUT_CROP": "crop_abc.png"})
    bound_v2 = bind_by_title(workflow_v2_renumbered, {"VENHO_INPUT_CROP": "crop_abc.png"})

    assert bound_v1["3"]["inputs"]["image"] == "crop_abc.png"
    assert bound_v2["17"]["inputs"]["image"] == "crop_abc.png"


def test_graph_binder_raises_structured_error_when_title_missing() -> None:
    workflow = {"1": {"_meta": {"title": "SOMETHING_ELSE"}, "inputs": {}}}
    with pytest.raises(RestorationError) as exc_info:
        bind_by_title(workflow, {"VENHO_INPUT_CROP": "crop.png"})
    assert exc_info.value.code == "ERR_GW_NODE_BINDING_FAILED"


def test_graph_binder_does_not_mutate_input_workflow() -> None:
    workflow = {"1": {"_meta": {"title": "VENHO_INPUT_CROP"}, "inputs": {}}}
    bind_by_title(workflow, {"VENHO_INPUT_CROP": "crop.png"})
    assert workflow["1"]["inputs"] == {}
