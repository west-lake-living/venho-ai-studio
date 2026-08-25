from __future__ import annotations

from pathlib import Path

from PIL import Image

from identity_restoration.application.benchmark_orchestration import (
    BenchmarkCaseContext,
    BenchmarkRegionalEvidenceAdapter,
    BenchmarkValidatorAdapter,
    OfficialBenchmarkCompositeExecutor,
    ProductionRegionalEvidenceAdapter,
    ValidatorEvidenceCache,
)
from image_studio_runtime.action_composite.models import BoundingBox, FaceGeometry


def _geometry_file(tmp_path: Path) -> Path:
    path = tmp_path / "geometry.json"
    expected = FaceGeometry(
        face_bbox=BoundingBox(left=1, top=1, right=7, bottom=7),
        head_bbox=BoundingBox(left=0, top=0, right=8, bottom=8), face_scale=0.75,
    )
    path.write_text(__import__("json").dumps({"geometry": expected.model_dump()}), encoding="utf-8")
    return path


class _Branch:
    def __init__(self, branch: str, output: Path, pixel: str = "PASS"):
        self.branch = branch
        self.output = output
        self.pixel = pixel
        self.calls = 0

    def capabilities(self):
        return {self.branch: {"ready": True, "physicalCallable": True, "evidenceWriter": True}}

    def execute(self, **kwargs):
        self.calls += 1
        return {
            "faceQcBefore": None, "faceQcAfter": None, "identityScore": None,
            "eyesBrowsScore": None, "geometryScore": None, "anatomyScore": None,
            "outfitScore": None, "environmentScore": None, "globalScore": None,
            "pixelPreservationResult": self.pixel, "runtimeMs": 1, "retryCount": 0,
            "workflowId": None, "workflowSha256": None, "gpuName": None,
            "vramPeakMb": None, "outputPath": str(self.output),
            "outputSha256": None, "executorStatus": "COMPLETED", "error": None,
            "provider": self.branch, "providerRequestId": None,
            "providerRunId": kwargs["run_id"], "backend": self.branch, "host": {},
        }


class _Qc:
    samples = 3
    identity = "fake-validator-v1"

    def __init__(self):
        self.calls = []

    def evaluate(self, image_path, *, role, context):
        self.calls.append((str(image_path), role))
        from validator_studio.schemas.validation_base import ArtifactRef
        report = {
            "project": "venho_hotel", "subject": "linh_an",
            "validation_type": "face" if role != "base" else "image",
            "artifact_ref": {"type": "image", "file": str(image_path), "hash": "sha256:" + "0" * 64},
            "overall_score": 95.0, "dna_match_score": 95.0,
            "category_scores": {"eyes_and_brows": 95.0},
        }
        return {
            "role": role, "faceQcScore": 95.0,
            "faceQc": {**report, "validation_type": "face"},
            "imageQc": {**report, "validation_type": "image"},
            "regional": {field: 95.0 for field in (
                "identity", "eyes_brows", "geometry", "anatomy",
                "outfit", "environment", "global_composite",
            )},
        }


