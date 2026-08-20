from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..application.dto.restore_command import RestoreCommand
from ..application.dto.restoration_result import RestorationResult
from ..domain.entities import CropTransform, MaskSet
from ..domain.value_objects import RestorationParams

# stdin/stdout contract for venho-os (GW-D3: subprocess + JSON, same pattern
# as the existing generate_image.py / validate_generated.py bridge). This is
# the shape contracts/restoration_request.schema.json §5.1 abbreviates —
# baseCanvas/mask/cropBox fields are spelled out fully here because the use
# case needs them to composite back into the canvas; see
# contracts/identity_restoration/restoration_request.schema.json (own
# subdirectory — Growth Phase 1's contracts/*.schema.json registry test
# enumerates the flat contracts/ directory by an explicit whitelist, so this
# bounded context's schemas live one level down, not mixed into it) for the
# authoritative, versioned shape.


def parse_restore_command(payload: dict[str, Any]) -> RestoreCommand:
    box = payload["cropBox"]
    transform = CropTransform.from_box(
        left=int(box["left"]), top=int(box["top"]), right=int(box["right"]), bottom=int(box["bottom"]),
        target_size=int(box.get("targetSize", box["right"] - box["left"])),
    )
    params = payload["params"]
    mask = MaskSet(
        editable=Path(payload["maskEditablePath"]).read_bytes(),
        feather=Path(payload.get("maskFeatherPath", payload["maskEditablePath"])).read_bytes(),
        version=payload.get("maskVersion", "hierarchical_face_v1"),
    )
    return RestoreCommand(
        run_id=payload["runId"],
        attempt_id=payload["attemptId"],
        restorer_id=payload["restorerId"],
        crop_png=Path(payload["cropPath"]).read_bytes(),
        mask=mask,
        base_canvas_png=Path(payload["basePath"]).read_bytes(),
        crop_transform=transform,
        a2_path=payload["a2Path"],
        a2_sha256=payload["a2Sha256"],
        workflow_id=payload["workflowId"],
        seed=int(payload["seed"]),
        params=RestorationParams(**params),
        timeout_seconds=int(payload.get("timeoutSeconds", 600)),
    )


def load_restore_command(path: Path) -> RestoreCommand:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_restore_command(payload)


def dump_result(result: RestorationResult) -> str:
    """Sanitized stdout payload. Never include a raw stack trace or the
    contents of an env var (2026-07-17 OPENAI_API_KEY stdout leak)."""
    return json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2)
