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


@dataclass(frozen=True)
class WorkflowInputSpec:
    """Stable semantic contract for the exported GW-P3 API graph.

    The authoritative Windows API export has no ``_meta.title`` fields. These
    specs therefore provide a fail-closed, content-addressed binding rule for
    that exact graph without changing its bytes or relying on numeric ids
    alone.
    """

    class_type: str
    input_name: str
    sentinel: str | None = None


WORKFLOW_INPUT_SPECS: Final[Mapping[str, WorkflowInputSpec]] = MappingProxyType({
    NODE_TITLES["LOAD_CROP"]: WorkflowInputSpec("LoadImage", "image", "input_crop.png"),
    NODE_TITLES["LOAD_MASK"]: WorkflowInputSpec("LoadImageMask", "image", "current_restoration_mask.png"),
    NODE_TITLES["LOAD_A2"]: WorkflowInputSpec("LoadImage", "image", "A2_Front_plate.png"),
    NODE_TITLES["SAMPLER"]: WorkflowInputSpec("KSampler", "seed"),
    NODE_TITLES["SAVE_RESTORED"]: WorkflowInputSpec("SaveImage", "images"),
})


WORKFLOWS: Final[Mapping[str, WorkflowDescriptor]] = MappingProxyType({
    "face_restore_win_sd15_ipadapter_v1": WorkflowDescriptor(
        filename="face_restore_win_sd15_ipadapter_v1.api.json",
        sha256="7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8",
        models=(
            "v1-5-pruned-emaonly.safetensors",
            "ip-adapter-faceid-plusv2_sd15.bin",
            "ip-adapter-faceid-plusv2_sd15_lora.safetensors",
            "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
            "buffalo_l",
        ),
        min_vram_mb=4200,
    ),
    "face_restore_win_sd15_ipadapter_v2": WorkflowDescriptor(
        filename="face_restore_win_sd15_ipadapter_v2.api.json",
        sha256="1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58",
        models=(
            "v1-5-pruned-emaonly.safetensors",
            "ip-adapter-faceid-plusv2_sd15.bin",
            "ip-adapter-faceid-plusv2_sd15_lora.safetensors",
            "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
            "buffalo_l",
        ),
        min_vram_mb=4200,
    ),
})