def test_composite_dispatches_official_branches_and_reuses_base_qc(tmp_path: Path, monkeypatch):
    image = tmp_path / "base.png"
    Image.new("RGBA", (8, 8), (20, 30, 40, 255)).save(image)
    mask = tmp_path / "mask.png"
    Image.new("L", (8, 8), 0).save(mask)
    context = BenchmarkCaseContext(
        case={"id": "B01", "taxonomy": "Close-up Front"},
        base_path=image, base_sha256="0" * 64, base_bytes=image.read_bytes(),
        a2_path=image, geometry_path=_geometry_file(tmp_path), crop_path=image,
        crop_mask_path=mask, full_mask_path=mask,
        crop_transform=__import__("identity_restoration.domain.entities", fromlist=["CropTransform"]).CropTransform.from_box(0, 0, 8, 8, 8),
        mask_version="test", geometry_backend="yunet",
        geometry_model="test.onnx", geometry_model_sha256="1" * 64,
    )
    branches = {name: _Branch(name, image) for name in ("control", "nano-banana-edit", "comfyui-remote")}
    qc = _Qc()
    monkeypatch.setattr(
        "identity_restoration.application.benchmark_orchestration.create_geometry_extractor",
        lambda _backend: type("Extractor", (), {"last_provenance": {"backend": "test"}, "__call__": lambda self, _path: FaceGeometry(face_bbox=BoundingBox(left=1, top=1, right=7, bottom=7), head_bbox=BoundingBox(left=0, top=0, right=8, bottom=8), face_scale=0.75)})(),
    )
    composite = OfficialBenchmarkCompositeExecutor(
        repo_root=tmp_path,
        context_factory=type("Factory", (), {"build": lambda self, case: context})(),
        control=branches["control"], nano=branches["nano-banana-edit"],
        remote=branches["comfyui-remote"],
        validator_cache=ValidatorEvidenceCache(tmp_path / "cache", qc),
        official_root=tmp_path,
    )
    for branch in branches:
        result = composite.execute(
            case=context.case, branch=branch, run_id="run", attempt_id=f"{branch}-1", seed=42
        )
        assert result["faceQcBefore"] == 95.0
        assert result["faceQcAfter"] == 95.0
        assert result["pixelPreservationResult"] == "PASS"
    assert len([item for item in qc.calls if item[1] == "base"]) == 1
    assert len(qc.calls) == 1


def test_validator_cache_is_sha_and_configuration_keyed(tmp_path: Path):
    image = tmp_path / "base.png"
    Image.new("RGB", (4, 4), (1, 2, 3)).save(image)
    qc = _Qc()
    cache = ValidatorEvidenceCache(tmp_path / "cache", qc)
    context = object()
    first = cache.evaluate(image, role="base", context=context)
    second = cache.evaluate(image, role="base", context=context)
    assert first == second
    assert len(qc.calls) == 1


def test_nano_unknown_pixel_evidence_is_recomputed_from_frozen_artifact(tmp_path: Path, monkeypatch):
    image = tmp_path / "base.png"
    Image.new("RGBA", (8, 8), (20, 30, 40, 255)).save(image)
    mask = tmp_path / "mask.png"
    Image.new("L", (8, 8), 0).save(mask)
    context = BenchmarkCaseContext(
        case={"id": "B01", "taxonomy": "Close-up Front"},
        base_path=image, base_sha256="0" * 64, base_bytes=image.read_bytes(),
        a2_path=image, geometry_path=_geometry_file(tmp_path), crop_path=image,
        crop_mask_path=mask, full_mask_path=mask,
        crop_transform=__import__("identity_restoration.domain.entities", fromlist=["CropTransform"]).CropTransform.from_box(0, 0, 8, 8, 8),
        mask_version="test", geometry_backend="yunet",
        geometry_model="test.onnx", geometry_model_sha256="1" * 64,
    )
    branches = {name: _Branch(name, image) for name in ("control", "comfyui-remote")}
    branches["nano-banana-edit"] = _Branch("nano-banana-edit", image, pixel="UNKNOWN")
    qc = _Qc()
    monkeypatch.setattr(
        "identity_restoration.application.benchmark_orchestration.create_geometry_extractor",
        lambda _backend: type("Extractor", (), {"last_provenance": {"backend": "test"}, "__call__": lambda self, _path: FaceGeometry(face_bbox=BoundingBox(left=1, top=1, right=7, bottom=7), head_bbox=BoundingBox(left=0, top=0, right=8, bottom=8), face_scale=0.75)})(),
    )
    composite = OfficialBenchmarkCompositeExecutor(
        repo_root=tmp_path,
        context_factory=type("Factory", (), {"build": lambda self, case: context})(),
        control=branches["control"], nano=branches["nano-banana-edit"],
        remote=branches["comfyui-remote"],
        validator_cache=ValidatorEvidenceCache(tmp_path / "cache", qc),
        official_root=tmp_path,
    )
    result = composite.execute(
        case=context.case, branch="nano-banana-edit", run_id="run", attempt_id="nano-1", seed=42
    )
    assert result["pixelPreservationResult"] == "PASS"


