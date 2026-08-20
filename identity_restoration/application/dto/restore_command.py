from __future__ import annotations

from dataclasses import dataclass

from ...domain.entities import CropTransform, MaskSet
from ...domain.value_objects import RestorationParams, RestorerId


@dataclass(frozen=True)
class RestoreCommand:
    """Mirrors contracts/restoration_request.schema.json (contractVersion 1.0)."""

    run_id: str
    attempt_id: str
    restorer_id: RestorerId
    crop_png: bytes
    mask: MaskSet
    base_canvas_png: bytes
    crop_transform: CropTransform
    a2_path: str
    a2_sha256: str
    workflow_id: str
    seed: int
    params: RestorationParams
    timeout_seconds: int = 600
