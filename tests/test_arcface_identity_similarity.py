from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from identity_restoration.application.face_observability import FaceDetection
from identity_restoration.infrastructure import arcface_similarity as module
from identity_restoration.infrastructure.arcface_similarity import (
    MODEL_SHA256,
    ArcFaceEmbedder,
    IdentitySimilarityBlocked,
    ReferenceImage,
    measure_identity_similarity,
)
from identity_restoration.interface.cli import main

LANDMARKS = ((40.0, 50.0), (72.0, 50.0), (56.0, 70.0), (42.0, 90.0), (70.0, 90.0))


def _face(x0: float, size: float, confidence: float = 0.9) -> FaceDetection:
    return FaceDetection(confidence=confidence, bbox=(x0, 0.0, x0 + size, size), landmarks=LANDMARKS)


class _Detector:
    """Faces keyed by the image's solid colour, so each file picks its own detections."""

    def __init__(self, by_colour: dict[int, tuple[FaceDetection, ...]]) -> None:
        self.by_colour = by_colour

    def detect(self, image: Image.Image) -> tuple[FaceDetection, ...]:
        return self.by_colour[image.getpixel((0, 0))[0]]


class _Embedder:
    expected_model_sha256 = MODEL_SHA256

    def __init__(self, vectors: dict[int, list[float]]) -> None:
        self.vectors = vectors

    def embed(self, aligned_bgr: np.ndarray) -> np.ndarray:
        vector = np.asarray(self.vectors[int(aligned_bgr[56, 56, 2])], dtype=np.float64)
        return vector / np.linalg.norm(vector)


def _image(tmp_path: Path, name: str, colour: int) -> Path:
    path = tmp_path / f"{name}.png"
    Image.new("RGB", (128, 128), (colour, colour, colour)).save(path)
    return path


def test_reports_per_reference_cosine_mean_and_max(tmp_path: Path) -> None:
    cand = _image(tmp_path, "cand", 10)
    refs = [ReferenceImage("A2", _image(tmp_path, "a2", 20)), ReferenceImage("B3", _image(tmp_path, "b3", 30))]
    detector = _Detector({10: (_face(0, 100),), 20: (_face(0, 100),), 30: (_face(0, 100),)})
    embedder = _Embedder({10: [1, 0], 20: [1, 0], 30: [0, 1]})

    result = measure_identity_similarity(cand, refs, detector=detector, embedder=embedder)

    assert result["schema"] == "identity-similarity-v1"
    assert result["faceDetected"] is True
    assert [row["cosine"] for row in result["references"]] == [1.0, 0.0]
    assert result["meanCosine"] == 0.5 and result["maxCosine"] == 1.0
    assert result["model"]["sha256"] == MODEL_SHA256
    json.dumps(result)  # the CLI emits it as one JSON document


def test_counts_prominent_faces_but_ignores_tiny_background_faces(tmp_path: Path) -> None:
    cand = _image(tmp_path, "cand", 10)
    ref = [ReferenceImage("A2", _image(tmp_path, "a2", 20))]
    detector = _Detector({
        10: (_face(0, 100), _face(110, 40), _face(120, 20)),  # 16% and 4% of the subject's area
        20: (_face(0, 100),),
    })
    result = measure_identity_similarity(
        cand, ref, detector=detector, embedder=_Embedder({10: [1, 0], 20: [1, 0]})
    )
    assert result["candidate"]["faceCount"] == 3
    assert result["candidate"]["prominentFaceCount"] == 2


def test_candidate_without_face_is_measured_not_blocked(tmp_path: Path) -> None:
    cand = _image(tmp_path, "cand", 10)
    ref = [ReferenceImage("A2", _image(tmp_path, "a2", 20))]
    result = measure_identity_similarity(
        cand, ref, detector=_Detector({10: (), 20: (_face(0, 100),)}), embedder=_Embedder({20: [1, 0]})
    )
    assert result["faceDetected"] is False and result["meanCosine"] is None


def test_reference_without_face_blocks(tmp_path: Path) -> None:
    cand = _image(tmp_path, "cand", 10)
    ref = [ReferenceImage("A2", _image(tmp_path, "a2", 20))]
    with pytest.raises(IdentitySimilarityBlocked, match="reference A2"):
        measure_identity_similarity(
            cand, ref, detector=_Detector({10: (_face(0, 100),), 20: ()}), embedder=_Embedder({})
        )


def test_embedder_refuses_missing_or_tampered_model(tmp_path: Path) -> None:
    aligned = np.zeros((112, 112, 3), dtype=np.uint8)
    with pytest.raises(IdentitySimilarityBlocked, match="missing"):
        ArcFaceEmbedder(model_path=tmp_path / "absent.onnx").embed(aligned)
    fake = tmp_path / "w600k_r50.onnx"
    fake.write_bytes(b"not the pinned model")
    with pytest.raises(IdentitySimilarityBlocked, match="SHA-256 mismatch"):
        ArcFaceEmbedder(model_path=fake).embed(aligned)


def test_cli_rejects_malformed_reference_and_reports_error(tmp_path: Path, capsys) -> None:
    cand = _image(tmp_path, "cand", 10)
    assert main(["identity-similarity", "--image", str(cand), "--reference", "no-equals-sign"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["error"]["code"] == "ERR_IDENTITY_SIMILARITY_FAILED"


_REAL_MODEL = module._default_model_path()


@pytest.mark.skipif(not _REAL_MODEL.is_file(), reason="pinned ArcFace model not provisioned")
def test_real_model_runs_offline_on_cpu() -> None:
    rng = np.random.default_rng(0)
    aligned = rng.integers(0, 255, (112, 112, 3), dtype=np.uint8)
    vector = ArcFaceEmbedder().embed(aligned)
    assert vector.shape == (512,)
    assert abs(float(np.linalg.norm(vector)) - 1.0) < 1e-9
