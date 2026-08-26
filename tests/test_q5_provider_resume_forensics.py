from __future__ import annotations

from pathlib import Path

import pytest


def test_face_samples_are_process_local_and_503_aborts_before_aggregate(monkeypatch) -> None:
    """Q5 contract probe: a later transport failure discards prior samples."""
    import validator_studio.face_validator as module

    rubric = {
        "binary_gates": [
            {"id": "identity_structure"},
            {"id": "eye_ratio"},
            {"id": "forbidden_traits"},
        ],
        "weighted": {
            "facial_shape": 0.30,
            "eyes_and_brows": 0.25,
            "nose": 0.20,
            "mouth_and_chin": 0.15,
            "technical_quality": 0.10,
        },
    }
    payload = {
        "gates": [
            {"gate": gate["id"], "passed": True}
            for gate in rubric["binary_gates"]
        ],
        "weighted_scores": {key: 90 for key in rubric["weighted"]},
        "notes": [],
    }
    calls: list[int] = []
    events: list[dict] = []

    class FakeClient:
        last_raw_response = None

        def __init__(self, *args, **kwargs):
            self.raw_response_sink = None

        def analyze_image(self, image_path: Path, prompt: str, **kwargs):
            sample_index = kwargs.get("sample_index", 1)
            calls.append(sample_index)
            if sample_index == 1:
                self.last_raw_response = '{"gates": [...sample-1...]}'
                return payload
            self.last_raw_response = "503 UNAVAILABLE"
            raise RuntimeError("503 UNAVAILABLE")

    aggregate_called = False

    def aggregate_probe(samples):
        nonlocal aggregate_called
        aggregate_called = True
        return samples[0]

    monkeypatch.setattr(module, "VisionClient", FakeClient)
    monkeypatch.setattr(module, "_merge_face_samples", aggregate_probe)

    with pytest.raises(RuntimeError, match="503 UNAVAILABLE"):
        module._observe_face(
            Path("candidate.png"),
            {"project": "venho_hotel", "subject": "linh_an"},
            rubric,
            provider="gemini",
            samples=3,
            raw_response_sink=events.append,
        )

    assert calls == [1, 2]
    assert aggregate_called is False
    assert any(event["sampleIndex"] == 1 and event["parseStatus"] == "parsed" for event in events)
    assert events[-1]["sampleIndex"] == 2
    assert events[-1]["parseStatus"] == "failed"
