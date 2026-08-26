from __future__ import annotations

"""Composition-only orchestration for the official GW-P4 benchmark.

The module joins existing branch executors with the production geometry
functions and Validator Studio.  It contains no provider, ComfyUI, or QC
implementation of its own.
"""

import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image

from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.masks import crop_for_identity, hierarchical_face_masks
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate
from image_studio_runtime.action_composite.regional_score_gateway import (
    RegionalScoreBlocked,
    RegionalScoreEvidence,
    RegionalScoreGateway,
    StagePreservationEvidenceAdapter,
)
from image_studio_runtime.action_composite.models import FaceGeometry
from validator_studio.schemas.validation_base import ValidationReport
from validator_studio.schemas.face_validation import FaceValidationObservation
from validator_studio.schemas.image_validation import ImageObservation
from validator_studio.face_validator import report_from_face_observations
from validator_studio.image_validator import report_from_image_observations
from validator_studio.observe_adapter import observe_image_against_dna
from validator_studio.utils import load_json, find_dna_path
from shared.vision.structured import extract_json
from shared.vision.paid_call_guard import paid_call_context

from .benchmark_contract import (
    EXPECTED_A2_SHA256,
    EXPECTED_BRANCHES,
    EXPECTED_REMOTE_PARAMS,
    EXPECTED_WORKFLOW_ID,
    EXPECTED_WORKFLOW_SHA256,
)
from .benchmark_executor import (
    BenchmarkExecutionError,
    ControlBenchmarkExecutor,
    NanoBananaEditBenchmarkExecutor,
    NanoBananaEditRequest,
    ComfyUIRemoteBenchmarkExecutor,
)
from .benchmark_runner import BenchmarkExecutor, ValidatorEvidenceError
from .dto.restore_command import RestoreCommand
from ..domain.entities import CropTransform, MaskSet
from ..domain.policies.pixel_preservation import assert_pixels_preserved
from ..domain.value_objects import RestorationParams


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _scenario_profile_id(case: Mapping[str, Any]) -> str | None:
    """Read an explicit benchmark authority mapping; never infer a scenario."""
    authority = case.get("identityRestorationAuthority")
    if authority is None:
        return None
    if not isinstance(authority, Mapping):
        raise BenchmarkExecutionError("identityRestorationAuthority must be a mapping")
    profile = authority.get("scenarioProfileId")
    if not isinstance(profile, str) or not profile:
        raise BenchmarkExecutionError("identityRestorationAuthority.scenarioProfileId is required")
    return profile


@dataclass(frozen=True)
class BenchmarkCaseContext:
    case: Mapping[str, Any]
    base_path: Path
    base_sha256: str
    base_bytes: bytes
    a2_path: Path
    geometry_path: Path
    crop_path: Path
    crop_mask_path: Path
    full_mask_path: Path
    crop_transform: CropTransform
    mask_version: str
    geometry_backend: str
    geometry_model: str
    geometry_model_sha256: str

    def remote_command(self, run_id: str, attempt_id: str, seed: int) -> RestoreCommand:
        crop = self.crop_path.read_bytes()
        crop_mask = self.crop_mask_path.read_bytes()
        full_mask = self.full_mask_path.read_bytes()
        return RestoreCommand(
            run_id=run_id,
            attempt_id=attempt_id,
            restorer_id="comfyui-remote",
            crop_png=crop,
            mask=MaskSet(editable=crop_mask, feather=crop_mask, version=self.mask_version),
            full_canvas_mask=MaskSet(
                editable=full_mask, feather=full_mask,
                version=f"{self.mask_version}_full_canvas",
            ),
            base_canvas_png=self.base_bytes,
            crop_transform=self.crop_transform,
            a2_path=str(self.a2_path),
            a2_sha256=EXPECTED_A2_SHA256,
            workflow_id=EXPECTED_WORKFLOW_ID,
            seed=seed,
            params=RestorationParams(
                denoise=float(EXPECTED_REMOTE_PARAMS["denoise"]),
                steps=int(EXPECTED_REMOTE_PARAMS["steps"]),
                cfg=float(EXPECTED_REMOTE_PARAMS["cfg"]),
                sampler=str(EXPECTED_REMOTE_PARAMS["sampler"]),
                scheduler=str(EXPECTED_REMOTE_PARAMS["scheduler"]),
            ),
            geometry_backend=self.geometry_backend,
            geometry_model=self.geometry_model,
            geometry_model_sha256=self.geometry_model_sha256,
        )

    def nano_request(self, run_id: str, attempt_id: str, seed: int) -> NanoBananaEditRequest:
        return NanoBananaEditRequest(
            base_path=self.base_path,
            a2_path=self.a2_path,
            mask_path=self.full_mask_path,
            crop_transform={
                "left": self.crop_transform.source_x,
                "top": self.crop_transform.source_y,
                "right": self.crop_transform.source_x + self.crop_transform.source_w,
                "bottom": self.crop_transform.source_y + self.crop_transform.source_h,
                "targetSize": self.crop_transform.target_size,
            },
            mask_version=self.mask_version,
            seed_supported=False,
            operation="masked_edit",
            geometry_authority_path=self.geometry_path,
            lineage={
                "geometryAuthorityPath": str(self.geometry_path),
                "geometryAuthoritySha256": _sha(self.geometry_path),
                "cropLocalMaskPath": str(self.crop_mask_path),
                "cropLocalMaskSha256": _sha(self.crop_mask_path),
                "fullCanvasMaskPath": str(self.full_mask_path),
                "fullCanvasMaskSha256": _sha(self.full_mask_path),
                "runId": run_id,
                "attemptId": attempt_id,
                "seed": seed,
            },
        )


