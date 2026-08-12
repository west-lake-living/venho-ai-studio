from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image

from .geometry import BBoxFaceDetector, FaceDetector, load_image
from .locks import GeometryLock
from .masks import crop_for_identity, face_mask
from .metadata import ReproducibilityMetadata
from .models import ActionCompositeJob, CompositeResult, CompositeState, RegionalQC
from .providers import IdentityRestorer
from .regression_guard import unchanged_outside_mask


class ActionCompositePipeline:
    """POC vertical slice: geometry lock -> local face restore -> regional QC."""

    def __init__(self, detector: FaceDetector | None = None, *, identity_threshold: float = 90.0) -> None:
        self.detector = detector or BBoxFaceDetector()
        self.identity_threshold = identity_threshold

    def run(self, job: ActionCompositeJob, restorer: IdentityRestorer,
            *, output_dir: str | Path, identity_score: Optional[float] = None,
            geometry_score: float | None = None, restorer_config: dict[str, Any] | None = None,
            identity_loader: Callable[[str], bytes] | None = None,
            reproducibility: Optional[ReproducibilityMetadata] = None) -> CompositeResult:
        state = CompositeState.INIT
        base = load_image(job.base_image)
        state = CompositeState.ANALYZE_GEOMETRY
        geometry = self.detector.detect(base, job.face_bbox)
        geometry_lock = GeometryLock(geometry)
        crop, crop_box = crop_for_identity(base, geometry.face_bbox)
        mask = face_mask(base.size, geometry.face_bbox)
        state = CompositeState.RESTORE_FACE
        reference = identity_loader(job.identity_reference) if identity_loader else Path(job.identity_reference).read_bytes()
        restored = restorer.restore(base, reference, mask, geometry.model_dump(), {"crop": crop, **(restorer_config or {})})
        if restored.size != base.size:
            raise ValueError("Identity restorer must return an image with the original dimensions")
        state = CompositeState.VALIDATE_FACE
        # Judge the restorer's raw output, not the composite. Compositing already
        # discards everything outside the mask, so checking it would only confirm
        # a tautology while a restorer that regenerated the whole scene — body,
        # hair, Nike top, West Lake — still reported a clean run (plan §18).
        unchanged = unchanged_outside_mask(base, restored, mask)
        output = Image.composite(restored, base, mask)
        failures: list[str] = []
        if not unchanged:
            failures.append("pixel_preservation_failed")
        if identity_score is not None and identity_score < self.identity_threshold:
            failures.append("identity_below_threshold")
        qc = RegionalQC(identity_score=identity_score, geometry_score=geometry_score,
                        pixel_preservation=unchanged,
                        status=_qc_status(identity_score, failures),
                        failures=failures)
        state = CompositeState.FINALIZE
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        output_path = target / "image.png"
        output.save(output_path, format="PNG")
        manifest = {"job": job.model_dump(), "geometry": geometry.model_dump(), "geometry_lock": geometry_lock.as_manifest(),
                    "reproducibility": (reproducibility or ReproducibilityMetadata(workflow_version=job.workflow_version)).as_manifest(),
                    "qc": qc.model_dump(),
                    "artifacts": [{"path": "image.png", "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}]}
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return CompositeResult(job_id=job.job_id, state=state, output_path=str(output_path), geometry=geometry, qc=qc,
                               metadata={"crop_bbox": crop_box.model_dump(), "workflow_version": job.workflow_version})


def _qc_status(identity_score: Optional[float], failures: list[str]) -> str:
    """A failed gate is FAIL, never UNVALIDATED.

    ``identity_score`` is compared against ``None`` and not truthiness: a real
    0.0 identity score is a hard failure, not a missing measurement.
    """
    if failures:
        return "FAIL"
    return "UNVALIDATED" if identity_score is None else "PASS"