def test_production_regional_adapter_reuses_only_complete_gateway_manifest(tmp_path: Path):
    image = tmp_path / "image.png"
    Image.new("RGB", (4, 4), (1, 2, 3)).save(image)
    assert ProductionRegionalEvidenceAdapter.load(image) is None

    manifest = image.parent / "manifest.json"
    scores = {name: 95 for name in ProductionRegionalEvidenceAdapter.REQUIRED}
    manifest.write_text(__import__("json").dumps({
        "regional_scores": {
            "scores": scores,
            "sources": {name: "production" for name in scores},
            "provenance": {name: {"producer": "production"} for name in scores},
        }
    }), encoding="utf-8")
    evidence = ProductionRegionalEvidenceAdapter.load(image)
    assert evidence is not None
    assert evidence["authority"].endswith("RegionalScoreGateway")
    assert evidence["scores"] == scores


def test_production_regional_adapter_rejects_partial_manifest(tmp_path: Path):
    image = tmp_path / "image.png"
    Image.new("RGB", (4, 4), (1, 2, 3)).save(image)
    (tmp_path / "manifest.json").write_text(__import__("json").dumps({
        "regional_scores": {"scores": {"anatomy": 95}, "sources": {}, "provenance": {}}
    }), encoding="utf-8")
    assert ProductionRegionalEvidenceAdapter.load(image) is None


def test_benchmark_regional_adapter_invokes_production_gateway_and_persists_gate(
    tmp_path: Path, monkeypatch
):
    from validator_studio.schemas.validation_base import ArtifactRef, ValidationReport

    image = tmp_path / "image.png"
    Image.new("RGBA", (8, 8), (20, 30, 40, 255)).save(image)
    mask = tmp_path / "mask.png"
    Image.new("L", (8, 8), 0).save(mask)
    geometry = tmp_path / "geometry.json"
    expected = FaceGeometry(
        face_bbox=BoundingBox(left=1, top=1, right=7, bottom=7),
        head_bbox=BoundingBox(left=0, top=0, right=8, bottom=8), face_scale=0.75,
    )
    geometry.write_text(__import__("json").dumps({"geometry": expected.model_dump()}), encoding="utf-8")
    context = BenchmarkCaseContext(
        case={"id": "B01", "taxonomy": "Close-up Front"},
        base_path=image, base_sha256="0" * 64, base_bytes=image.read_bytes(),
        a2_path=image, geometry_path=geometry, crop_path=image,
        crop_mask_path=mask, full_mask_path=mask,
        crop_transform=__import__("identity_restoration.domain.entities", fromlist=["CropTransform"]).CropTransform.from_box(0, 0, 8, 8, 8),
        mask_version="test", geometry_backend="yunet",
        geometry_model="test.onnx", geometry_model_sha256="1" * 64,
    )
    report_args = dict(
        project="venho_hotel", subject="linh_an", artifact_ref=ArtifactRef(
            type="image", file=str(image), hash="sha256:" + "0" * 64
        ), overall_score=95, dna_match_score=95,
        category_scores={"eyes_and_brows": 95},
    )
    report = ValidationReport(validation_type="image", **report_args)
    face = report.model_copy(update={"validation_type": "face"})
    output_qc = {"faceQc": face.model_dump(mode="json"), "imageQc": report.model_dump(mode="json")}

    class _Extractor:
        last_provenance = {"backend": "test", "original_sha256": "0" * 64}

        def __call__(self, _path):
            return expected

    monkeypatch.setattr(
        "identity_restoration.application.benchmark_orchestration.create_geometry_extractor",
        lambda _backend: _Extractor(),
    )
    result = BenchmarkRegionalEvidenceAdapter(
        evidence_root=tmp_path / "regional-evidence"
    ).materialize(
        run_id="run-1", attempt_id="B01-control-attempt-1", benchmark_id="B01",
        branch="control", context=context, output_path=image,
        output_qc=output_qc, pixel_preservation=True,
    )
    assert result["regionalAuthority"].endswith("RegionalScoreGateway")
    assert result["regionalGateEvidence"]["authority"].endswith("RegionalGate")
    assert result["regionalGateEvidence"]["evidenceId"]
    assert Path(result["regionalEvidence"]["evidencePath"]).is_file()
    assert set(result["regional"]).__contains__("anatomy")
