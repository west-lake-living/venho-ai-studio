from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

from PIL import Image

from .geometry import BBoxFaceDetector, FaceDetector, load_image
from .locks import GeometryLock
from .masks import crop_for_identity, hierarchical_face_masks
from .metadata import ReproducibilityMetadata
from .models import ActionCompositeJob, CompositeResult, CompositeState, FaceGeometry, RegionalQC
from .providers import IdentityRestorer
from .regional_score_gateway import RegionalScoreEvidence, RegionalScoreGateway, ValidatorExecutionContext
from .regression_guard import unchanged_outside_mask
from .workflow_v2 import CandidateSelector, RegionalGate, SceneCandidate


class ActionCompositePipeline:
    """POC vertical slice: geometry lock -> local face restore -> regional QC."""

    def __init__(self, detector: FaceDetector | None = None, *, identity_threshold: float = 90.0) -> None:
        self.detector = detector or BBoxFaceDetector()
        self.identity_threshold = identity_threshold

    def run(self, job: ActionCompositeJob, restorer: IdentityRestorer,
            *, output_dir: str | Path, identity_score: Optional[float] = None,
            geometry_score: float | None = None, restorer_config: dict[str, Any] | None = None,
            identity_loader: Callable[[str], bytes] | None = None,
            reproducibility: Optional[ReproducibilityMetadata] = None,
            regional_scores: Optional[Mapping[str, Optional[float]]] = None,
            regional_evidence: Optional[RegionalScoreEvidence] = None,
            regional_score_gateway: Optional[RegionalScoreGateway] = None,
            scene_candidates: Optional[Iterable[SceneCandidate]] = None,
            selected_candidate: Optional[SceneCandidate] = None,
            observed_geometry_extractor: Optional[Callable[[Path], FaceGeometry]] = None,
            observed_geometry_method: str = "face-geometry-extractor-v1",
            validator_context: Optional[ValidatorExecutionContext] = None) -> CompositeResult:
        state = CompositeState.INIT
        base = load_image(job.base_image)
        if scene_candidates is not None:
            selected_candidate = CandidateSelector().select(scene_candidates)
        if selected_candidate is not None and Path(selected_candidate.image_path) != Path(job.base_image):
            raise ValueError("Selected SceneCandidate source must equal the execution base image")
        state = CompositeState.ANALYZE_GEOMETRY
        geometry = self.detector.detect(base, job.face_bbox)
        geometry_lock = GeometryLock(geometry)
        crop, crop_box = crop_for_identity(base, geometry.face_bbox)
        masks = hierarchical_face_masks(base.size, geometry.face_bbox, version=job.mask_version)
        default_mask = masks.shape
        mask_override = (restorer_config or {}).get("effective_mask")
        if mask_override is not None and not isinstance(mask_override, Image.Image):
            raise ValueError("effective_mask must be a PIL image when supplied")
        # Opt-in only: the normal production path remains hierarchical_face_v1.
        mask = mask_override if isinstance(mask_override, Image.Image) else default_mask
        state = CompositeState.RESTORE_FACE
        reference = identity_loader(job.identity_reference) if identity_loader else Path(job.identity_reference).read_bytes()
        reference_sha256 = hashlib.sha256(reference).hexdigest()
        if job.identity_reference_sha256 and reference_sha256 != job.identity_reference_sha256:
            raise ValueError("A2 identity reference hash does not match the job contract")
        restore_options = {
            "crop": crop,
            "crop_box": crop_box.model_dump(),
            "crop_mask": (restorer_config or {}).get(
                "crop_mask", mask.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom))
            ),
            "masks": masks.as_manifest(),
            **(restorer_config or {}),
        }
        restored = restorer.restore(base, reference, mask, geometry.model_dump(), restore_options)
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
        regional_gate = None
        score_sources: dict[str, str] = {}
        score_provenance: dict[str, Any] = {}
        selected_candidate_manifest = selected_candidate.model_dump() if selected_candidate else None
        observed_geometry = None
        if observed_geometry_extractor is not None:
            target_for_observation = Path(output_dir) / "final_composite.png"
            target_for_observation.parent.mkdir(parents=True, exist_ok=True)
            output.save(target_for_observation, format="PNG")
            observed = observed_geometry_extractor(target_for_observation)
            if not isinstance(observed, FaceGeometry):
                raise ValueError("Observed geometry extractor must return FaceGeometry")
            observed_geometry = {"geometry": observed.model_dump(),
                                 "source_artifact": str(target_for_observation),
                                 "extraction_method": observed_geometry_method}
            extractor_provenance = getattr(observed_geometry_extractor, "last_provenance", None)
            if isinstance(extractor_provenance, dict):
                observed_geometry["provenance"] = extractor_provenance
        if regional_evidence is not None:
            updates: dict[str, Any] = {}
            if selected_candidate is not None and regional_evidence.scene_candidate is None:
                updates["scene_candidate"] = selected_candidate
                updates["scene_source_artifacts"] = [selected_candidate.image_path]
            if observed_geometry is not None and regional_evidence.geometry_observed is None:
                updates["geometry_observed"] = FaceGeometry.model_validate(observed_geometry["geometry"])
                updates["geometry_expected"] = geometry
                updates["geometry_source_artifacts"] = [job.base_image, observed_geometry["source_artifact"]]
            if updates:
                regional_evidence = regional_evidence.model_copy(update=updates)
        if regional_evidence is not None:
            if regional_score_gateway is None:
                regional_score_gateway = RegionalScoreGateway()
            regional_result = regional_score_gateway.build(regional_evidence)
            regional_scores = regional_result.scores
            score_sources = regional_result.sources
            score_provenance = regional_result.provenance
        if regional_scores is not None:
            regional_gate = RegionalGate(
                identity=regional_scores.get("identity", identity_score),
                eyes_brows=regional_scores.get("eyes_brows"),
                geometry=regional_scores.get("geometry", geometry_score),
                anatomy=regional_scores.get("anatomy"),
                outfit=regional_scores.get("outfit"),
                environment=regional_scores.get("environment"),
                global_composite=regional_scores.get("global_composite", regional_scores.get("global")),
                pixel_preservation=unchanged,
            )
            gate_passed, gate_failures = regional_gate.evaluate()
            if not gate_passed:
                failures.extend(item for item in gate_failures if item not in failures)
        ledger = {"version": "action_composite_v2.1", "events": []}
        if selected_candidate is not None:
            ledger["events"].append({"state": "SELECT_CANDIDATE",
                                      "candidate_id": selected_candidate.candidate_id,
                                      "source_artifact": selected_candidate.image_path,
                                      "scores": dict(selected_candidate.scores)})
        if regional_scores is not None:
            ledger["events"].append({"state": "REGIONAL_QC", "scores": dict(regional_scores),
                                      "sources": score_sources,
                                      "provenance": score_provenance,
                                      "status": "PASS" if regional_gate and regional_gate.evaluate()[0] else "FAIL"})
        effective_identity_score = identity_score
        if effective_identity_score is None and regional_scores is not None:
            effective_identity_score = regional_scores.get("identity")
        qc = RegionalQC(identity_score=identity_score, geometry_score=geometry_score,
                        eyes_brows_score=(regional_scores or {}).get("eyes_brows"),
                        anatomy_score=(regional_scores or {}).get("anatomy"),
                        outfit_score=(regional_scores or {}).get("outfit"),
                        environment_score=(regional_scores or {}).get("environment"),
                        global_score=(regional_scores or {}).get("global_composite", (regional_scores or {}).get("global")),
                        pixel_preservation=unchanged,
                        status=_qc_status(effective_identity_score, failures),
                        failures=failures)
        state = CompositeState.FINALIZE
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        output_path = target / "image.png"
        output.save(output_path, format="PNG")
        manifest = {"contract_version": "action_composite_v2.1",
                    "job": job.model_dump(),
                    "identity_authority": {"name": "A2-FRONT", "sha256": reference_sha256},
                    "geometry": geometry.model_dump(), "geometry_lock": geometry_lock.as_manifest(),
                    "face_geometry_evidence": {"expected": geometry.model_dump(),
                                                "observed": observed_geometry} if observed_geometry else None,
                    "scene_candidate": selected_candidate_manifest,
                    "validator_context": validator_context.model_dump() if validator_context else None,
                    "mask": {**masks.as_manifest(),
                             "effective_override": (restorer_config or {}).get("mask_metadata")},
                    "regional_gate": regional_gate.model_dump() if regional_gate else None,
                    "regional_scores": {"scores": dict(regional_scores), "sources": score_sources,
                                        "provenance": score_provenance} if regional_scores else None,
                    "workflow_ledger": ledger,
                    "reproducibility": (reproducibility or ReproducibilityMetadata(workflow_version=job.workflow_version)).as_manifest(),
                    "qc": qc.model_dump(),
                    "artifacts": [{"path": "image.png", "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}]}
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return CompositeResult(job_id=job.job_id, state=state, output_path=str(output_path), geometry=geometry, qc=qc,
                               metadata={"crop_bbox": crop_box.model_dump(), "workflow_version": job.workflow_version,
                                         "identity_reference_sha256": reference_sha256,
                                         "mask_version": masks.version,
                                         "regional_scores": dict(regional_scores) if regional_scores else None,
                                         "regional_score_sources": score_sources,
                                         "regional_score_provenance": score_provenance,
                                         "workflow_ledger": ledger,
                                         "scene_candidate": selected_candidate_manifest,
                                         "face_geometry_evidence": {"expected": geometry.model_dump(),
                                                                     "observed": observed_geometry} if observed_geometry else None,
                                         "validator_context": validator_context.model_dump() if validator_context else None})


def _qc_status(identity_score: Optional[float], failures: list[str]) -> str:
    """A failed gate is FAIL, never UNVALIDATED.

    ``identity_score`` is compared against ``None`` and not truthiness: a real
    0.0 identity score is a hard failure, not a missing measurement.
    """
    if failures:
        return "FAIL"
    return "UNVALIDATED" if identity_score is None else "PASS"
