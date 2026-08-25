from __future__ import annotations

import json
from typing import Any, Mapping

from .error_mapper import map_missing_node_title
from .node_registry import NODE_TITLES, WORKFLOW_INPUT_SPECS

# GW-D7: bind by _meta.title, never by numeric node id — ids renumber every
# time the graph is re-saved from the ComfyUI UI; titles are ours to control.


def bind_by_title(workflow: Mapping[str, Any], bindings: Mapping[str, str],
                  *, runtime_values: Mapping[str, Any] | None = None,
                  geometry_values: Mapping[str, int] | None = None) -> dict[str, Any]:
    """``bindings`` maps a node TITLE (from node_registry.NODE_TITLES) to the
    uploaded asset's ``name`` (ComfyUI's own returned name — see http_client.py
    upload_image, GW-E9). Sets ``inputs.image`` on the matching node."""
    prepared: dict[str, Any] = json.loads(json.dumps(workflow))
    titles = {str(node.get("_meta", {}).get("title", "")): node_id
             for node_id, node in prepared.items() if isinstance(node, dict)}
    for title, uploaded_name in bindings.items():
        node_id = titles.get(title) or _find_semantic_node(prepared, title)
        prepared[node_id].setdefault("inputs", {})["image"] = uploaded_name
    if runtime_values:
        _bind_runtime_values(prepared, runtime_values)
    if geometry_values is not None:
        _bind_geometry_values(prepared, geometry_values)
    return prepared


def _find_semantic_node(workflow: Mapping[str, Any], title: str) -> str:
    spec = WORKFLOW_INPUT_SPECS.get(title)
    if spec is None:
        raise map_missing_node_title(title)
    matches = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or node.get("class_type") != spec.class_type:
            continue
        inputs = node.get("inputs", {})
        if spec.sentinel is None or inputs.get(spec.input_name) == spec.sentinel:
            matches.append(str(node_id))
    if len(matches) != 1:
        raise map_missing_node_title(title)
    return matches[0]


def _bind_runtime_values(workflow: Mapping[str, Any], values: Mapping[str, Any]) -> None:
    sampler_id = _find_semantic_node(workflow, NODE_TITLES["SAMPLER"])
    inputs = workflow[sampler_id].setdefault("inputs", {})
    for key in ("seed", "denoise", "steps", "cfg", "sampler_name", "scheduler"):
        if key in values and key in inputs:
            inputs[key] = values[key]


def _bind_geometry_values(workflow: Mapping[str, Any], values: Mapping[str, int]) -> None:
    """Bind request geometry to the versioned dimension-preserving graph.

    The v2 graph deliberately has no meaningful geometry default.  All four
    values are required at request time, and the same pad values are applied
    to the image and mask branches before VAE encoding.
    """
    required = {"padRight", "padBottom", "finalCropWidth", "finalCropHeight"}
    if set(values) != required:
        raise ValueError(f"geometry binding requires exactly {sorted(required)}")
    pad_right = int(values["padRight"])
    pad_bottom = int(values["padBottom"])
    final_width = int(values["finalCropWidth"])
    final_height = int(values["finalCropHeight"])
    if not (0 <= pad_right < 8 and 0 <= pad_bottom < 8 and final_width > 0 and final_height > 0):
        raise ValueError("geometry binding contains invalid dimensions or padding")

    image_pads = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or node.get("class_type") != "ImagePadForOutpaint":
            continue
        source = node.get("inputs", {}).get("image")
        if source == ["2", 0]:
            image_pads.append(node_id)
    mask_pads = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or node.get("class_type") != "ImagePadForOutpaint":
            continue
        source = node.get("inputs", {}).get("image")
        if source == ["15", 0]:
            mask_pads.append(node_id)
    crop_nodes = [node_id for node_id, node in workflow.items()
                  if isinstance(node, dict) and node.get("class_type") == "ImageCrop"]
    if len(image_pads) != 1 or len(mask_pads) != 1 or len(crop_nodes) != 1:
        raise ValueError("dimension-preserving workflow geometry nodes are missing or ambiguous")

    for node_id in (image_pads[0], mask_pads[0]):
        inputs = workflow[node_id].setdefault("inputs", {})
        inputs["right"] = pad_right
        inputs["bottom"] = pad_bottom
    crop_inputs = workflow[crop_nodes[0]].setdefault("inputs", {})
    crop_inputs["x"] = 0
    crop_inputs["y"] = 0
    crop_inputs["width"] = final_width
    crop_inputs["height"] = final_height


def find_node_id_by_title(workflow: Mapping[str, Any], title: str) -> str:
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("_meta", {}).get("title") == title:
            return node_id
    raise map_missing_node_title(title)
