from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping

# THE ONLY SOURCE for every ComfyUI-attached identifier used by the NEW SD1.5
# + IPAdapter FaceID workflow (GW-P3). These strings must never appear
# anywhere else in the repo — use case, domain, CLI, script, or a comment
# used as documentation of truth — enforced by
# tests/identity_restoration/test_no_comfyui_string_leakage.py.
#
# This is exactly the guard against the regression that shipped in v2.1, when
# `model: "gpt-image-2"` was hardcoded straight into route.ts and leaked into
# the manifest (GW-D7, GW-E7).
#
# Scope note: this registry covers the NEW workflow GW-P3 authors for the
# Windows worker. The legacy SDXL/PuLID workflow that ComfyUIIdentityRestorer
# already runs keeps its own binding scheme
# (image_studio_runtime/action_composite/providers.py::DEFAULT_NODE_BINDINGS)
# unchanged — extract, don't recreate (patch v2.1 §2.3); it is not migrated
# into this registry.

NODE_TITLES: Final[Mapping[str, str]] = MappingProxyType({
    "LOAD_CROP": "VENHO_INPUT_CROP",
    "LOAD_MASK": "VENHO_INPUT_MASK",
    "LOAD_A2": "VENHO_INPUT_A2_FRONT",
    "SAMPLER": "VENHO_SAMPLER",
    "SAVE_RESTORED": "VENHO_OUTPUT_RESTORED_CROP",
})


@dataclass(frozen=True)
class WorkflowDescriptor:
    filename: str
    sha256: str
    models: tuple[str, ...]
    min_vram_mb: int


# Populated once GW-P3-T10 authors the workflow in repo and pins its sha256
# into config/projects/venho_hotel/identity_restoration/workflow_pins.yaml.
WORKFLOWS: Final[Mapping[str, WorkflowDescriptor]] = MappingProxyType({
    "face_restore_win_sd15_ipadapter_v1": WorkflowDescriptor(
        filename="face_restore_win_sd15_ipadapter_v1.api.json",
        sha256="<pin after the workflow is authored and stable — see workflows/README.md>",
        models=("sd15_base", "ipadapter_faceid_sd15", "clip_vision_h", "insightface_buffalo_l"),
        min_vram_mb=4200,
    ),
})