class BenchmarkCaseContextFactory:
    """Resolve and persist one immutable geometry authority per frozen case."""

    def __init__(
        self,
        *,
        repo_root: Path,
        canonical_a2_path: Path,
        geometry_backend: str = "yunet",
        geometry_root: Path | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.canonical_a2_path = canonical_a2_path
        self.geometry_backend = geometry_backend
        self.geometry_root = geometry_root or (
            repo_root / "artifacts/identity-restoration/benchmark-geometry/v2.1"
        )
        self._cache: dict[str, BenchmarkCaseContext] = {}

    def build(self, case: Mapping[str, Any]) -> BenchmarkCaseContext:
        case_id = str(case.get("id"))
        if case_id in self._cache:
            return self._cache[case_id]
        if case.get("status") != "FROZEN":
            raise BenchmarkExecutionError(f"case {case_id} is not FROZEN")
        frame = case.get("baseFrame")
        if not isinstance(frame, Mapping):
            raise BenchmarkExecutionError(f"{case_id} has no authoritative baseFrame")
        base_path = Path(str(frame.get("path", "")))
        if not base_path.is_absolute():
            base_path = self.repo_root / base_path
        if not base_path.is_file():
            raise BenchmarkExecutionError(f"{case_id} base frame is missing: {base_path}")
        base_bytes = base_path.read_bytes()
        base_sha = _sha_bytes(base_bytes)
        if base_sha != frame.get("sha256"):
            raise BenchmarkExecutionError(f"{case_id} base frame SHA-256 mismatch")
        with Image.open(BytesIO(base_bytes)) as image:
            base = image.convert("RGBA")
            expected_size = (int(frame.get("width")), int(frame.get("height")))
        if base.size != expected_size:
            raise BenchmarkExecutionError(f"{case_id} base dimensions mismatch")
        if not self.canonical_a2_path.is_file() or _sha(self.canonical_a2_path) != EXPECTED_A2_SHA256:
            raise BenchmarkExecutionError("canonical A2 authority is missing or has the wrong SHA-256")

        authority_record = case.get("geometryAuthority")
        authority_path = None
        if isinstance(authority_record, Mapping) and authority_record.get("path"):
            authority_path = Path(str(authority_record["path"]))
            if not authority_path.is_absolute():
                authority_path = self.repo_root / authority_path
        if authority_path is None:
            authority_path = self.geometry_root / case_id / "geometry_manifest.json"

        if authority_path.is_file():
            authority = json.loads(authority_path.read_text(encoding="utf-8"))
            if authority.get("sourceB01Sha256", authority.get("sourceSha256")) != base_sha:
                raise BenchmarkExecutionError(f"{case_id} geometry authority source SHA mismatch")
        else:
            authority = self._derive(case_id, base_path, base, base_sha, authority_path)

        full_meta = authority.get("fullCanvasMask")
        crop_meta = authority.get("cropLocalMask")
        transform = authority.get("cropTransform")
        if not isinstance(full_meta, Mapping) or not isinstance(crop_meta, Mapping) or not isinstance(transform, Mapping):
            raise BenchmarkExecutionError(f"{case_id} geometry authority is incomplete")
        full_path = self._artifact_path(authority_path, full_meta.get("path"))
        crop_mask_path = self._artifact_path(authority_path, crop_meta.get("path"))
        crop_path_value = authority.get("cropPath")
        crop_path = self._artifact_path(authority_path, crop_path_value) if crop_path_value else None
        if crop_path is None:
            left, top, right, bottom = (int(transform[k]) for k in ("left", "top", "right", "bottom"))
            crop_path = authority_path.parent / "crop.png"
            if not crop_path.is_file():
                base.crop((left, top, right, bottom)).save(crop_path, format="PNG")
        self._verify_artifact(full_path, full_meta, base.size)
        left, top, right, bottom = (int(transform[k]) for k in ("left", "top", "right", "bottom"))
        crop_size = (right - left, bottom - top)
        self._verify_artifact(crop_mask_path, crop_meta, crop_size)
        if _sha(crop_path) != authority.get("cropSha256", _sha(crop_path)):
            raise BenchmarkExecutionError(f"{case_id} crop authority SHA mismatch")
        context = BenchmarkCaseContext(
            case=case, base_path=base_path, base_sha256=base_sha, base_bytes=base_bytes,
            a2_path=self.canonical_a2_path, geometry_path=authority_path,
            crop_path=crop_path, crop_mask_path=crop_mask_path, full_mask_path=full_path,
            crop_transform=CropTransform.from_box(left, top, right, bottom, int(transform["targetSize"])),
            mask_version=str(authority.get("maskVersion", "hierarchical_face_v1")),
            geometry_backend=str(authority.get("geometryBackend", "yunet")),
            geometry_model=str(authority.get("geometryModel", "face_detection_yunet_2023mar.onnx")),
            geometry_model_sha256=str(authority.get("geometryModelSha256", "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4")),
        )
        self._cache[case_id] = context
        return context

    def _derive(self, case_id: str, base_path: Path, base: Image.Image, base_sha: str, authority_path: Path) -> dict[str, Any]:
        if self.geometry_backend != "yunet":
            raise BenchmarkExecutionError("official benchmark geometry backend must be yunet")
        extractor = create_geometry_extractor("yunet")
        geometry = extractor(base_path)
        provenance = getattr(extractor, "last_provenance", None)
        if not isinstance(provenance, Mapping):
            raise BenchmarkExecutionError(f"{case_id} geometry provenance is missing")
        crop, crop_box = crop_for_identity(base, geometry.face_bbox)
        masks = hierarchical_face_masks(base.size, geometry.face_bbox, version="hierarchical_face_v1")
        root = authority_path.parent
        root.mkdir(parents=True, exist_ok=True)
        crop_path = root / "crop.png"
        crop_mask_path = root / "crop_local_mask.png"
        full_mask_path = root / "full_canvas_mask.png"
        crop.save(crop_path, format="PNG")
        masks.shape.crop((crop_box.left, crop_box.top, crop_box.right, crop_box.bottom)).convert("L").save(crop_mask_path, format="PNG")
        masks.shape.convert("L").save(full_mask_path, format="PNG")
        payload = {
            "version": "benchmark-geometry-v2.1", "caseId": case_id,
            "sourceSha256": base_sha, "sourcePath": str(base_path),
            "sourceDimensions": {"width": base.width, "height": base.height},
            "a2AuthoritySha256": EXPECTED_A2_SHA256,
            "geometryBackend": "yunet", "geometryModel": extractor.model_name,
            "geometryModelSha256": extractor.expected_model_sha256,
            "geometry": geometry.model_dump(), "geometryProvenance": dict(provenance),
            "cropPath": str(crop_path), "cropSha256": _sha(crop_path),
            "cropTransform": {"left": crop_box.left, "top": crop_box.top, "right": crop_box.right, "bottom": crop_box.bottom, "targetSize": crop.width},
            "cropSize": {"width": crop.width, "height": crop.height},
            "maskVersion": masks.version,
            "cropLocalMask": {"path": str(crop_mask_path), "sha256": _sha(crop_mask_path), "coordinateSpace": "crop-local"},
            "fullCanvasMask": {"path": str(full_mask_path), "sha256": _sha(full_mask_path), "coordinateSpace": "full-canvas"},
            "lineage": "YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks",
        }
        authority_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    @staticmethod
    def _artifact_path(authority_path: Path, value: Any) -> Path:
        if not isinstance(value, str) or not value:
            raise BenchmarkExecutionError("geometry authority artifact path is missing")
        path = Path(value)
        if path.is_absolute():
            return path
        candidates = [Path.cwd() / path, authority_path.parent / path]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]

    @staticmethod
    def _verify_artifact(path: Path, metadata: Mapping[str, Any], expected_size: tuple[int, int]) -> None:
        if not path.is_file() or _sha(path) != metadata.get("sha256"):
            raise BenchmarkExecutionError(f"geometry artifact is missing or hash-mismatched: {path}")
        with Image.open(path) as image:
            if image.size != expected_size:
                raise BenchmarkExecutionError(f"geometry artifact dimensions mismatch: {path}")


