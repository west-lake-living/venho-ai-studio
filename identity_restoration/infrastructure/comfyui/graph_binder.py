from __future__ import annotations

import json
from typing import Any, Mapping

from .error_mapper import map_missing_node_title

# GW-D7: bind by _meta.title, never by numeric node id — ids renumber every
# time the graph is re-saved from the ComfyUI UI; titles are ours to control.


def bind_by_title(workflow: Mapping[str, Any], bindings: Mapping[str, str]) -> dict[str, Any]:
    """``bindings`` maps a node TITLE (from node_registry.NODE_TITLES) to the
    uploaded asset's ``name`` (ComfyUI's own returned name — see http_client.py
    upload_image, GW-E9). Sets ``inputs.image`` on the matching node."""
    prepared: dict[str, Any] = json.loads(json.dumps(workflow))
    titles = {str(node.get("_meta", {}).get("title", "")): node_id
             for node_id, node in prepared.items() if isinstance(node, dict)}
    for title, uploaded_name in bindings.items():
        node_id = titles.get(title)
        if node_id is None:
            raise map_missing_node_title(title)
        prepared[node_id].setdefault("inputs", {})["image"] = uploaded_name
    return prepared


def find_node_id_by_title(workflow: Mapping[str, Any], title: str) -> str:
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("_meta", {}).get("title") == title:
            return node_id
    raise map_missing_node_title(title)