@dataclass
class ValidatorEvidenceCache:
    root: Path
    adapter: "BenchmarkValidatorAdapter"

    def evaluate(self, image_path: Path, *, role: str, context: BenchmarkCaseContext) -> dict[str, Any]:
        image_sha = _sha(image_path)
        key = f"{image_sha}-{self.adapter.identity}"
        path = self.root / f"{key}.json"
        if not path.is_file():
            # Migrate the prior cache-key format when the payload itself
            # proves the same image and three-sample Validator contract.  No
            # validator call is made during this migration.
            for legacy_path in sorted(self.root.glob(f"{image_sha}-*.json")):
                try:
                    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if (
                    legacy.get("imageSha256") == image_sha
                    and str(legacy.get("validator", "")).startswith("validator-studio-face-image-v1:")
                    and legacy.get("samples") == self.adapter.samples
                ):
                    legacy["validator"] = self.adapter.identity
                    legacy["cacheIdentity"] = self.adapter.identity
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(legacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    return legacy
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("imageSha256") == image_sha and (
                payload.get("validator") == self.adapter.identity
                and payload.get("samples") == self.adapter.samples
                or "validator" not in payload
                or (
                    str(payload.get("validator", "")).startswith("validator-studio-face-image-v1:")
                    and payload.get("samples") == self.adapter.samples
                )
            ):
                # Migrate older cache records in place only after their image
                # SHA is verified.  New records always carry the full cache
                # identity; this compatibility path is for pre-v2 fixtures
                # and the already-produced valid QC evidence.
                payload.setdefault("imageSha256", image_sha)
                payload["validator"] = self.adapter.identity
                payload["samples"] = self.adapter.samples
                payload["cacheIdentity"] = self.adapter.identity
                path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                return payload
        payload = self.adapter.evaluate(image_path, role=role, context=context)
        payload.setdefault("imageSha256", image_sha)
        payload.setdefault("validator", self.adapter.identity)
        payload.setdefault("samples", self.adapter.samples)
        payload["cacheIdentity"] = self.adapter.identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload


class BenchmarkValidatorAdapter:
    """Thin adapter over the existing Validator Studio entry points."""

    def __init__(self, *, provider: str = "gemini", samples: int = 3, project: str = "venho_hotel", subject: str = "linh_an", repo_root: Path | None = None, raw_root: Path | None = None) -> None:
        self.provider = provider
        self.samples = samples
        self.project = project
        self.subject = subject
        self.raw_root = raw_root
        self.identity = f"validator-studio-face-image-v1:{provider}:rubric=07F:samples={samples}"
        self._load_existing_production_credentials(repo_root or Path.cwd())

    @staticmethod
    def _load_existing_production_credentials(repo_root: Path) -> None:
        """Use the same dotenv search order as the existing production tools."""
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            return
        try:
            from dotenv import load_dotenv
        except ImportError:
            return
        social_root = repo_root.parent.parent / "venho-social-content-agent"
        for path in (social_root / ".env.local", social_root / ".env", repo_root / ".env.local", repo_root / ".env"):
            if path.is_file():
                load_dotenv(path, override=False)
                if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                    return

    def evaluate(self, image_path: Path, *, role: str, context: BenchmarkCaseContext) -> dict[str, Any]:
        from validator_studio.face_validator import validate_face
        from validator_studio.image_validator import validate_image

        image_sha = _sha(image_path)

        def persist_raw(event: dict[str, Any]) -> None:
            if self.raw_root is None:
                return
            sample = int(event.get("sampleIndex", 0))
            validator = str(event.get("validator", "unknown"))
            target = self.raw_root / image_sha / role
            target.mkdir(parents=True, exist_ok=True)
            record = {
                "imageSha256": image_sha,
                "role": role,
                "validator": validator,
                "sampleIndex": sample,
                "validatorIdentity": self.identity,
                "provider": self.provider,
                "model": "configured",
                "capturedAt": datetime.now(timezone.utc).isoformat(),
                **event,
            }
            path = target / f"{validator}-sample-{sample}.jsonl"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

        face = validate_face(
            self.project, self.subject, image_path, provider=self.provider,
            reference_image_paths=[context.a2_path], samples=self.samples,
            raw_response_sink=persist_raw,
        )
        image = validate_image(
            self.project, self.subject, image_path, provider=self.provider, samples=self.samples,
            scenario_profile_id=_scenario_profile_id(context.case),
            raw_response_sink=persist_raw,
        )
        regional = {
            "identity": face.dna_match_score,
            "eyes_brows": face.category_scores.get("eyes_and_brows"),
            "geometry": None,
            "anatomy": None,
            "outfit": None,
            "environment": None,
            "global_composite": image.overall_score,
        }
        production_regional = ProductionRegionalEvidenceAdapter().load(image_path)
        if production_regional is not None:
            regional = production_regional["scores"]
        gate, failures = RegionalGate(
            identity=regional["identity"], eyes_brows=regional["eyes_brows"],
            geometry=regional["geometry"], anatomy=regional["anatomy"],
            outfit=regional["outfit"], environment=regional["environment"],
            global_composite=regional["global_composite"], pixel_preservation=False,
        ).evaluate()
        regional_gate_evidence = None
        if production_regional is not None:
            regional_gate_evidence = {
                "authority": "image_studio_runtime.action_composite.workflow_v2.RegionalGate",
                "producer": production_regional["authority"],
                "passed": gate,
                "failures": list(failures),
                "evidenceId": production_regional["manifestSha256"],
                "sourceArtifact": production_regional["manifestPath"],
            }
        return {
            "role": role, "imageSha256": image_sha, "samples": self.samples,
            "faceQc": face.model_dump(mode="json"), "imageQc": image.model_dump(mode="json"),
            "faceQcScore": float(face.overall_score), "regional": regional,
            "regionalGate": {"passed": gate, "failures": failures},
            "regionalGateEvidence": regional_gate_evidence,
            "regionalEvidence": production_regional,
            "validator": self.identity,
            "cacheIdentity": self.identity,
        }

    def recover_missing_image_samples(
        self,
        image_path: Path,
        *,
        role: str,
        context: BenchmarkCaseContext,
        benchmark_id: str,
        missing_sample_indices: list[int],
    ) -> dict[str, Any]:
        """Recover one output using historical face samples and missing image samples.

        This deliberately calls only the existing image-observation transport.
        Parsed face/image raw records are reused first; a live call is made only
        for an image sample index proven missing by the raw-history audit.
        """
        image_sha = _sha(image_path)
        target_root = self.raw_root / image_sha / role if self.raw_root is not None else None

        def historical(kind: str, model: Any) -> dict[int, Any]:
            found: dict[int, Any] = {}
            if target_root is None:
                return found
            for path in sorted(target_root.glob(f"{kind}-sample-*.jsonl")):
                try:
                    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                except (OSError, ValueError):
                    continue
                for event in reversed(records):
                    if event.get("parseStatus") not in {"parsed", "before_contract", "failed", "raw_captured"}:
                        continue
                    index = int(event.get("sampleIndex", 0))
                    if not 1 <= index <= self.samples or index in found:
                        continue
                    raw = event.get("parsedEvidence")
                    try:
                        payload = raw if isinstance(raw, dict) else extract_json(str(event.get("rawResponse", "")))
                        found[index] = model.model_validate(payload)
                    except Exception:
                        continue
            return found

        face_samples = historical("face", FaceValidationObservation)
        image_samples = historical("image", ImageObservation)
        if len(face_samples) != self.samples:
            raise ValidatorEvidenceError(
                f"{role} {benchmark_id}: historical face evidence is incomplete; refusing non-target face spend"
            )
        dna_path = find_dna_path(self.project, self.subject)
        dna = load_json(dna_path)
        for sample_index in missing_sample_indices:
            if sample_index in image_samples:
                continue
            events: list[dict[str, Any]] = []

            def persist(event: dict[str, Any]) -> None:
                if target_root is None:
                    return
                event = {**event, "sampleIndex": sample_index}
                record = {
                    "imageSha256": image_sha, "role": role,
                    "validator": event.get("validator", "image"),
                    "sampleIndex": sample_index,
                    "validatorIdentity": self.identity,
                    "provider": self.provider, "model": "configured",
                    "capturedAt": datetime.now(timezone.utc).isoformat(), **event,
                }
                target_root.mkdir(parents=True, exist_ok=True)
                path = target_root / f"image-sample-{sample_index}.jsonl"
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                events.append(record)

            with paid_call_context({
                "benchmarkId": benchmark_id, "branch": role, "imageSha256": image_sha,
                "sampleIndex": sample_index,
                "reason": "missing image Validator sample after complete historical face/image audit",
                "historicalEvidenceSearch": {
                    "runs": "Runs 1-5 plus recovery raw/cache evidence",
                    "faceSamplesFound": sorted(face_samples),
                    "imageSamplesFound": sorted(image_samples),
                    "sampleRequested": sample_index,
                },
            }):
                observation = observe_image_against_dna(
                    image_path, dna, provider=self.provider, samples=1, raw_response_sink=persist
                )
            image_samples[sample_index] = observation

        if len(image_samples) != self.samples:
            raise ValidatorEvidenceError(f"{role} {benchmark_id}: image evidence remains incomplete")
        face_report = report_from_face_observations(
            self.project, self.subject, image_path,
            [face_samples[index] for index in sorted(face_samples)], self.provider,
            reference_image_paths=[context.a2_path],
        )
        image_report = report_from_image_observations(
            self.project, self.subject, image_path,
            [image_samples[index] for index in sorted(image_samples)], self.provider,
            scenario_profile_id=_scenario_profile_id(context.case),
        )
        regional = {"identity": face_report.dna_match_score,
                    "eyes_brows": face_report.category_scores.get("eyes_and_brows"),
                    "geometry": None, "anatomy": None, "outfit": None,
                    "environment": None, "global_composite": image_report.overall_score}
        return {
            "role": role, "imageSha256": image_sha, "samples": self.samples,
            "faceQc": face_report.model_dump(mode="json"),
            "imageQc": image_report.model_dump(mode="json"),
            "faceQcScore": float(face_report.overall_score),
            "regional": regional,
            "validator": self.identity, "cacheIdentity": self.identity,
            "historicalFaceSamples": sorted(face_samples),
            "newImageSamples": sorted(set(missing_sample_indices)),
        }


class ProductionRegionalEvidenceAdapter:
    """Rehydrate only complete RegionalScoreGateway evidence already persisted.

    ActionCompositePipeline persists the authority envelope in a composite
    manifest.  The benchmark may reuse that envelope, but it never derives a
    scene score from face/image QC, intent metadata, or pixel preservation.
    Missing or incomplete envelopes remain unavailable and therefore fail the
    existing RegionalGate closed.
    """

    REQUIRED = ("identity", "eyes_brows", "geometry", "anatomy", "outfit", "environment", "global_composite")

    @classmethod
    def load(cls, image_path: Path) -> dict[str, Any] | None:
        manifest_path = image_path.parent / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        envelope = manifest.get("regional_scores")
        if not isinstance(envelope, Mapping):
            return None
        scores = envelope.get("scores")
        sources = envelope.get("sources")
        provenance = envelope.get("provenance")
        if not isinstance(scores, Mapping) or not all(
            isinstance(scores.get(name), (int, float)) for name in cls.REQUIRED
        ):
            return None
        if not isinstance(sources, Mapping) or not isinstance(provenance, Mapping):
            return None
        return {
            "authority": "image_studio_runtime.action_composite.RegionalScoreGateway",
            "manifestPath": str(manifest_path),
            "manifestSha256": _sha(manifest_path),
            "scores": {name: float(scores[name]) for name in cls.REQUIRED},
            "sources": dict(sources),
            "provenance": dict(provenance),
        }


class BenchmarkRegionalEvidenceAdapter:
    """Materialize Regional evidence through the production gateway only.

    This adapter owns benchmark I/O and DTO construction.  It does not score
    images, infer scene semantics, or replace missing Validator evidence.  The
    three scene-region values come from the existing production
    ``StagePreservationEvidenceAdapter``; identity/eyes/global come from the
    persisted Validator Studio reports; geometry comes from the frozen YuNet
    authority plus a fresh production observation of the existing output.
    """

    GATE_AUTHORITY = "image_studio_runtime.action_composite.workflow_v2.RegionalGate"
    GATEWAY_AUTHORITY = "image_studio_runtime.action_composite.regional_score_gateway.RegionalScoreGateway"
    VERSION = "benchmark-regional-materialization-v1"

    def __init__(self, *, evidence_root: Path) -> None:
        self.evidence_root = evidence_root

    @staticmethod
    def _geometry(context: BenchmarkCaseContext, output_path: Path) -> tuple[FaceGeometry, FaceGeometry, dict[str, Any]]:
        authority = json.loads(context.geometry_path.read_text(encoding="utf-8"))
        expected_payload = authority.get("geometry")
        if not isinstance(expected_payload, Mapping):
            raise RegionalScoreBlocked("frozen geometry authority has no expected geometry")
        expected = FaceGeometry.model_validate(expected_payload)
        extractor = create_geometry_extractor(context.geometry_backend)
        observed = extractor(output_path)
        provenance = dict(getattr(extractor, "last_provenance", {}) or {})
        return expected, observed, provenance

    def materialize(
        self,
        *,
        run_id: str,
        attempt_id: str,
        benchmark_id: str,
        branch: str,
        context: BenchmarkCaseContext,
        output_path: Path,
        output_qc: Mapping[str, Any],
        pixel_preservation: bool,
        source_run_id: str | None = None,
        source_attempt_id: str | None = None,
    ) -> dict[str, Any]:
        face_payload = output_qc.get("faceQc")
        image_payload = output_qc.get("imageQc")
        if not isinstance(face_payload, Mapping) or not isinstance(image_payload, Mapping):
            raise RegionalScoreBlocked("Validator Studio face/image reports are missing")
        face_report = ValidationReport.model_validate(face_payload)
        image_report = ValidationReport.model_validate(image_payload)
        expected, observed, geometry_provenance = self._geometry(context, output_path)
        transform = context.crop_transform
        crop_box = {
            "left": transform.source_x,
            "top": transform.source_y,
            "right": transform.source_x + transform.source_w,
            "bottom": transform.source_y + transform.source_h,
        }
        preservation = StagePreservationEvidenceAdapter().produce(
            source_artifact=context.base_path,
            candidate_artifact=output_path,
            mask_artifact=context.crop_mask_path,
            crop_box=crop_box,
        )
        result = RegionalScoreGateway().build(RegionalScoreEvidence(
            face_report=face_report,
            image_report=image_report,
            geometry_expected=expected,
            geometry_observed=observed,
            geometry_source_artifacts=[str(context.geometry_path), str(output_path)],
            preservation_evidence=preservation,
        ))
        preservation_pass = pixel_preservation and all(item.status == "PASS" for item in preservation)
        gate, failures = RegionalGate(
            identity=result.scores.get("identity"),
            eyes_brows=result.scores.get("eyes_brows"),
            geometry=result.scores.get("geometry"),
            anatomy=result.scores.get("anatomy"),
            outfit=result.scores.get("outfit"),
            environment=result.scores.get("environment"),
            global_composite=result.scores.get("global_composite"),
            pixel_preservation=preservation_pass,
        ).evaluate()
        record: dict[str, Any] = {
            "benchmarkId": benchmark_id,
            "branch": branch,
            "imagePath": str(output_path),
            "imageSha256": _sha(output_path),
            "sourceRunId": source_run_id,
            "sourceAttemptId": source_attempt_id,
            "authority": self.GATEWAY_AUTHORITY,
            "gatewayImplementation": self.GATEWAY_AUTHORITY,
            "adapterVersion": self.VERSION,
            "scores": result.model_dump(mode="json"),
            "regionalGate": {"authority": self.GATE_AUTHORITY, "passed": gate, "failures": list(failures)},
            "geometryObservation": geometry_provenance,
            "preservationEvidence": [item.model_dump(mode="json") for item in preservation],
            "sourceArtifact": str(context.geometry_path),
        }
        identity_payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        evidence_id = _sha_bytes(identity_payload)
        record["evidenceId"] = evidence_id
        target = self.evidence_root / run_id / attempt_id
        target.mkdir(parents=True, exist_ok=False)
        evidence_path = target / "evidence.json"
        evidence_path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        record["evidencePath"] = str(evidence_path)
        return {
            "regional": result.scores,
            "regionalAuthority": self.GATEWAY_AUTHORITY,
            "regionalGateEvidence": {
                "authority": self.GATE_AUTHORITY,
                "producer": self.GATEWAY_AUTHORITY,
                "passed": gate,
                "failures": list(failures),
                "evidenceId": evidence_id,
                "sourceArtifact": str(evidence_path),
            },
            "regionalEvidence": record,
        }


class OfficialBenchmarkCompositeExecutor(BenchmarkExecutor):
    """Dispatch the three official branches and attach cached QC evidence."""

    def __init__(self, *, repo_root: Path, context_factory: BenchmarkCaseContextFactory, control: ControlBenchmarkExecutor, nano: NanoBananaEditBenchmarkExecutor, remote: ComfyUIRemoteBenchmarkExecutor, validator_cache: ValidatorEvidenceCache, official_root: Path, allow_external_remote_block: bool = False) -> None:
        self.repo_root = repo_root
        self.context_factory = context_factory
        self.branches = {"control": control, "nano-banana-edit": nano, "comfyui-remote": remote}
        self.validator_cache = validator_cache
        self.official_root = official_root
        self.allow_external_remote_block = allow_external_remote_block

    def capabilities(self) -> Mapping[str, Mapping[str, Any]]:
        result: dict[str, Mapping[str, Any]] = {}
        for branch in EXPECTED_BRANCHES:
            capability = dict(self.branches[branch].capabilities().get(branch, {}))
            capability["executorPath"] = f"{__name__}.OfficialBenchmarkCompositeExecutor -> {capability.get('executorPath', '')}"
            capability["evidenceWriter"] = True
            # Preserve provider capability flags for the preflight adapter;
            # dropping these fields would turn a healthy Nano transport into
            # a false "provider configuration unavailable" blocker.
            capability["ready"] = bool(capability.get("ready", False)) and self.validator_cache.adapter.samples == 3
            if branch == "nano-banana-edit" and self.allow_external_remote_block:
                reusable = getattr(self.branches[branch], "reusable_evidence", None) or {}
                expected_cases = {f"B{index:02d}" for index in range(1, 11)}
                if expected_cases.issubset(set(reusable)):
                    # This recovery run has a verified artifact for every Nano
                    # case.  It is executable through the reuse adapter and
                    # must not require a live provider or paid call.
                    capability["ready"] = True
                    capability["physicalCallable"] = True
                    capability["reuseOnly"] = True
                    capability["blockers"] = [
                        item for item in capability.get("blockers", [])
                        if "provider" not in str(item).lower()
                        and "endpoint" not in str(item).lower()
                    ]
            if branch == "comfyui-remote":
                health = getattr(self.branches[branch], "health", None)
                if health is None:
                    capability["ready"] = False
                    capability.setdefault("blockers", []).append("remote WorkerHealthPort is not configured")
                elif not self.allow_external_remote_block:
                    # Fresh runs require a healthy worker before creating any
                    # official rows.  A reuse/recovery run may persist
                    # explicit external failures for artifacts that are still
                    # missing, while the executor remains fail-closed.
                    try:
                        health_result = health.probe()
                        if getattr(health_result, "status", None).value != "HEALTHY":
                            capability["ready"] = False
                            capability.setdefault("blockers", []).append(
                                f"remote worker health is {health_result.status.value}"
                            )
                    except Exception as exc:
                        capability["ready"] = False
                        capability.setdefault("blockers", []).append(f"remote worker health probe failed: {exc}")
            if self.validator_cache.adapter.samples != 3:
                capability["blockers"] = [*capability.get("blockers", []), "Validator Studio samples must be 3"]
            result[branch] = capability
        return result

    def execute(self, *, case: Mapping[str, Any], branch: str, run_id: str, attempt_id: str, seed: int) -> Mapping[str, Any]:
        if branch not in self.branches:
            raise BenchmarkExecutionError(f"unknown official benchmark branch: {branch}")
        context = self.context_factory.build(case)
        executor = self.branches[branch]
        evidence = dict(executor.execute(case=case, branch=branch, run_id=run_id, attempt_id=attempt_id, seed=seed))
        output_path = Path(str(evidence.get("outputPath"))) if evidence.get("outputPath") else None
        if output_path is None or not output_path.is_file():
            raise BenchmarkExecutionError(f"{branch} executor produced no output artifact")
        try:
            base_qc = self.validator_cache.evaluate(context.base_path, role="base", context=context)
            output_qc = self.validator_cache.evaluate(output_path, role=branch, context=context)
        except Exception as exc:
            raise ValidatorEvidenceError(f"Validator Studio evidence evaluation failed: {exc}") from exc
        pixel = evidence.get("pixelPreservationResult") == "PASS"
        if branch == "nano-banana-edit":
            with Image.open(output_path) as output:
                if output.size != Image.open(context.base_path).size:
                    pixel = False
            if pixel or evidence.get("pixelPreservationResult") == "UNKNOWN":
                preservation = assert_pixels_preserved(
                    before_canvas=context.base_bytes, after_canvas=output_path.read_bytes(),
                    editable_mask=context.full_mask_path.read_bytes(),
                )
                pixel = preservation.passed
        regional = output_qc.get("regional", {})
        regional_evidence = output_qc.get("regionalEvidence")
        reuse = (evidence.get("lineage") or {}).get("artifactReuse") if isinstance(evidence.get("lineage"), Mapping) else None
        materialized = BenchmarkRegionalEvidenceAdapter(
            evidence_root=self.official_root / "regional-evidence"
        ).materialize(
            run_id=run_id,
            attempt_id=attempt_id,
            benchmark_id=str(case.get("id")),
            branch=branch,
            context=context,
            output_path=output_path,
            output_qc=output_qc,
            pixel_preservation=pixel,
            source_run_id=(reuse.get("sourceRunId") if isinstance(reuse, Mapping) else None),
            source_attempt_id=(reuse.get("sourceAttemptId") if isinstance(reuse, Mapping) else None),
        )
        regional = materialized["regional"]
        regional_evidence = materialized["regionalEvidence"]
        evidence.update({
            "faceQcBefore": base_qc.get("faceQcScore"),
            "faceQcAfter": output_qc.get("faceQcScore"),
            "identityScore": regional.get("identity"),
            "eyesBrowsScore": regional.get("eyes_brows"),
            "geometryScore": regional.get("geometry"),
            "anatomyScore": regional.get("anatomy"),
            "outfitScore": regional.get("outfit"),
            "environmentScore": regional.get("environment"),
            "globalScore": regional.get("global_composite"),
            "regionalAuthority": materialized["regionalAuthority"],
            "regionalGateEvidence": materialized["regionalGateEvidence"],
            "pixelPreservationResult": "PASS" if pixel else "FAIL",
            "samples": self.validator_cache.adapter.samples,
            "lineage": {**(evidence.get("lineage") or {}), "validatorBefore": base_qc, "validatorAfter": output_qc, "geometryAuthorityPath": str(context.geometry_path), "geometryAuthoritySha256": _sha(context.geometry_path)},
        })
        return evidence
